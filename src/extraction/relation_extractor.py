from collections import defaultdict
from typing import Dict, List, Tuple

from src.schema.types import EventRecord, LinkedMention, RelationRecord


class RelationExtractor:
    LOCATION_TRIGGERS = ["位于", "located in", "位在", "是...城市"]

    def extract(
        self, linked_mentions: List[LinkedMention], events: List[EventRecord]
    ) -> List[RelationRecord]:
        grouped_mentions = self._group_mentions_by_sentence(linked_mentions)
        relations: List[RelationRecord] = []
        seen = set()
        relation_index = 1

        for event in events:
            event_relations = self._relations_from_event(event)
            for relation in event_relations:
                key = self._relation_key(relation)
                if key in seen:
                    continue
                seen.add(key)
                relation.relation_id = f"REL{relation_index:03d}"
                relation_index += 1
                relations.append(relation)

        for (text_id, sentence_id), mentions in sorted(grouped_mentions.items()):
            sentence = mentions[0].context
            for relation in self._relations_from_sentence(text_id, sentence_id, sentence, mentions):
                key = self._relation_key(relation)
                if key in seen:
                    continue
                seen.add(key)
                relation.relation_id = f"REL{relation_index:03d}"
                relation_index += 1
                relations.append(relation)

        return relations

    def _group_mentions_by_sentence(
        self, linked_mentions: List[LinkedMention]
    ) -> Dict[Tuple[str, int], List[LinkedMention]]:
        grouped: Dict[Tuple[str, int], List[LinkedMention]] = defaultdict(list)
        for mention in linked_mentions:
            if mention.status != "linked":
                continue
            grouped[(mention.text_id, mention.sentence_id)].append(mention)

        for key in grouped:
            grouped[key].sort(key=lambda item: (item.start, item.end))
        return grouped

    def _relations_from_event(self, event: EventRecord) -> List[RelationRecord]:
        relation_specs: List[Tuple[Dict[str, str], str, Dict[str, str]]] = []
        participants = self._participants_by_role(event.participants)

        if event.event_type == "EducationEvent":
            relation_specs.extend(
                self._build_role_relations(event, participants, "student", "studied_at", ["institution"])
            )
        elif event.event_type == "PublicationEvent":
            relation_specs.extend(
                self._build_role_relations(event, participants, "author", "published", ["work"])
            )
        elif event.event_type == "ResearchEvent":
            relation_specs.extend(
                self._build_role_relations(
                    event, participants, "researcher", "proposed", ["topic"]
                )
            )
        elif event.event_type == "WarWorkEvent":
            relation_specs.extend(
                self._build_role_relations(
                    event, participants, "researcher", "worked_at", ["organization", "location"]
                )
            )
            relation_specs.extend(
                self._build_role_relations(
                    event, participants, "researcher", "used", ["device"]
                )
            )
            relation_specs.extend(
                self._build_role_relations(
                    event, participants, "researcher", "participated_in", ["background_event"]
                )
            )
        elif event.event_type == "EmploymentEvent":
            relation_specs.extend(
                self._build_role_relations(
                    event, participants, "staff", "worked_at", ["organization", "location"]
                )
            )
        elif event.event_type == "InfluenceEvent":
            influencer = participants.get("influencer", [])
            influenced = participants.get("influenced", [])
            if influencer and influenced:
                relation_specs.append((influenced[0], "influenced_by", influencer[0]))

        relations: List[RelationRecord] = []
        for head, relation, tail in relation_specs:
            relations.append(
                RelationRecord(
                    relation_id="",
                    text_id=event.text_id,
                    sentence_id=event.sentence_id,
                    head_id=head["entity_id"],
                    head_name=head["name"],
                    head_type=head["entity_type"],
                    relation=relation,
                    tail_id=tail["entity_id"],
                    tail_name=tail["name"],
                    tail_type=tail["entity_type"],
                    evidence=event.evidence,
                    method="event_rule",
                    trigger=event.trigger,
                    source_event_id=event.event_id,
                )
            )

        return relations

    def _build_role_relations(
        self,
        event: EventRecord,
        participants: Dict[str, List[Dict[str, str]]],
        head_role: str,
        relation: str,
        tail_roles: List[str],
    ) -> List[Tuple[Dict[str, str], str, Dict[str, str]]]:
        head_items = participants.get(head_role, [])
        if not head_items:
            return []

        relations = []
        head = head_items[0]
        for role in tail_roles:
            for tail in participants.get(role, []):
                relations.append((head, relation, tail))
        return relations

    def _relations_from_sentence(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
    ) -> List[RelationRecord]:
        relations: List[RelationRecord] = []
        lowered = sentence.lower()
        organizations = self._pick_mentions(mentions, "Organization")
        places = self._pick_mentions(mentions, "Place")
        if not organizations or not places:
            return relations

        if not any(trigger in lowered for trigger in ["位于", "located in"]):
            return relations

        for organization in organizations:
            for place in places:
                if place.start <= organization.end:
                    continue
                trigger_text = sentence[organization.end : place.start]
                if "位于" not in trigger_text and "located in" not in trigger_text.lower():
                    continue
                relations.append(
                    RelationRecord(
                        relation_id="",
                        text_id=text_id,
                        sentence_id=sentence_id,
                        head_id=organization.entity_id,
                        head_name=organization.canonical_name,
                        head_type=organization.resolved_entity_type,
                        relation="located_in",
                        tail_id=place.entity_id,
                        tail_name=place.canonical_name,
                        tail_type=place.resolved_entity_type,
                        evidence=sentence,
                        method="sentence_rule",
                        trigger="位于" if "位于" in sentence else "located in",
                    )
                )
        return relations

    def _participants_by_role(
        self, participants: List[Dict[str, str]]
    ) -> Dict[str, List[Dict[str, str]]]:
        grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for participant in participants:
            grouped[participant["role"]].append(participant)
        return grouped

    def _pick_mentions(self, mentions: List[LinkedMention], entity_type: str) -> List[LinkedMention]:
        picked = []
        seen = set()
        for mention in mentions:
            if mention.resolved_entity_type != entity_type:
                continue
            if mention.entity_id in seen:
                continue
            seen.add(mention.entity_id)
            picked.append(mention)
        return picked

    def _relation_key(self, relation: RelationRecord) -> tuple:
        return (
            relation.text_id,
            relation.sentence_id,
            relation.head_id,
            relation.relation,
            relation.tail_id,
        )
