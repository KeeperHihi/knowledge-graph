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
    source_map: Dict[str, dict],
    output_dir: Path = OUTPUT_DIR,
) -> dict:
    unique_entities = {}
    for linked in linked_mentions:
        if linked.status == "linked" and linked.entity_id in entity_map:
            unique_entities[linked.entity_id] = entity_map[linked.entity_id]
    event_payload = build_event_payloads(events, source_map)

    entity_payload = [
        unique_entities[entity_id].to_dict() for entity_id in sorted(unique_entities)
    ]
    write_json(output_dir / "entities.json", entity_payload)
    write_json(output_dir / "events.json", event_payload)
    write_json(output_dir / "graph.json", graph)
    write_json(output_dir / "nodes.json", graph["nodes"])
    write_json(output_dir / "edges.json", graph["edges"])
    traceability = build_traceability_payload(
        mentions=mentions,
        linked_mentions=linked_mentions,
        relations=relations,
        events=events,
        source_map=source_map,
    )
    write_json(output_dir / "traceability.json", traceability)

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
        relations=relations,
        events=events,
        unique_entity_count=len(unique_entities),
        source_map=source_map,
    )
    write_json(output_dir / "report.json", report)

    return {
        "entities_path": str(output_dir / "entities.json"),
        "events_path": str(output_dir / "events.json"),
        "relations_path": str(output_dir / "relations.csv"),
        "triples_path": str(output_dir / "triples.csv"),
        "graph_path": str(output_dir / "graph.json"),
        "traceability_path": str(output_dir / "traceability.json"),
        "report_path": str(output_dir / "report.json"),
        "unique_entity_count": len(unique_entities),
        "relation_count": len(relations),
        "event_count": len(events),
    }


def build_traceability_payload(
    mentions: List[Mention],
    linked_mentions: List[LinkedMention],
    relations: List[RelationRecord],
    events: List[EventRecord],
    source_map: Dict[str, dict],
) -> dict:
    text_trace = []
    for text_id in sorted(source_map):
        source_info = source_map[text_id]
        text_trace.append(
            {
                "text_id": text_id,
                "source_title": source_info.get("source_title", ""),
                "source_url": source_info.get("source_url", ""),
                "collected_on": source_info.get("collected_on", ""),
                "note": source_info.get("note", ""),
                "mention_count": sum(1 for mention in mentions if mention.text_id == text_id),
                "linked_count": sum(
                    1
                    for linked in linked_mentions
                    if linked.text_id == text_id and linked.status == "linked"
                ),
                "relation_count": sum(1 for relation in relations if relation.text_id == text_id),
                "event_count": sum(1 for event in events if event.text_id == text_id),
                "relations": [
                    {
                        "relation_id": relation.relation_id,
                        "triple": f"{relation.head_name} - {relation.relation} - {relation.tail_name}",
                        "evidence": relation.evidence,
                    }
                    for relation in relations
                    if relation.text_id == text_id
                ][:4],
                "events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "trigger": event.trigger,
                        "evidence": event.evidence,
                    }
                    for event in events
                    if event.text_id == text_id
                ][:4],
            }
        )

    return {"texts": text_trace}


def build_event_payloads(events: List[EventRecord], source_map: Dict[str, dict]) -> List[dict]:
    payload = []
    for event in events:
        source_info = source_map.get(event.text_id, {})
        item = event.to_dict()
        item["source_title"] = source_info.get("source_title", "")
        item["source_url"] = source_info.get("source_url", "")
        item["collected_on"] = source_info.get("collected_on", "")
        item["source_note"] = source_info.get("note", "")
        payload.append(item)
    return payload
