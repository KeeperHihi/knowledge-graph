from collections import Counter
from typing import List

from src.schema.types import LinkedMention, Mention


def build_report(
    raw_text_count: int,
    sentence_count: int,
    mentions: List[Mention],
    linked_mentions: List[LinkedMention],
    unique_entity_count: int,
) -> dict:
    mention_type_counts = Counter(mention.entity_type for mention in mentions)
    linked_type_counts = Counter(
        linked.resolved_entity_type
        for linked in linked_mentions
        if linked.status == "linked"
    )

    return {
        "raw_text_count": raw_text_count,
        "sentence_count": sentence_count,
        "mention_count": len(mentions),
        "linked_count": sum(1 for item in linked_mentions if item.status == "linked"),
        "nil_count": sum(1 for item in linked_mentions if item.status == "NIL"),
        "unique_linked_entity_count": unique_entity_count,
        "mention_type_counts": dict(mention_type_counts),
        "entity_type_counts": dict(linked_type_counts),
    }
