from collections import defaultdict
from typing import Dict, List, Tuple

from src.schema.types import EventRecord, LinkedMention


class EventExtractor:
    EDUCATION_TRIGGERS = ["就读", "学习", "攻读", "深造", "studied", "study", "matriculated"]
    PUBLICATION_TRIGGERS = ["发表", "published", "论文", "paper"]
    PROPOSAL_TRIGGERS = ["提出", "proposed", "设计", "designed"]
    WAR_TRIGGERS = ["破译", "密码", "战争", "战时", "Enigma", "Bletchley", "GC&CS", "盟军"]
    EMPLOYMENT_TRIGGERS = ["工作", "任职", "加入", "worked", "joined", "回到"]
    INFLUENCE_TRIGGERS = ["影响", "influence", "influenced"]

    def extract(self, linked_mentions: List[LinkedMention]) -> List[EventRecord]:
        grouped = self._group_mentions_by_sentence(linked_mentions)
        events: List[EventRecord] = []
        event_index = 1

        for (text_id, sentence_id), mentions in sorted(grouped.items()):
            sentence = mentions[0].context
            builders = [
                self._extract_education_event,
                self._extract_publication_event,
                self._extract_research_event,
                self._extract_war_work_event,
                self._extract_employment_event,
                self._extract_influence_event,
            ]
            for builder in builders:
                event = builder(text_id, sentence_id, sentence, mentions, event_index)
                if event is None:
                    continue
                events.append(event)
                event_index += 1

        return events

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

    def _extract_education_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.EDUCATION_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        institutions = self._pick_mentions(mentions, "Organization")
        places = self._pick_mentions(mentions, "Place")
        if not persons or (not institutions and not places):
            return None

        place = places[0] if places else None
        participants = [self._participant("student", persons[0])]
        for institution in institutions:
            participants.append(self._participant("institution", institution))
        if place is not None:
            participants.append(self._participant("city", place))

        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="EducationEvent",
            trigger=self._find_trigger(sentence, self.EDUCATION_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            place=place.canonical_name if place is not None else "",
            description="记录人物的求学经历。",
        )

    def _extract_publication_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.PUBLICATION_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        works = self._pick_mentions(mentions, "Work")
        if not persons or not works:
            return None

        participants = [
            self._participant("author", persons[0]),
            self._participant("work", works[0]),
        ]
        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="PublicationEvent",
            trigger=self._find_trigger(sentence, self.PUBLICATION_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            description="记录图灵相关论文或作品的发表信息。",
        )

    def _extract_research_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.PROPOSAL_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        targets = (
            self._pick_mentions(mentions, "Concept")
            + self._pick_mentions(mentions, "Device")
            + self._pick_mentions(mentions, "Work")
        )
        if not persons or not targets:
            return None

        participants = [
            self._participant("researcher", persons[0]),
            self._participant("topic", targets[0]),
        ]
        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="ResearchEvent",
            trigger=self._find_trigger(sentence, self.PROPOSAL_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            description="记录图灵提出概念、设备或研究方向的句子。",
        )

    def _extract_war_work_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.WAR_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        places = self._pick_mentions(mentions, "Place")
        organizations = self._pick_mentions(mentions, "Organization")
        devices = self._pick_mentions(mentions, "Device")
        events = self._pick_mentions(mentions, "Event")
        if not persons:
            return None
        if not places and not organizations and not devices and not events:
            return None

        participants = [self._participant("researcher", persons[0])]
        if organizations:
            participants.append(self._participant("organization", organizations[0]))
        if places:
            participants.append(self._participant("location", places[0]))
        if devices:
            participants.append(self._participant("device", devices[0]))
        if events:
            participants.append(self._participant("background_event", events[0]))

        place = places[0].canonical_name if places else ""
        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="WarWorkEvent",
            trigger=self._find_trigger(sentence, self.WAR_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            place=place,
            description="记录图灵在战争背景下的密码工作。",
        )

    def _extract_employment_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.EMPLOYMENT_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        organizations = self._pick_mentions(mentions, "Organization")
        places = self._pick_mentions(mentions, "Place")
        if not persons or (not organizations and not places):
            return None

        participants = [self._participant("staff", persons[0])]
        if organizations:
            participants.append(self._participant("organization", organizations[0]))
        if places:
            participants.append(self._participant("location", places[0]))

        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="EmploymentEvent",
            trigger=self._find_trigger(sentence, self.EMPLOYMENT_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            place=places[0].canonical_name if places else "",
            description="记录图灵在机构或地点工作的经历。",
        )

    def _extract_influence_event(
        self,
        text_id: str,
        sentence_id: int,
        sentence: str,
        mentions: List[LinkedMention],
        event_index: int,
    ) -> EventRecord | None:
        if not self._contains_any(sentence, self.INFLUENCE_TRIGGERS):
            return None

        persons = self._pick_mentions(mentions, "Person")
        if len(persons) < 2:
            return None

        influencer, influenced = self._resolve_influence_direction(sentence, persons)
        participants = [
            self._participant("influencer", influencer),
            self._participant("influenced", influenced),
        ]
        return self._build_event(
            event_id=event_index,
            text_id=text_id,
            sentence_id=sentence_id,
            event_type="InfluenceEvent",
            trigger=self._find_trigger(sentence, self.INFLUENCE_TRIGGERS),
            evidence=sentence,
            participants=participants,
            time=self._first_time(mentions),
            description="记录人物之间的思想影响。",
        )

    def _pick_mentions(self, mentions: List[LinkedMention], entity_type: str) -> List[LinkedMention]:
        picked: List[LinkedMention] = []
        seen = set()
        for mention in mentions:
            if mention.resolved_entity_type != entity_type:
                continue
            if mention.entity_id in seen:
                continue
            seen.add(mention.entity_id)
            picked.append(mention)
        return picked

    def _participant(self, role: str, mention: LinkedMention) -> Dict[str, str]:
        return {
            "role": role,
            "entity_id": mention.entity_id,
            "name": mention.canonical_name,
            "entity_type": mention.resolved_entity_type,
        }

    def _resolve_influence_direction(
        self, sentence: str, persons: List[LinkedMention]
    ) -> tuple[LinkedMention, LinkedMention]:
        dui_index = sentence.find("对")
        if dui_index != -1:
            before_dui = [item for item in persons if item.start < dui_index]
            after_dui = [item for item in persons if item.start > dui_index]
            if before_dui and after_dui:
                return before_dui[-1], after_dui[0]
            if before_dui and ("对他的" in sentence or "对其" in sentence):
                influenced = next(
                    (item for item in persons if item.entity_id == "E001"),
                    persons[0],
                )
                return before_dui[-1], influenced
        return persons[0], persons[1]

    def _build_event(
        self,
        event_id: int,
        text_id: str,
        sentence_id: int,
        event_type: str,
        trigger: str,
        evidence: str,
        participants: List[Dict[str, str]],
        time: str = "",
        place: str = "",
        description: str = "",
    ) -> EventRecord:
        return EventRecord(
            event_id=f"EVT{event_id:03d}",
            text_id=text_id,
            sentence_id=sentence_id,
            event_type=event_type,
            trigger=trigger,
            evidence=evidence,
            participants=participants,
            time=time,
            place=place,
            description=description,
        )

    def _first_time(self, mentions: List[LinkedMention]) -> str:
        for mention in mentions:
            if mention.entity_type == "Time":
                return mention.mention
        return ""

    def _find_trigger(self, sentence: str, triggers: List[str]) -> str:
        lowered = sentence.lower()
        for trigger in triggers:
            if trigger.lower() in lowered:
                return trigger
        return ""

    def _contains_any(self, sentence: str, triggers: List[str]) -> bool:
        lowered = sentence.lower()
        return any(trigger.lower() in lowered for trigger in triggers)
