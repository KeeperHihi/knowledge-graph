import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DATA_DIR
from src.evaluation.manual_eval import run_manual_evaluation


if __name__ == "__main__":
    result = run_manual_evaluation(eval_dir=DATA_DIR / "eval")
    print(json.dumps(result, ensure_ascii=False, indent=2))
