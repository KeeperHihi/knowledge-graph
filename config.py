from pathlib import Path

# 项目基础路径配置
PROJECT_NAME = "turing-kg"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
KB_DIR = DATA_DIR / "kb"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"

DEFAULT_ENCODING = "utf-8"

# 当前阶段只做轻量方案，因此阈值保持简单、易解释
LINKING_SCORE_THRESHOLD = 0.58

# 抽取阶段至少支持的类型
SUPPORTED_ENTITY_TYPES = [
    "Person",
    "Organization",
    "Place",
    "Event",
    "Work",
    "Time",
    "Concept",
    "Device",
]

# 用于规则抽取的基础正则
TIME_PATTERNS = [
    r"\b(?:18|19|20)\d{2}\b",
    r"(?:18|19|20)\d{2}年",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+(?:18|19|20)\d{2}\b",
]

ORGANIZATION_PATTERNS = [
    r"\bUniversity of [A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*\b",
]

WORK_PATTERNS = [
    r"《[^》]{2,40}》",
]

TRIPLES_HEADER = ["head", "relation", "tail", "evidence"]
