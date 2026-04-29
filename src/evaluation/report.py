from collections import Counter
from typing import Dict, List

from src.schema.types import EventRecord, LinkedMention, Mention, RelationRecord


def build_report(
    raw_text_count: int,
    sentence_count: int,
    mentions: List[Mention],
    linked_mentions: List[LinkedMention],
    relations: List[RelationRecord],
    events: List[EventRecord],
    unique_entity_count: int,
    source_map: Dict[str, dict],
) -> dict:
    mention_type_counts = Counter(mention.entity_type for mention in mentions)
    linked_type_counts = Counter(
        linked.resolved_entity_type
        for linked in linked_mentions
        if linked.status == "linked"
    )
    relation_type_counts = Counter(relation.relation for relation in relations)
    event_type_counts = Counter(event.event_type for event in events)

    text_statistics = []
    text_ids = sorted(
        {
            *[mention.text_id for mention in mentions],
            *[linked.text_id for linked in linked_mentions],
            *[relation.text_id for relation in relations],
            *[event.text_id for event in events],
        }
    )
    for text_id in text_ids:
        source_info = source_map.get(text_id, {})
        text_statistics.append(
            {
                "text_id": text_id,
                "source_title": source_info.get("source_title", ""),
                "source_url": source_info.get("source_url", ""),
                "sentence_count": len({mention.sentence_id for mention in mentions if mention.text_id == text_id}),
                "mention_count": sum(1 for mention in mentions if mention.text_id == text_id),
                "linked_count": sum(
                    1
                    for linked in linked_mentions
                    if linked.text_id == text_id and linked.status == "linked"
                ),
                "relation_count": sum(1 for relation in relations if relation.text_id == text_id),
                "event_count": sum(1 for event in events if event.text_id == text_id),
            }
        )

    return {
        "raw_text_count": raw_text_count,
        "sentence_count": sentence_count,
        "mention_count": len(mentions),
        "linked_count": sum(1 for item in linked_mentions if item.status == "linked"),
        "nil_count": sum(1 for item in linked_mentions if item.status == "NIL"),
        "unique_linked_entity_count": unique_entity_count,
        "relation_count": len(relations),
        "event_count": len(events),
        "source_count": len(source_map),
        "mention_type_counts": dict(mention_type_counts),
        "entity_type_counts": dict(linked_type_counts),
        "relation_type_counts": dict(relation_type_counts),
        "event_type_counts": dict(event_type_counts),
        "text_statistics": text_statistics,
    }
