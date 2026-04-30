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

    def test_publication_event_generates_published_relation(self) -> None:
        sentence = "Alan Turing 在 1936 年发表了《Computable Numbers》，并提出了 Turing Machine 的经典思想。"
        mentions = [
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", sentence, 0, 12),
            make_linked("《Computable Numbers》", "E019", "Computable Numbers", "Work", sentence, 19, 39),
            make_linked("Turing Machine", "E017", "Turing Machine", "Concept", sentence, 45, 59),
        ]

        events = self.event_extractor.extract(mentions)
        relations = self.relation_extractor.extract(mentions, events)

        self.assertTrue(any(event.event_type == "PublicationEvent" for event in events))
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "published"
                and relation.tail_name == "Computable Numbers"
                for relation in relations
            )
        )

    def test_education_relation_does_not_point_to_city(self) -> None:
        sentence = "Alan Turing 在 University of Cambridge 学习数学，Cambridge 这座城市则是他的求学背景。"
        mentions = [
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", sentence, 0, 12),
            make_linked(
                "University of Cambridge",
                "E008",
                "University of Cambridge",
                "Organization",
                sentence,
                15,
                39,
            ),
            make_linked("Cambridge", "E011", "Cambridge", "Place", sentence, 44, 53),
        ]

        events = self.event_extractor.extract(mentions)
        relations = self.relation_extractor.extract(mentions, events)

        self.assertTrue(any(event.event_type == "EducationEvent" for event in events))
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "studied_at"
                and relation.tail_name == "University of Cambridge"
                for relation in relations
            )
        )
        self.assertFalse(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "studied_at"
                and relation.tail_name == "Cambridge"
                for relation in relations
            )
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

        self.assertTrue(any(event.event_type == "EducationEvent" for event in events))
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "studied_at"
                and relation.tail_name == "Sherborne School"
                for relation in relations
            )
        )
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "influenced_by"
                and relation.tail_name == "Christopher Morcom"
                for relation in relations
            )
        )

    def test_employment_relation_does_not_point_to_city(self) -> None:
        sentence = "Alan Turing 晚年仍在 University of Manchester 工作，Wilmslow 是他的居住地。"
        mentions = [
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", sentence, 0, 12),
            make_linked(
                "University of Manchester",
                "E009",
                "University of Manchester",
                "Organization",
                sentence,
                18,
                42,
            ),
            make_linked("Wilmslow", "E031", "Wilmslow", "Place", sentence, 46, 54),
        ]

        events = self.event_extractor.extract(mentions)
        relations = self.relation_extractor.extract(mentions, events)

        self.assertTrue(any(event.event_type == "EmploymentEvent" for event in events))
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "worked_at"
                and relation.tail_name == "University of Manchester"
                for relation in relations
            )
        )
        self.assertFalse(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "worked_at"
                and relation.tail_name == "Wilmslow"
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

    def test_device_sentences_can_link_bombe_and_mark_i(self) -> None:
        bombe_sentence = "1940 年前后，Alan Turing 在 Bletchley Park 使用 Bombe 辅助破解 Enigma 密码。"
        bombe_mentions = [
            make_linked("1940 年", "T1940", "1940 年", "Time", bombe_sentence, 0, 6, text_id="device_case", sentence_id=1),
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", bombe_sentence, 10, 22, text_id="device_case", sentence_id=1),
            make_linked("Bletchley Park", "E010", "Bletchley Park", "Place", bombe_sentence, 25, 39, text_id="device_case", sentence_id=1),
            make_linked("Bombe", "E016", "Bombe", "Device", bombe_sentence, 43, 48, text_id="device_case", sentence_id=1),
            make_linked("Enigma", "E015", "Enigma", "Device", bombe_sentence, 54, 60, text_id="device_case", sentence_id=1),
        ]
        mark_i_sentence = "1948 年后，Alan Turing 在 University of Manchester 工作，并设计 Manchester Mark I 的程序检查方法。"
        mark_i_mentions = [
            make_linked("1948 年", "T1948", "1948 年", "Time", mark_i_sentence, 0, 6, text_id="device_case", sentence_id=2),
            make_linked("Alan Turing", "E001", "Alan Turing", "Person", mark_i_sentence, 8, 20, text_id="device_case", sentence_id=2),
            make_linked(
                "University of Manchester",
                "E009",
                "University of Manchester",
                "Organization",
                mark_i_sentence,
                23,
                47,
                text_id="device_case",
                sentence_id=2,
            ),
            make_linked(
                "Manchester Mark I",
                "E025",
                "Manchester Mark I",
                "Device",
                mark_i_sentence,
                54,
                71,
                text_id="device_case",
                sentence_id=2,
            ),
        ]

        events = self.event_extractor.extract(bombe_mentions + mark_i_mentions)
        relations = self.relation_extractor.extract(bombe_mentions + mark_i_mentions, events)

        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "used"
                and relation.tail_name == "Bombe"
                for relation in relations
            )
        )
        self.assertTrue(
            any(
                relation.head_name == "Alan Turing"
                and relation.relation == "proposed"
                and relation.tail_name == "Manchester Mark I"
                for relation in relations
            )
        )


if __name__ == "__main__":
    unittest.main()
