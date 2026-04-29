from typing import Dict, List

from src.schema.types import Entity, EventRecord, LinkedMention, RelationRecord


class GraphBuilder:
    def build(
        self,
        entity_map: Dict[str, Entity],
        linked_mentions: List[LinkedMention],
        relations: List[RelationRecord],
        events: List[EventRecord],
    ) -> dict:
        nodes = {}
        edges = []

        for mention in linked_mentions:
            if mention.status != "linked" or mention.entity_id not in entity_map:
                continue
            entity = entity_map[mention.entity_id]
            nodes[entity.entity_id] = {
                "id": entity.entity_id,
                "label": entity.canonical_name,
                "type": entity.entity_type,
                "description": entity.description,
                "source": "entity",
            }

        for event in events:
            nodes[event.event_id] = {
                "id": event.event_id,
                "label": event.event_type,
                "type": "EventNode",
                "description": event.description,
                "source": "event",
                "time": event.time,
                "place": event.place,
                "evidence": event.evidence,
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
                    }
                )

        for relation in relations:
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
                }
            )

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "events": [event.to_dict() for event in events],
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "event_count": len(events),
                "relation_count": len(relations),
            },
        }
