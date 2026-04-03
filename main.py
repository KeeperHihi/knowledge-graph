import argparse
import json

from src.kg.pipeline import run_disambiguation, run_extraction, run_full_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="turing-kg pipeline 入口")
    parser.add_argument(
        "--mode",
        choices=["extraction", "disambiguation", "pipeline"],
        default="pipeline",
        help="选择运行模式",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "extraction":
        result = run_extraction()
    elif args.mode == "disambiguation":
        result = run_disambiguation()
    else:
        result = run_full_pipeline()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
