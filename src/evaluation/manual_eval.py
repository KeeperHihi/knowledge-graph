import csv
from pathlib import Path
from typing import Dict, List

from config import INTERMEDIATE_DIR, OUTPUT_DIR
from src.utils.io import read_json, read_jsonl, write_json


def evaluate_entity_linking(gold_cases: List[dict], linked_mentions: List[dict]) -> dict:
    mention_map = {
        (item["text_id"], item["sentence_id"], item["mention"]): item for item in linked_mentions
    }
    checked_cases = []
    correct = 0
    closest_case = None

    for gold in gold_cases:
        predicted = mention_map.get((gold["text_id"], gold["sentence_id"], gold["mention"]))
        matched = bool(predicted and predicted["entity_id"] == gold["expected_entity_id"])
        if matched:
            correct += 1

        score_gap = None
        if predicted and predicted.get("candidate_details"):
            ranked = sorted(
                predicted["candidate_details"],
                key=lambda item: item["final_score"],
                reverse=True,
            )
            if len(ranked) >= 2:
                score_gap = round(ranked[0]["final_score"] - ranked[1]["final_score"], 4)
                if closest_case is None or score_gap < closest_case["score_gap"]:
                    closest_case = {
                        "mention": gold["mention"],
                        "text_id": gold["text_id"],
                        "score_gap": score_gap,
                        "selected_name": predicted["canonical_name"],
                    }

        checked_cases.append(
            {
                "case_id": gold["case_id"],
                "mention": gold["mention"],
                "expected_name": gold["expected_name"],
                "predicted_name": predicted["canonical_name"] if predicted else "未找到",
                "matched": matched,
                "note": gold.get("note", ""),
            }
        )

    total = len(gold_cases)
    accuracy = round(correct / total, 4) if total else 0.0
    key_finding = f"实体消歧小样本命中 {correct}/{total}。"
    if closest_case is not None:
        key_finding += (
            f" 其中最接近的一组是 {closest_case['mention']}，"
            f"当前胜出实体是 {closest_case['selected_name']}，分差只有 {closest_case['score_gap']:.2f}。"
        )

    return {
        "checked": total,
        "correct": correct,
        "accuracy": accuracy,
        "checked_cases": checked_cases,
        "key_finding": key_finding,
    }


def evaluate_relations(gold_cases: List[dict], relations: List[dict]) -> dict:
    predicted_set = {
        (item["text_id"], int(item["sentence_id"]), item["head_name"], item["relation"], item["tail_name"])
        for item in relations
    }
    checked_cases = []
    matched = 0
    misses = []

    for gold in gold_cases:
        key = (
            gold["text_id"],
            gold["sentence_id"],
            gold["head_name"],
            gold["relation"],
            gold["tail_name"],
        )
        is_matched = key in predicted_set
        if is_matched:
            matched += 1
        else:
            misses.append(gold)
        checked_cases.append(
            {
                "case_id": gold["case_id"],
                "triple": f"{gold['head_name']} - {gold['relation']} - {gold['tail_name']}",
                "matched": is_matched,
                "note": gold.get("note", ""),
            }
        )

    total = len(gold_cases)
    hit_rate = round(matched / total, 4) if total else 0.0
    key_finding = f"关系抽取小样本命中 {matched}/{total}。"
    error_analysis = []
    if misses:
        first_miss = misses[0]
        key_finding += f" 当前最明显的漏例是 {first_miss['tail_name']} 相关关系。"
        error_analysis.append(
            {
                "task": "relation_extraction",
                "text_id": first_miss["text_id"],
                "sentence_id": first_miss["sentence_id"],
                "expected": f"{first_miss['head_name']} - {first_miss['relation']} - {first_miss['tail_name']}",
                "reason": first_miss.get("note", ""),
            }
        )

    return {
        "checked": total,
        "matched": matched,
        "hit_rate": hit_rate,
        "checked_cases": checked_cases,
        "key_finding": key_finding,
        "error_analysis": error_analysis,
    }


def evaluate_events(gold_cases: List[dict], events: List[dict]) -> dict:
    predicted_set = {
        (item["text_id"], int(item["sentence_id"]), item["event_type"]) for item in events
    }
    checked_cases = []
    matched = 0
    misses = []

    for gold in gold_cases:
        key = (gold["text_id"], gold["sentence_id"], gold["event_type"])
        is_matched = key in predicted_set
        if is_matched:
            matched += 1
        else:
            misses.append(gold)
        checked_cases.append(
            {
                "case_id": gold["case_id"],
                "event_type": gold["event_type"],
                "text_id": gold["text_id"],
                "sentence_id": gold["sentence_id"],
                "matched": is_matched,
                "note": gold.get("note", ""),
            }
        )

    total = len(gold_cases)
    hit_rate = round(matched / total, 4) if total else 0.0
    key_finding = f"事件抽取小样本命中 {matched}/{total}。"
    error_analysis = []
    if misses:
        first_miss = misses[0]
        key_finding += f" 当前最明显的漏例是 {first_miss['event_type']}。"
        error_analysis.append(
            {
                "task": "event_extraction",
                "text_id": first_miss["text_id"],
                "sentence_id": first_miss["sentence_id"],
                "expected": first_miss["event_type"],
                "reason": first_miss.get("note", ""),
            }
        )

    return {
        "checked": total,
        "matched": matched,
        "hit_rate": hit_rate,
        "checked_cases": checked_cases,
        "key_finding": key_finding,
        "error_analysis": error_analysis,
    }


def load_relations_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def run_manual_evaluation(
    eval_dir: Path,
    linked_path: Path = INTERMEDIATE_DIR / "linked_entities.jsonl",
    relations_path: Path = OUTPUT_DIR / "relations.csv",
    events_path: Path = OUTPUT_DIR / "events.json",
    output_path: Path = OUTPUT_DIR / "evaluation_summary.json",
) -> dict:
    entity_gold = read_json(eval_dir / "entity_linking_gold.json")
    relation_gold = read_json(eval_dir / "relation_gold.json")
    event_gold = read_json(eval_dir / "event_gold.json")

    linked_mentions = read_jsonl(linked_path)
    relations = load_relations_csv(relations_path)
    events = read_json(events_path)

    entity_result = evaluate_entity_linking(entity_gold, linked_mentions)
    relation_result = evaluate_relations(relation_gold, relations)
    event_result = evaluate_events(event_gold, events)

    summary = {
        "entity_linking_accuracy": entity_result["accuracy"],
        "relation_hit_rate": relation_result["hit_rate"],
        "event_hit_rate": event_result["hit_rate"],
        "entity_linking": entity_result,
        "relation_extraction": relation_result,
        "event_extraction": event_result,
        "key_findings": [
            entity_result["key_finding"],
            relation_result["key_finding"],
            event_result["key_finding"],
        ],
        "error_analysis": relation_result["error_analysis"] + event_result["error_analysis"],
    }

    write_json(output_path, summary)
    return summary
