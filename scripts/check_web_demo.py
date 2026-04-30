import argparse
import json
import shutil
import subprocess
import sys
import threading
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CheckFailed(Exception):
    pass


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


class ReusableTCPServer(TCPServer):
    allow_reuse_address = True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查网页演示需要的页面和数据是否齐全")
    parser.add_argument("--port", type=int, default=8765, help="临时检查端口，默认 8765")
    return parser


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def fetch_text(base_url: str, path: str) -> str:
    url = f"{base_url}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.read().decode("utf-8")
    except Exception as error:
        raise CheckFailed(f"无法访问 {url}: {error}") from error


def fetch_json(base_url: str, path: str) -> dict:
    try:
        return json.loads(fetch_text(base_url, path))
    except json.JSONDecodeError as error:
        raise CheckFailed(f"{path} 不是合法 JSON: {error}") from error


def validate_index(html: str) -> None:
    tab_names = ["实体抽取", "实体消歧", "事件抽取", "关系抽取", "知识图谱"]
    missing = [name for name in tab_names if name not in html]
    require(not missing, f"网页首页缺少页签文字: {', '.join(missing)}")
    require("节点 / 边" not in html, "网页仍保留旧的节点/边选择提示")
    require("先点击一个节点或一条关系" not in html, "网页仍提示可以点击关系")


def validate_graph(graph: dict) -> tuple[int, int]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    summary = graph.get("summary", {})
    require(nodes, "graph.json 里 nodes 为空")
    require(edges, "graph.json 里 edges 为空")
    require(summary.get("relation_count", 0) > 0, "graph.json 里 relation_count 不正确")
    require(summary.get("event_count", 0) > 0, "graph.json 里 event_count 不正确")
    node_ids = {node.get("id") for node in nodes}
    require("E016" in node_ids, "graph.json 缺少 Bombe 节点")
    require("E025" in node_ids, "graph.json 缺少 Manchester Mark I 节点")
    for node_id, label in [("E016", "Bombe"), ("E025", "Manchester Mark I")]:
        linked = any(edge.get("source") == node_id or edge.get("target") == node_id for edge in edges)
        require(linked, f"{label} 仍然是孤立节点")
    return len(nodes), len(edges)


def validate_report(report: dict) -> tuple[int, int, int, int]:
    required_fields = ["raw_text_count", "mention_count", "relation_count", "event_count"]
    for field in required_fields:
        require(report.get(field, 0) > 0, f"report.json 里 {field} 不正确")
    return (
        report["raw_text_count"],
        report["mention_count"],
        report["relation_count"],
        report["event_count"],
    )


def validate_explainability(explainability: dict) -> dict:
    case_keys = {
        "entity_extraction_cases": "实体抽取",
        "disambiguation_cases": "实体消歧",
        "event_extraction_cases": "事件抽取",
        "relation_extraction_cases": "关系抽取",
    }
    counts = {}
    for key, label in case_keys.items():
        cases = explainability.get(key, [])
        require(cases, f"explainability.json 缺少{label}案例: {key}")
        counts[label] = len(cases)
    for case in explainability.get("relation_extraction_cases", []):
        require(case.get("head_id"), "关系抽取案例缺少 head_id")
        require(case.get("tail_id"), "关系抽取案例缺少 tail_id，前端无法确认尾实体")
    return counts


def validate_app_behavior(app_js: str) -> None:
    old_edge_selectors = [
        "selectedEdgeId",
        "function selectEdge",
        "function findEdgeAt",
        "function updateDetailForEdge",
        "pointToSegmentDistance",
        "已选关系",
    ]
    for keyword in old_edge_selectors:
        require(keyword not in app_js, f"app.js 仍包含边选中逻辑: {keyword}")
    require("clearSelection()" in app_js, "app.js 缺少空白点击取消选择逻辑")
    removed_button_text = "在图里" + "看"
    require(removed_button_text not in app_js, "app.js 仍包含案例跳转按钮文案")
    require("case-button" not in app_js, "app.js 仍包含案例跳转按钮")


def check_app_js_syntax() -> str:
    node_path = shutil.which("node")
    if node_path is None:
        return "[WARN] 未找到 node，跳过 app.js 语法检查"

    result = subprocess.run(
        [node_path, "--check", str(PROJECT_ROOT / "web" / "app.js")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    require(result.returncode == 0, f"app.js 语法检查失败:\n{result.stderr}")
    return "[OK] app.js 语法检查通过"


def start_server(port: int) -> ReusableTCPServer:
    handler = partial(QuietHandler, directory=str(PROJECT_ROOT))
    try:
        httpd = ReusableTCPServer(("127.0.0.1", port), handler)
    except OSError as error:
        raise CheckFailed(f"端口 {port} 启动失败，可以换一个端口重试: {error}") from error

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def run_checks(port: int) -> None:
    base_url = f"http://127.0.0.1:{port}"
    httpd = start_server(port)
    try:
        html = fetch_text(base_url, "web/index.html")
        validate_index(html)
        print("[OK] 网页首页可以访问，五个页签都存在")

        app_js = fetch_text(base_url, "web/app.js")
        validate_app_behavior(app_js)
        print("[OK] app.js 可以通过网页服务访问")
        print("[OK] 图谱页只保留节点选择，空白点击会取消选择")
        print(check_app_js_syntax())

        graph = fetch_json(base_url, "data/output/graph.json")
        node_count, edge_count = validate_graph(graph)
        print(f"[OK] 图谱数据包含 {node_count} 个节点、{edge_count} 条边")

        report = fetch_json(base_url, "data/output/report.json")
        raw_count, mention_count, relation_count, event_count = validate_report(report)
        print(
            f"[OK] 报告数据包含 {raw_count} 份 raw 文本、{mention_count} 个 mention、"
            f"{relation_count} 条关系、{event_count} 个事件"
        )

        explainability = fetch_json(base_url, "data/output/explainability.json")
        case_counts = validate_explainability(explainability)
        case_text = "，".join(f"{label} {count} 个" for label, count in case_counts.items())
        print(f"[OK] 四类过程案例齐全：{case_text}")

        print(f"\n网页演示材料检查通过: {base_url}/web/index.html")
    finally:
        httpd.shutdown()
        httpd.server_close()


def main() -> None:
    args = build_parser().parse_args()
    try:
        run_checks(args.port)
    except CheckFailed as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
