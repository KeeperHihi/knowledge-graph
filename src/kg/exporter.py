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
    explainability = build_explainability_payload(
        mentions=mentions,
        linked_mentions=linked_mentions,
        events=events,
        relations=relations,
        source_map=source_map,
    )
    write_json(output_dir / "explainability.json", explainability)

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
        "explainability_path": str(output_dir / "explainability.json"),
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


def build_explainability_payload(
    linked_mentions: List[LinkedMention],
    events: List[EventRecord],
    relations: List[RelationRecord],
    source_map: Dict[str, dict],
    mentions: List[Mention] | None = None,
) -> dict:
    entity_extraction_cases = build_entity_extraction_cases(mentions or [], source_map)
    disambiguation_cases = build_disambiguation_cases(linked_mentions, source_map)
    event_relation_cases = build_event_relation_cases(events, relations, source_map)
    relation_extraction_cases = build_relation_extraction_cases(relations, source_map)
    return {
        "scoring_formula": {
            "alias_weight": 0.5,
            "context_keyword_weight": 0.3,
            "type_prior_weight": 0.2,
        },
        "entity_extraction_cases": entity_extraction_cases,
        "disambiguation_cases": disambiguation_cases,
        "event_extraction_cases": event_relation_cases,
        "relation_extraction_cases": relation_extraction_cases,
        "event_relation_cases": event_relation_cases,
    }


def build_entity_extraction_cases(mentions: List[Mention], source_map: Dict[str, dict]) -> List[dict]:
    grouped_mentions = {}
    for mention in mentions:
        key = (mention.text_id, mention.sentence_id, mention.context)
        grouped_mentions.setdefault(key, []).append(mention)

    preferred_keys = [
        ("text_01_biography", 2),
        ("text_04_test_and_machine", 2),
        ("text_08_bletchley_team", 1),
    ]
    picked_key = None
    for text_id, sentence_id in preferred_keys:
        picked_key = next(
            (
                key
                for key, items in grouped_mentions.items()
                if key[0] == text_id and key[1] == sentence_id and len(items) >= 3
            ),
            None,
        )
        if picked_key is not None:
            break

    if picked_key is None and grouped_mentions:
        picked_key = max(grouped_mentions, key=lambda key: len(grouped_mentions[key]))

    if picked_key is None:
        return []

    text_id, sentence_id, context = picked_key
    source_info = source_map.get(text_id, {})
    picked_mentions = sorted(grouped_mentions[picked_key], key=lambda item: item.start)
    return [
        {
            "case_id": "ENTITY01",
            "title": "从原始句子里找实体",
            "text_id": text_id,
            "sentence_id": sentence_id,
            "context": context,
            "mentions": [
                {
                    "mention": mention.mention,
                    "entity_type": mention.entity_type,
                    "method": mention.method,
                    "start": mention.start,
                    "end": mention.end,
                    "rule_note": "词典匹配" if mention.method == "gazetteer" else "正则匹配",
                }
                for mention in picked_mentions
            ],
            "source_title": source_info.get("source_title", ""),
            "source_url": source_info.get("source_url", ""),
        }
    ]


def build_disambiguation_cases(
    linked_mentions: List[LinkedMention], source_map: Dict[str, dict]
) -> List[dict]:
    preferred_rules = [
        ("text_03_cambridge_manchester", "Cambridge"),
        ("text_01_biography", "剑桥大学"),
        ("text_05_places", "Cambridge"),
        ("text_05_places", "Princeton"),
    ]
    picked_cases = []
    seen = set()

    for text_id, mention_text in preferred_rules:
        case = next(
            (
                linked
                for linked in linked_mentions
                if linked.text_id == text_id
                and linked.mention == mention_text
                and len(linked.candidate_details) > 1
            ),
            None,
        )
        if case is None:
            continue
        case_key = (case.text_id, case.sentence_id, case.start, case.end)
        if case_key in seen:
            continue
        seen.add(case_key)
        picked_cases.append(case)

    if len(picked_cases) < 2:
        fallback_cases = sorted(
            (
                linked
                for linked in linked_mentions
                if len(linked.candidate_details) > 1 and linked.status == "linked"
            ),
            key=lambda item: (-len(item.candidate_details), item.text_id, item.sentence_id, item.start),
        )
        for case in fallback_cases:
            case_key = (case.text_id, case.sentence_id, case.start, case.end)
            if case_key in seen:
                continue
            seen.add(case_key)
            picked_cases.append(case)
            if len(picked_cases) >= 3:
                break

    payload = []
    for index, linked in enumerate(picked_cases[:3], start=1):
        source_info = source_map.get(linked.text_id, {})
        ranked_candidates = sorted(
            linked.candidate_details,
            key=lambda item: item["final_score"],
            reverse=True,
        )
        payload.append(
            {
                "case_id": f"DISAMBIG{index:02d}",
                "title": f"{linked.mention} 的消歧过程",
                "mention": linked.mention,
                "text_id": linked.text_id,
                "sentence_id": linked.sentence_id,
                "context": linked.context,
                "status": linked.status,
                "selected_entity_id": linked.entity_id,
                "selected_name": linked.canonical_name,
                "selected_type": linked.resolved_entity_type,
                "selected_score": linked.score,
                "selected_reason": "综合别名匹配、上下文关键词和类型一致性后，最终分数最高。",
                "candidates": ranked_candidates,
                "source_title": source_info.get("source_title", ""),
                "source_url": source_info.get("source_url", ""),
            }
        )
    return payload


