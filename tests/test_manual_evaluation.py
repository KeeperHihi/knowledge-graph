import unittest

from src.evaluation.manual_eval import (
    evaluate_entity_linking,
    evaluate_events,
    evaluate_relations,
)


class ManualEvaluationTestCase(unittest.TestCase):
    def test_manual_evaluation_summary_fields_exist(self) -> None:
        entity_result = evaluate_entity_linking(
            gold_cases=[
                {
                    "case_id": "EL001",
                    "text_id": "text_demo",
                    "sentence_id": 1,
                    "mention": "剑桥",
                    "expected_entity_id": "E011",
                    "expected_name": "Cambridge",
                }
            ],
            linked_mentions=[
                {
                    "text_id": "text_demo",
                    "sentence_id": 1,
                    "mention": "剑桥",
                    "entity_id": "E011",
                    "canonical_name": "Cambridge",
                    "candidate_details": [
                        {"canonical_name": "Cambridge", "final_score": 0.85},
                        {"canonical_name": "University of Cambridge", "final_score": 0.79},
                    ],
                }
            ],
        )
        relation_result = evaluate_relations(
            gold_cases=[
                {
                    "case_id": "REL001",
                    "text_id": "text_demo",
                    "sentence_id": 1,
                    "head_name": "Alan Turing",
                    "relation": "studied_at",
                    "tail_name": "University of Cambridge",
                }
            ],
            relations=[
                {
                    "text_id": "text_demo",
                    "sentence_id": "1",
                    "head_name": "Alan Turing",
                    "relation": "studied_at",
                    "tail_name": "University of Cambridge",
                }
            ],
        )
        event_result = evaluate_events(
            gold_cases=[
                {
                    "case_id": "EV001",
                    "text_id": "text_demo",
                    "sentence_id": 1,
                    "event_type": "EducationEvent",
                }
            ],
            events=[
                {
                    "text_id": "text_demo",
                    "sentence_id": 1,
                    "event_type": "EducationEvent",
                }
            ],
        )

        self.assertEqual(entity_result["accuracy"], 1.0)
        self.assertEqual(relation_result["hit_rate"], 1.0)
        self.assertEqual(event_result["hit_rate"], 1.0)
        self.assertIn("key_finding", entity_result)
        self.assertIn("key_finding", relation_result)
        self.assertIn("key_finding", event_result)


if __name__ == "__main__":
    unittest.main()
