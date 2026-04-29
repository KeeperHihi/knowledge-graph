from typing import Dict, List

from src.schema.types import Entity, EventRecord, LinkedMention, RelationRecord


class GraphBuilder:
    def build(
        self,
        entity_map: Dict[str, Entity],
        linked_mentions: List[LinkedMention],
        relations: List[RelationRecord],
        events: List[EventRecord],
        source_map: Dict[str, dict],
    ) -> dict:
        nodes = {}
        edges = []
        entity_mentions: Dict[str, List[LinkedMention]] = {}

        for mention in linked_mentions:
            if mention.status != "linked":
                continue
            entity_mentions.setdefault(mention.entity_id, []).append(mention)

        for mention in linked_mentions:
            if mention.status != "linked" or mention.entity_id not in entity_map:
                continue
            entity = entity_map[mention.entity_id]
            mention_records = entity_mentions.get(entity.entity_id, [])
            nodes[entity.entity_id] = {
                "id": entity.entity_id,
                "label": entity.canonical_name,
                "type": entity.entity_type,
                "description": entity.description,
                "source": "entity",
                "mention_count": len(mention_records),
                "text_ids": sorted({item.text_id for item in mention_records}),
                "evidence_samples": self._build_entity_evidence_samples(mention_records, source_map),
            }

        for event in events:
            source_info = source_map.get(event.text_id, {})
            nodes[event.event_id] = {
                "id": event.event_id,
                "label": event.event_type,
                "type": "EventNode",
                "description": event.description,
                "source": "event",
                "time": event.time,
                "place": event.place,
                "evidence": event.evidence,
                "text_id": event.text_id,
                "sentence_id": event.sentence_id,
                "source_title": source_info.get("source_title", ""),
                "source_url": source_info.get("source_url", ""),
                "collected_on": source_info.get("collected_on", ""),
                "source_note": source_info.get("note", ""),
            }
            for participant in event.participants:
                if participant["entity_id"] not in nodes:
                    continue
                edges.append(
                    {
                        "id": f"{event.event_id}_{participant['entity_id']}",
                        "source": event.event_id,
                        "target": participant["entity_id"],
                        "label": participant["role"],
                        "kind": "event_participant",
                        "evidence": event.evidence,
                        "event_id": event.event_id,
                        "text_id": event.text_id,
                        "sentence_id": event.sentence_id,
                        "source_title": source_info.get("source_title", ""),
                        "source_url": source_info.get("source_url", ""),
                        "collected_on": source_info.get("collected_on", ""),
                        "source_note": source_info.get("note", ""),
                    }
                )

        for relation in relations:
            source_info = source_map.get(relation.text_id, {})
            edges.append(
                {
                    "id": relation.relation_id,
                    "source": relation.head_id,
                    "target": relation.tail_id,
                    "label": relation.relation,
                    "kind": "relation",
                    "evidence": relation.evidence,
                    "trigger": relation.trigger,
                    "event_id": relation.source_event_id,
                    "text_id": relation.text_id,
                    "sentence_id": relation.sentence_id,
                    "source_title": source_info.get("source_title", ""),
                    "source_url": source_info.get("source_url", ""),
                    "collected_on": source_info.get("collected_on", ""),
                    "source_note": source_info.get("note", ""),
                }
            )

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "events": [self._build_event_payload(event, source_map) for event in events],
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "event_count": len(events),
                "relation_count": len(relations),
            },
        }

    def _build_event_payload(self, event: EventRecord, source_map: Dict[str, dict]) -> dict:
        source_info = source_map.get(event.text_id, {})
        payload = event.to_dict()
        payload["source_title"] = source_info.get("source_title", "")
        payload["source_url"] = source_info.get("source_url", "")
        payload["collected_on"] = source_info.get("collected_on", "")
        payload["source_note"] = source_info.get("note", "")
        return payload

    def _build_entity_evidence_samples(
        self, mention_records: List[LinkedMention], source_map: Dict[str, dict]
    ) -> List[dict]:
        samples = []
        seen = set()
        for mention in mention_records:
            key = (mention.text_id, mention.sentence_id)
            if key in seen:
                continue
            seen.add(key)
            source_info = source_map.get(mention.text_id, {})
            samples.append(
                {
                    "text_id": mention.text_id,
                    "sentence_id": mention.sentence_id,
                    "evidence": mention.context,
                    "source_title": source_info.get("source_title", ""),
                    "source_url": source_info.get("source_url", ""),
                }
            )
            if len(samples) >= 3:
                break
        return samples
