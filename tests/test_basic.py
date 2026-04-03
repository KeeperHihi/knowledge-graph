import unittest

from config import KB_DIR, RAW_DIR
from src.disambiguation.entity_linker import EntityLinker
from src.extraction.entity_extractor import EntityExtractor
from src.preprocess.cleaner import preprocess_raw_texts
from src.schema.types import Mention


class BasicPipelineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.extractor = EntityExtractor.from_kb_file(KB_DIR / "seed_entities.json")
        cls.linker = EntityLinker.from_kb_file(KB_DIR / "seed_entities.json")

    def test_mention_extraction_has_results(self) -> None:
        sentences = preprocess_raw_texts(RAW_DIR)
        mentions = self.extractor.extract(sentences)
        self.assertGreater(len(mentions), 0)

    def test_turing_aliases_link_to_same_entity(self) -> None:
        mentions = [
            Mention(
                text_id="case_1",
                sentence_id=1,
                mention="图灵",
                start=0,
                end=2,
                entity_type="Person",
                context="图灵在 Bletchley Park 参与破译工作。",
                method="gazetteer",
            ),
            Mention(
                text_id="case_2",
                sentence_id=1,
                mention="Alan Turing",
                start=0,
                end=12,
                entity_type="Person",
                context="Alan Turing studied at Princeton University.",
                method="gazetteer",
            ),
            Mention(
                text_id="case_3",
                sentence_id=1,
                mention="阿兰·图灵",
                start=0,
                end=5,
                entity_type="Person",
                context="阿兰·图灵提出了图灵机思想。",
                method="gazetteer",
            ),
        ]

        linked = [self.linker.link_mention(mention) for mention in mentions]
        entity_ids = {item.entity_id for item in linked}
        self.assertEqual(entity_ids, {"E001"})

    def test_cambridge_can_be_disambiguated(self) -> None:
        university_mention = Mention(
            text_id="case_4",
            sentence_id=1,
            mention="剑桥",
            start=3,
            end=5,
            entity_type="Place",
            context="图灵后来回到剑桥学习数学，并继续接触学院导师。",
            method="gazetteer",
        )
        city_mention = Mention(
            text_id="case_5",
            sentence_id=1,
            mention="剑桥",
            start=0,
            end=2,
            entity_type="Place",
            context="剑桥是一座位于英格兰东部的城市，也是一座大学城。",
            method="gazetteer",
        )

        university_link = self.linker.link_mention(university_mention)
        city_link = self.linker.link_mention(city_mention)

        self.assertEqual(university_link.entity_id, "E008")
        self.assertEqual(city_link.entity_id, "E011")


if __name__ == "__main__":
    unittest.main()
