from pathlib import Path

from config import INTERMEDIATE_DIR, KB_DIR, OUTPUT_DIR, RAW_DIR
from src.disambiguation.entity_linker import EntityLinker
from src.extraction.entity_extractor import EntityExtractor
from src.kg.exporter import export_outputs
from src.preprocess.cleaner import preprocess_raw_texts
from src.schema.types import Mention
from src.utils.io import load_entities, read_jsonl, read_text_files, write_jsonl


def run_extraction(
    raw_dir: Path = RAW_DIR,
    kb_path: Path = KB_DIR / "seed_entities.json",
    mention_path: Path = INTERMEDIATE_DIR / "mentions.jsonl",
) -> dict:
    sentences = preprocess_raw_texts(raw_dir)
    extractor = EntityExtractor.from_kb_file(kb_path)
    mentions = extractor.extract(sentences)
    write_jsonl(mention_path, [mention.to_dict() for mention in mentions])

    return {
        "mode": "extraction",
        "raw_text_count": len(read_text_files(raw_dir)),
        "sentence_count": len(sentences),
        "mention_count": len(mentions),
        "mentions_path": str(mention_path),
    }


def run_disambiguation(
    kb_path: Path = KB_DIR / "seed_entities.json",
    mention_path: Path = INTERMEDIATE_DIR / "mentions.jsonl",
    linked_path: Path = INTERMEDIATE_DIR / "linked_entities.jsonl",
) -> dict:
    mention_records = read_jsonl(mention_path)
    mentions = [Mention(**record) for record in mention_records]
    linker = EntityLinker.from_kb_file(kb_path)
    linked_mentions = linker.link_mentions(mentions)
    write_jsonl(linked_path, [linked.to_dict() for linked in linked_mentions])

    return {
        "mode": "disambiguation",
        "mention_count": len(mentions),
        "linked_count": sum(1 for item in linked_mentions if item.status == "linked"),
        "nil_count": sum(1 for item in linked_mentions if item.status == "NIL"),
        "linked_path": str(linked_path),
    }


def run_full_pipeline(
    raw_dir: Path = RAW_DIR,
    kb_path: Path = KB_DIR / "seed_entities.json",
    mention_path: Path = INTERMEDIATE_DIR / "mentions.jsonl",
    linked_path: Path = INTERMEDIATE_DIR / "linked_entities.jsonl",
    output_dir: Path = OUTPUT_DIR,
) -> dict:
    sentences = preprocess_raw_texts(raw_dir)
    raw_text_count = len(read_text_files(raw_dir))

    extractor = EntityExtractor.from_kb_file(kb_path)
    mentions = extractor.extract(sentences)
    write_jsonl(mention_path, [mention.to_dict() for mention in mentions])

    linker = EntityLinker.from_kb_file(kb_path)
    linked_mentions = linker.link_mentions(mentions)
    write_jsonl(linked_path, [linked.to_dict() for linked in linked_mentions])

    entities = load_entities(kb_path)
    entity_map = {entity.entity_id: entity for entity in entities}
    export_result = export_outputs(
        raw_text_count=raw_text_count,
        sentence_count=len(sentences),
        mentions=mentions,
        linked_mentions=linked_mentions,
        entity_map=entity_map,
        output_dir=output_dir,
    )

    return {
        "mode": "pipeline",
        "raw_text_count": raw_text_count,
        "sentence_count": len(sentences),
        "mention_count": len(mentions),
        "linked_count": sum(1 for item in linked_mentions if item.status == "linked"),
        "nil_count": sum(1 for item in linked_mentions if item.status == "NIL"),
        "mentions_path": str(mention_path),
        "linked_path": str(linked_path),
        **export_result,
    }
