from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
# 某个原始文本被切分出来的一条句子，是预处理阶段的输出，也是抽取阶段的输入
class SentenceRecord:
    text_id: str     # 原始文件名，例如 text_01_biography
    sentence_id: int # 该文本内部的句子序号，从 1 开始
    text: str        # 句子正文

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
# 从某个句子里抽到的一个实体 Mention，是抽取阶段的输出，也是消歧阶段的输入
class Mention:
    text_id: str
    sentence_id: int
    mention: str     # 原文片段
    start: int       # [start, end)
    end: int
    entity_type: str # 抽取阶段给它的类型
    context: str     # 整句文本，后续消歧要用
    method: str      # 记录它是怎么抽出来的，比如 regex: 正则; gazetteer: 已知实体清单

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
# 知识库中的标准实体
class Entity:
    entity_id: str
    canonical_name: str # 标准名称
    entity_type: str
    aliases: List[str]  # 用来做候选召回和别名匹配
    keywords: List[str] # 用来做上下文打分
    description: str    # 主要是为了导出和可读性

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
# 表示关系的数据结构
class Triple:
    head: str
    relation: str
    tail: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
# Mention 消歧之后的结果
class LinkedMention:
    text_id: str
    sentence_id: int
    mention: str
    start: int
    end: int
    entity_type: str
    context: str
    method: str
    entity_id: str
    canonical_name: str
    resolved_entity_type: str
    score: float
    status: str # linked or NIL
    alias_score: float = 0.0
    context_keyword_score: float = 0.0
    type_prior_score: float = 0.0
    candidate_ids: List[str] = field(default_factory=list) # 可能是这个 Memtion 对应的实体构成的列表
    candidate_details: List[Dict[str, str | float]] = field(default_factory=list) # 保存每个候选实体的打分明细

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RelationRecord:
    relation_id: str
    text_id: str
    sentence_id: int
    head_id: str
    head_name: str
    head_type: str
    relation: str
    tail_id: str
    tail_name: str
    tail_type: str
    evidence: str
    method: str
    trigger: str = ""
    source_event_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EventRecord:
    event_id: str
    text_id: str
    sentence_id: int
    event_type: str
    trigger: str
    evidence: str
    participants: List[Dict[str, str]]
    time: str = ""
    place: str = ""
    description: str = ""
    source_relation_ids: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, str]] = None

    def to_dict(self) -> dict:
        return asdict(self)
