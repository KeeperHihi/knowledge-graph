import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kg.pipeline import run_full_pipeline
from src.evaluation.manual_eval import run_manual_evaluation
from config import DATA_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行课程作业演示流程")
    parser.add_argument("--port", type=int, default=8000, help="网页端口，默认 8000")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="只跑完整流水线并打印演示提示，不启动网页服务",
    )
    return parser


def print_demo_notes(result: dict, evaluation: dict, port: int) -> None:
    print("\n演示摘要")
    print(f"- 原始文本数: {result['raw_text_count']}")
    print(f"- 句子数: {result['sentence_count']}")
    print(f"- 关系数: {result['relation_count']}")
    print(f"- 事件数: {result['event_count']}")
    print(f"- 统计报告: {result['report_path']}")
    print(f"- 来源回溯: {result['traceability_path']}")
    print(f"- 图谱数据: {result['graph_path']}")
    print("- 人工检查结果: data/output/evaluation_summary.json")
    print(
        f"- 人工检查摘要: 消歧 {evaluation['entity_linking']['correct']}/{evaluation['entity_linking']['checked']}，"
        f"关系 {evaluation['relation_extraction']['matched']}/{evaluation['relation_extraction']['checked']}，"
        f"事件 {evaluation['event_extraction']['matched']}/{evaluation['event_extraction']['checked']}"
    )
    print("\n建议答辩顺序")
    print("1. 先展示 data/raw 和 source_manifest，说明数据不是直接手写成图谱。")
    print("2. 再展示 mentions.jsonl 和 linked_entities.jsonl，说明抽取与消歧的中间结果。")
    print("3. 再展示 report.json、traceability.json 和 evaluation_summary.json，说明统计摘要、来源回溯和人工检查结果。")
    print(f"4. 最后打开 http://127.0.0.1:{port}/web/index.html 做网页演示。")
    print("5. 网页按五个页签从左到右讲：")
    print("   - 实体抽取：看 raw 句子里 mention 的高亮。")
    print("   - 实体消歧：看 Princeton/Manchester 候选实体打分。")
    print("   - 事件抽取：看触发词、参与实体和事件记录。")
    print("   - 关系抽取：看事件或规则怎样生成三元组。")
    print("   - 知识图谱：点击节点看连边，拖动节点，切人物视角。")
    print(f"6. 答辩前可运行 python3 scripts/check_web_demo.py --port {port + 1} 做网页材料自检。")
    print("\n配套文档")
    print("- docs/student_method.md")
    print("- docs/demo_walkthrough.md")


def main() -> None:
    args = build_parser().parse_args()
    result = run_full_pipeline()
    evaluation = run_manual_evaluation(eval_dir=DATA_DIR / "eval")
    print_demo_notes(result, evaluation, args.port)

    if args.prepare_only:
        return

    os.chdir(PROJECT_ROOT)
    handler = SimpleHTTPRequestHandler
    with TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"\n演示网页: http://127.0.0.1:{args.port}/web/index.html")
        print("按 Ctrl+C 停止服务。")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止。")


if __name__ == "__main__":
    main()
