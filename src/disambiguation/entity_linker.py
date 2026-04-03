from pathlib import Path
from typing import Dict, List

from config import LINKING_SCORE_THRESHOLD
from src.schema.types import Entity, LinkedMention, Mention
from src.utils.io import load_entities
from src.utils.text import keyword_hit_score, normalize_text, token_overlap_ratio


class EntityLinker:
    def __init__(self, entities: List[Entity], threshold: float = LINKING_SCORE_THRESHOLD):
        self.entities = entities
        self.threshold = threshold
        self.entity_map: Dict[str, Entity] = {entity.entity_id: entity for entity in entities}
        self.alias_index = self._build_alias_index(entities)

    @classmethod
    def from_kb_file(cls, kb_path: Path) -> "EntityLinker":
        return cls(load_entities(kb_path))

    def _build_alias_index(self, entities: List[Entity]) -> Dict[str, set]:
        alias_index: Dict[str, set] = {}
        # 之所以 value 是 set，是因为这一步要扩大候选范围，有几种可能性会让一个 alias 对应多个可能的 entity_id，比如：
        # 1) apply 既是苹果公司也是水果
        # 2) 归一化后 A.I. -> ai
        # 3) 歧义，比如 ML 可能是 Machine Learning 也可能是人名
        for entity in entities:
            for alias in [entity.canonical_name, *entity.aliases]:
                normalized = normalize_text(alias)
                if not normalized:
                    continue
                alias_index.setdefault(normalized, set()).add(entity.entity_id)
        return alias_index

    def generate_candidates(self, mention: Mention) -> List[Entity]:
        mention_norm = normalize_text(mention.mention)
        candidate_ids = set(self.alias_index.get(mention_norm, set()))

        for alias_norm, entity_ids in self.alias_index.items():
            if not mention_norm:
                continue
            if mention_norm in alias_norm or alias_norm in mention_norm:
                # 如果概念存在包含关系，也加入候选
                candidate_ids.update(entity_ids)

        return [self.entity_map[entity_id] for entity_id in sorted(candidate_ids)]

    def alias_score(self, mention_text: str, entity: Entity) -> float:
        mention_norm = normalize_text(mention_text)
        alias_norms = [normalize_text(alias) for alias in [entity.canonical_name, *entity.aliases]]

        if mention_norm in alias_norms:
            return 1.0

        for alias_norm in alias_norms:
            if mention_norm and (mention_norm in alias_norm or alias_norm in mention_norm):
                return 0.9

        overlap_score = max(
            token_overlap_ratio(mention_text, alias)
            for alias in [entity.canonical_name, *entity.aliases]
        )
        return max(0.0, min(0.6, overlap_score))

    def context_keyword_score(self, context: str, entity: Entity) -> float:
        return keyword_hit_score(context, entity.keywords)

    def type_prior_score(self, mention_type: str, entity_type: str) -> float:
        if not mention_type:
            return 0.5
        if mention_type == entity_type:
            return 1.0

        loosely_related = {
            ("Place", "Organization"),
            ("Organization", "Place"),
            ("Work", "Concept"),
            ("Concept", "Work"),
            ("Work", "Device"),
            ("Device", "Concept"),
            ("Concept", "Device"),
        }
        if (mention_type, entity_type) in loosely_related:
            return 0.2
        return 0.0

    def score_candidate(self, mention: Mention, entity: Entity) -> dict:
        alias_score = self.alias_score(mention.mention, entity)
        context_score = self.context_keyword_score(mention.context, entity)
        type_score = self.type_prior_score(mention.entity_type, entity.entity_type)
        final_score = round(0.5 * alias_score + 0.3 * context_score + 0.2 * type_score, 4)

        return {
            "entity": entity,
            "alias_score": alias_score,
            "context_keyword_score": context_score,
            "type_prior_score": type_score,
            "score": final_score,
        }

    def link_mention(self, mention: Mention) -> LinkedMention:
        candidates = self.generate_candidates(mention)
        if not candidates:
            return LinkedMention(
                **mention.to_dict(),
                entity_id="NIL",
                canonical_name="NIL",
                resolved_entity_type="NIL",
                score=0.0,
                status="NIL",
                candidate_ids=[],
            )

        scored_candidates = [self.score_candidate(mention, entity) for entity in candidates]
        best_candidate = max(
            scored_candidates,
            key=lambda item: (
                item["score"],
                item["context_keyword_score"],
                item["alias_score"],
            ),
        )

        if best_candidate["score"] < self.threshold:
            return LinkedMention(
                **mention.to_dict(),
                entity_id="NIL",
                canonical_name="NIL",
                resolved_entity_type="NIL",
                score=best_candidate["score"],
                status="NIL",
                alias_score=best_candidate["alias_score"],
                context_keyword_score=best_candidate["context_keyword_score"],
                type_prior_score=best_candidate["type_prior_score"],
                candidate_ids=[item["entity"].entity_id for item in scored_candidates],
            )

        chosen_entity = best_candidate["entity"]
        return LinkedMention(
            **mention.to_dict(),
            entity_id=chosen_entity.entity_id,
            canonical_name=chosen_entity.canonical_name,
            resolved_entity_type=chosen_entity.entity_type,
            score=best_candidate["score"],
            status="linked",
            alias_score=best_candidate["alias_score"],
            context_keyword_score=best_candidate["context_keyword_score"],
            type_prior_score=best_candidate["type_prior_score"],
            candidate_ids=[item["entity"].entity_id for item in scored_candidates],
        )

    def link_mentions(self, mentions: List[Mention]) -> List[LinkedMention]:
        return [self.link_mention(mention) for mention in mentions]
