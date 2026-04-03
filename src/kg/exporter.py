from pathlib import Path
from typing import Dict, List

from config import OUTPUT_DIR, TRIPLES_HEADER
from src.evaluation.report import build_report
from src.schema.types import Entity, LinkedMention, Mention
from src.utils.io import write_csv, write_json


def export_outputs(
    raw_text_count: int,
    sentence_count: int,
    mentions: List[Mention],
    linked_mentions: List[LinkedMention],
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
    write_csv(output_dir / "triples.csv", TRIPLES_HEADER, [])

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
        "triples_path": str(output_dir / "triples.csv"),
        "report_path": str(output_dir / "report.json"),
        "unique_entity_count": len(unique_entities),
    }
