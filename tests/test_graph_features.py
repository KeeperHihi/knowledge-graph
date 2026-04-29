import unittest

from src.extraction.event_extractor import EventExtractor
from src.extraction.relation_extractor import RelationExtractor
from src.schema.types import LinkedMention


def make_linked(
    mention: str,
    entity_id: str,
    canonical_name: str,
    resolved_entity_type: str,
    context: str,
    start: int,
    end: int,
    text_id: str = "case",
    sentence_id: int = 1,
    entity_type: str | None = None,
) -> LinkedMention:
    return LinkedMention(
        text_id=text_id,
        sentence_id=sentence_id,
        mention=mention,
        start=start,
        end=end,
        entity_type=entity_type or resolved_entity_type,
        context=context,
        method="gazetteer",
        entity_id=entity_id,
        canonical_name=canonical_name,
        resolved_entity_type=resolved_entity_type,
        score=1.0,
        status="linked",
    )


class GraphFeatureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.event_extractor = EventExtractor()
        self.relation_extractor = RelationExtractor()

    def test_education_event_can_keep_two_schools(self) -> None:
        sentence = "Alan Turing 曾就读于剑桥大学，后来前往 Princeton University 攻读博士学位。"
        mentions = [
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", sentence, 0, 12),
            make_linked("剑桥大学", "E008", "University of Cambridge", "Organization", sentence, 17, 21),
            make_linked(
                "Princeton University",
                "E007",
                "Princeton University",
                "Organization",
                sentence,
                29,
                49,
            ),
        ]

        events = self.event_extractor.extract(mentions)
        relations = self.relation_extractor.extract(mentions, events)

        studied_targets = {
            relation.tail_name
            for relation in relations
            if relation.head_name == "Alan Turing" and relation.relation == "studied_at"
        }
        self.assertEqual(
            studied_targets,
            {"University of Cambridge", "Princeton University"},
        )

    def test_influence_direction_prefers_the_person_before_dui(self) -> None:
        sentence = "图灵在 Sherborne School 接受中学教育，青年时期的朋友 Christopher Morcom 对他的科学兴趣影响很大。"
        mentions = [
            make_linked("图灵", "E001", "Alan Turing", "Person", sentence, 0, 2),
            make_linked(
                "Sherborne School",
                "E028",
                "Sherborne School",
                "Organization",
                sentence,
                5,
                21,
            ),
            make_linked(
                "Christopher Morcom",
                "E006",
                "Christopher Morcom",
                "Person",
                sentence,
                34,
                53,
            ),
        ]

        events = self.event_extractor.extract(mentions)
        relations = self.relation_extractor.extract(mentions, events)

        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "influenced_by"
                and relation.tail_name == "Christopher Morcom"
                for relation in relations
            )
        )

    def test_location_rule_needs_place_after_the_trigger(self) -> None:
        wrong_sentence = "Cambridge 很有名，而 Princeton University 常被简称为 Princeton。"
        wrong_mentions = [
            make_linked("Cambridge", "E011", "Cambridge", "Place", wrong_sentence, 0, 9),
            make_linked(
                "Princeton University",
                "E007",
                "Princeton University",
                "Organization",
                wrong_sentence,
                14,
                34,
            ),
        ]
        right_sentence = "University of Manchester 位于 Manchester。"
        right_mentions = [
            make_linked(
                "University of Manchester",
                "E009",
                "University of Manchester",
                "Organization",
                right_sentence,
                0,
                24,
            ),
            make_linked("Manchester", "E012", "Manchester", "Place", right_sentence, 28, 38),
        ]

        wrong_relations = self.relation_extractor.extract(wrong_mentions, [])
        right_relations = self.relation_extractor.extract(right_mentions, [])

        self.assertEqual(len(wrong_relations), 0)
        self.assertTrue(
            any(
                relation.relation == "located_in"
                and relation.head_name == "University of Manchester"
                and relation.tail_name == "Manchester"
                for relation in right_relations
            )
        )


if __name__ == "__main__":
    unittest.main()