def build_event_relation_cases(
    events: List[EventRecord],
    relations: List[RelationRecord],
    source_map: Dict[str, dict],
) -> List[dict]:
    relations_by_event = {}
    for relation in relations:
        if not relation.source_event_id:
            continue
        relations_by_event.setdefault(relation.source_event_id, []).append(relation)

    preferred_rules = [
        ("text_01_biography", "PublicationEvent"),
        ("text_03_cambridge_manchester", "EducationEvent"),
        ("text_08_bletchley_team", "EmploymentEvent"),
        ("text_11_late_life", "EmploymentEvent"),
    ]
    picked_events = []
    seen = set()

    for text_id, event_type in preferred_rules:
        event = next(
            (
                item
                for item in events
                if item.text_id == text_id
                and item.event_type == event_type
                and relations_by_event.get(item.event_id)
            ),
            None,
        )
        if event is None or event.event_id in seen:
            continue
        seen.add(event.event_id)
        picked_events.append(event)

    if len(picked_events) < 2:
        fallback_events = [
            item for item in events if item.event_id in relations_by_event and item.event_id not in seen
        ]
        for event in fallback_events:
            seen.add(event.event_id)
            picked_events.append(event)
            if len(picked_events) >= 4:
                break

    payload = []
    for index, event in enumerate(picked_events[:4], start=1):
        source_info = source_map.get(event.text_id, {})
        event_relations = relations_by_event.get(event.event_id, [])
        payload.append(
            {
                "case_id": f"EVENTCHAIN{index:02d}",
                "title": f"{event.event_type} 如何生成关系",
                "text_id": event.text_id,
                "sentence_id": event.sentence_id,
                "evidence": event.evidence,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "trigger": event.trigger,
                "participants": event.participants,
                "relations": [
                    {
                        "relation_id": relation.relation_id,
                        "triple": f"{relation.head_name} - {relation.relation} - {relation.tail_name}",
                        "method": relation.method,
                        "trigger": relation.trigger,
                    }
                    for relation in event_relations
                ],
                "source_title": source_info.get("source_title", ""),
                "source_url": source_info.get("source_url", ""),
            }
        )
    return payload


def build_relation_extraction_cases(
    relations: List[RelationRecord],
    source_map: Dict[str, dict],
) -> List[dict]:
    preferred_rules = [
        ("text_01_biography", "published"),
        ("text_01_biography", "proposed"),
        ("text_08_bletchley_team", "worked_at"),
        ("text_10_manchester_test", "worked_at"),
    ]
    picked_relation = None
    for text_id, relation_name in preferred_rules:
        picked_relation = next(
            (
                relation
                for relation in relations
                if relation.text_id == text_id and relation.relation == relation_name
            ),
            None,
        )
        if picked_relation is not None:
            break

    if picked_relation is None and relations:
        picked_relation = relations[0]

    if picked_relation is None:
        return []

    source_info = source_map.get(picked_relation.text_id, {})
    return [
        {
            "case_id": "RELATION01",
            "title": "从事件和规则生成三元组",
            "relation_id": picked_relation.relation_id,
            "text_id": picked_relation.text_id,
            "sentence_id": picked_relation.sentence_id,
            "head_name": picked_relation.head_name,
            "head_type": picked_relation.head_type,
            "relation": picked_relation.relation,
            "tail_name": picked_relation.tail_name,
            "tail_type": picked_relation.tail_type,
            "triple": (
                f"{picked_relation.head_name} - {picked_relation.relation} - "
                f"{picked_relation.tail_name}"
            ),
            "trigger": picked_relation.trigger,
            "method": picked_relation.method,
            "source_event_id": picked_relation.source_event_id,
            "evidence": picked_relation.evidence,
            "source_title": source_info.get("source_title", ""),
            "source_url": source_info.get("source_url", ""),
        }
    ]
