import unittest

from src.evaluation.report import build_report
from src.kg.exporter import build_event_payloads, build_traceability_payload
from src.kg.graph_builder import GraphBuilder
from src.schema.types import Entity, EventRecord, LinkedMention, Mention, RelationRecord


class ReportingTestCase(unittest.TestCase):
    def test_report_and_traceability_keep_source_information(self) -> None:
        mentions = [
            Mention(
                text_id="text_demo",
                sentence_id=1,
                mention="图灵",
                start=0,
                end=2,
                entity_type="Person",
                context="图灵在剑桥学习数学。",
                method="gazetteer",
            )
        ]
        linked_mentions = [
            LinkedMention(
                text_id="text_demo",
                sentence_id=1,
                mention="图灵",
                start=0,
                end=2,
                entity_type="Person",
                context="图灵在剑桥学习数学。",
                method="gazetteer",
                entity_id="E001",
                canonical_name="Alan Turing",
                resolved_entity_type="Person",
                score=1.0,
                status="linked",
            )
        ]
        relations = [
            RelationRecord(
                relation_id="REL001",
                text_id="text_demo",
                sentence_id=1,
                head_id="E001",
                head_name="Alan Turing",
                head_type="Person",
                relation="studied_at",
                tail_id="E008",
                tail_name="University of Cambridge",
                tail_type="Organization",
                evidence="图灵在剑桥学习数学。",
                method="event_rule",
                trigger="学习",
            )
        ]
        events = [
            EventRecord(
                event_id="EVT001",
                text_id="text_demo",
                sentence_id=1,
                event_type="EducationEvent",
                trigger="学习",
                evidence="图灵在剑桥学习数学。",
                participants=[
                    {
                        "role": "student",
                        "entity_id": "E001",
                        "name": "Alan Turing",
                        "entity_type": "Person",
                    }
                ],
            )
        ]
        source_map = {
            "text_demo": {
                "text_id": "text_demo",
                "source_title": "Demo Source",
                "source_url": "https://example.com/demo",
                "note": "demo note",
            }
        }

        report = build_report(
            raw_text_count=1,
            sentence_count=1,
            mentions=mentions,
            linked_mentions=linked_mentions,
            relations=relations,
            events=events,
            unique_entity_count=1,
            source_map=source_map,
        )
        traceability = build_traceability_payload(
            mentions=mentions,
            linked_mentions=linked_mentions,
            relations=relations,
            events=events,
            source_map=source_map,
        )

        self.assertEqual(report["relation_count"], 1)
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(report["text_statistics"][0]["source_title"], "Demo Source")
        self.assertEqual(traceability["texts"][0]["source_url"], "https://example.com/demo")
        self.assertEqual(
            traceability["texts"][0]["relations"][0]["triple"],
            "Alan Turing - studied_at - University of Cambridge",
        )

        event_payload = build_event_payloads(events, source_map)
        self.assertEqual(event_payload[0]["source_title"], "Demo Source")
        self.assertEqual(event_payload[0]["source_url"], "https://example.com/demo")
        self.assertEqual(event_payload[0]["source_note"], "demo note")

        graph = GraphBuilder().build(
            entity_map={
                "E001": Entity(
                    entity_id="E001",
                    canonical_name="Alan Turing",
                    entity_type="Person",
                    aliases=["图灵"],
                    keywords=["数学"],
                    description="测试实体",
                )
            },
            linked_mentions=linked_mentions,
            relations=relations,
            events=events,
            source_map=source_map,
        )
        self.assertEqual(graph["events"][0]["source_title"], "Demo Source")
        self.assertEqual(graph["events"][0]["source_url"], "https://example.com/demo")


if __name__ == "__main__":
    unittest.main()
