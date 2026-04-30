import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动图谱可视化静态服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址；公网访问用 0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="网页端口，默认 8000")
    return parser


def display_host(host: str) -> str:
    return "<服务器公网 IP>" if host in {"0.0.0.0", "::"} else host


def main() -> None:
    args = build_parser().parse_args()
    os.chdir(PROJECT_ROOT)

    handler = SimpleHTTPRequestHandler
    with TCPServer((args.host, args.port), handler) as httpd:
        url_host = display_host(args.host)
        print(f"监听地址: {args.host}:{args.port}")
        print(f"流程演示页面: http://{url_host}:{args.port}/web/index.html")
        print(f"图谱总图页面: http://{url_host}:{args.port}/web/kg-atlas.html")
        print("按 Ctrl+C 停止服务。")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止。")


if __name__ == "__main__":
    main()
