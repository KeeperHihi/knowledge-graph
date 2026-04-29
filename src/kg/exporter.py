from pathlib import Path
from typing import Dict, List

from config import OUTPUT_DIR, RELATIONS_HEADER, TRIPLES_HEADER
from src.evaluation.report import build_report
from src.schema.types import Entity, EventRecord, LinkedMention, Mention, RelationRecord
from src.utils.io import write_csv, write_json


def export_outputs(
    raw_text_count: int,
    sentence_count: int,
    mentions: List[Mention],
    linked_mentions: List[LinkedMention],
    relations: List[RelationRecord],
    events: List[EventRecord],
    graph: dict,
    entity_map: Dict[str, Entity],
    output_dir: Path = OUTPUT_DIR,
) -> dict:
    unique_entities = {}
    for linked in linked_mentions:
        if linked.status == "linked" and linked.entity_id in entity_map:
            unique_entities[linked.entity_id] = entity_map[linked.entity_id]

    entity_payload = [
        unique_entities[entity_id].to_dict() for entity_id in sorted(unique_entities)
    ]
    write_json(output_dir / "entities.json", entity_payload)
    write_json(output_dir / "events.json", [event.to_dict() for event in events])
    write_json(output_dir / "graph.json", graph)
    write_json(output_dir / "nodes.json", graph["nodes"])
    write_json(output_dir / "edges.json", graph["edges"])

    relation_rows = [
        [
            relation.relation_id,
            relation.text_id,
            relation.sentence_id,
            relation.head_id,
            relation.head_name,
            relation.head_type,
            relation.relation,
            relation.tail_id,
            relation.tail_name,
            relation.tail_type,
            relation.trigger,
            relation.method,
            relation.source_event_id,
            relation.evidence,
        ]
        for relation in relations
    ]
    write_csv(output_dir / "relations.csv", RELATIONS_HEADER, relation_rows)

    triple_rows = [
        [relation.head_name, relation.relation, relation.tail_name, relation.evidence]
        for relation in relations
    ]
    write_csv(output_dir / "triples.csv", TRIPLES_HEADER, triple_rows)

    report = build_report(
        raw_text_count=raw_text_count,
        sentence_count=sentence_count,
        mentions=mentions,
        linked_mentions=linked_mentions,
        unique_entity_count=len(unique_entities),
    )
    write_json(output_dir / "report.json", report)

    return {
        "entities_path": str(output_dir / "entities.json"),
        "events_path": str(output_dir / "events.json"),
        "relations_path": str(output_dir / "relations.csv"),
        "triples_path": str(output_dir / "triples.csv"),
        "graph_path": str(output_dir / "graph.json"),
        "report_path": str(output_dir / "report.json"),
        "unique_entity_count": len(unique_entities),
        "relation_count": len(relations),
        "event_count": len(events),
    }
