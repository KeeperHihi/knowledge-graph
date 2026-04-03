import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from config import ORGANIZATION_PATTERNS, TIME_PATTERNS, WORK_PATTERNS
from src.schema.types import Entity, Mention, SentenceRecord
from src.utils.io import load_entities


@dataclass(frozen=True)
class GazetteerEntry:
    alias: str
    entity_type: str


class EntityExtractor:
    def __init__(self, entities: List[Entity]):
        self.entities = entities
        self.gazetteer = self._build_gazetteer(entities)
        self.time_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in TIME_PATTERNS]
        self.organization_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in ORGANIZATION_PATTERNS
        ]
        self.work_patterns = [re.compile(pattern) for pattern in WORK_PATTERNS]

    @classmethod
    def from_kb_file(cls, kb_path: Path) -> "EntityExtractor":
        return cls(load_entities(kb_path))

    def _build_gazetteer(self, entities: List[Entity]) -> List[GazetteerEntry]:
        entries = {}
        for entity in entities:
            for alias in [entity.canonical_name, *entity.aliases]:
                alias = alias.strip()
                if len(alias) < 2:
                    continue
                key = (alias, entity.entity_type)
                entries[key] = GazetteerEntry(alias=alias, entity_type=entity.entity_type)

        return sorted(entries.values(), key=lambda item: len(item.alias), reverse=True)

    def extract(self, sentences: List[SentenceRecord]) -> List[Mention]:
        mentions: List[Mention] = []
        for sentence in sentences:
            mentions.extend(self.extract_from_sentence(sentence))
        return mentions

    def extract_from_sentence(self, sentence: SentenceRecord) -> List[Mention]:
        candidates: List[Mention] = []
        text = sentence.text

        for entry in self.gazetteer:
            # 直接做主名和别名匹配
            flags = re.IGNORECASE if re.search(r"[A-Za-z]", entry.alias) else 0
            for match in re.finditer(re.escape(entry.alias), text, flags):
                candidates.append(
                    Mention(
                        text_id=sentence.text_id,
                        sentence_id=sentence.sentence_id,
                        mention=match.group(),
                        start=match.start(),
                        end=match.end(),
                        entity_type=entry.entity_type,
                        context=text,
                        method="gazetteer",
                    )
                )

        for pattern in self.time_patterns:
            # 所有的时间，包括时刻和日期
            for match in pattern.finditer(text):
                candidates.append(
                    Mention(
                        text_id=sentence.text_id,
                        sentence_id=sentence.sentence_id,
                        mention=match.group(),
                        start=match.start(),
                        end=match.end(),
                        entity_type="Time",
                        context=text,
                        method="regex",
                    )
                )

        for pattern in self.organization_patterns:
            # 目前认为 org 只有 university
            for match in pattern.finditer(text):
                candidates.append(
                    Mention(
                        text_id=sentence.text_id,
                        sentence_id=sentence.sentence_id,
                        mention=match.group(),
                        start=match.start(),
                        end=match.end(),
                        entity_type="Organization",
                        context=text,
                        method="regex",
                    )
                )

        for pattern in self.work_patterns:
            # 《》包裹的名词
            for match in pattern.finditer(text):
                candidates.append(
                    Mention(
                        text_id=sentence.text_id,
                        sentence_id=sentence.sentence_id,
                        mention=match.group(),
                        start=match.start(),
                        end=match.end(),
                        entity_type="Work",
                        context=text,
                        method="regex",
                    )
                )

        return self._resolve_overlaps(candidates)

    def _resolve_overlaps(self, mentions: List[Mention]) -> List[Mention]:
        unique_mentions = {}
        for mention in mentions:
            key = (
                mention.text_id,
                mention.sentence_id,
                mention.start,
                mention.end,
                mention.mention,
                mention.entity_type,
            )
            current = unique_mentions.get(key)
            if current is None or current.method == "regex":
                unique_mentions[key] = mention

        sorted_mentions = sorted(
            unique_mentions.values(),
            key=lambda item: (
                -(item.end - item.start),
                item.start,
                0 if item.method == "gazetteer" else 1,
            ),
        )

        kept: List[Mention] = []
        for candidate in sorted_mentions:
            overlap = False
            for chosen in kept:
                if chosen.text_id != candidate.text_id or chosen.sentence_id != candidate.sentence_id:
                    continue
                if not (candidate.end <= chosen.start or candidate.start >= chosen.end):
                    overlap = True
                    break
            if not overlap:
                kept.append(candidate)

        return sorted(kept, key=lambda item: (item.text_id, item.sentence_id, item.start))
