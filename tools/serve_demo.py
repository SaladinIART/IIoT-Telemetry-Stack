"""Serve frontend/build-demo the way GitHub Pages serves a project site.

Mirrors the hosted layout (sub-path prefix, 404.html SPA fallback) so
base-path and deep-link problems show up locally.

    cd frontend && BASE_PATH=/IIoT-Telemetry-Stack npm run build:demo
    python tools/serve_demo.py            # http://127.0.0.1:4173/IIoT-Telemetry-Stack/

On Git Bash for Windows, prefix commands that pass /paths with MSYS_NO_PATHCONV=1.
"""

from __future__ import annotations

import argparse
import http.server
import io
import os
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "frontend" / "build-demo"


def make_handler(root: Path, prefix: str):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            path = path.split("?", 1)[0].split("#", 1)[0]
            if path != prefix and not path.startswith(prefix + "/"):
                return str(root / "__outside_prefix__")
            return str(root / path[len(prefix) :].lstrip("/"))

        def send_head(self):
            target = self.translate_path(self.path)
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                body = (root / "404.html").read_bytes()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return io.BytesIO(body)
            return super().send_head()

        def log_message(self, *args) -> None:  # keep the console quiet
            pass

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--prefix", default="/IIoT-Telemetry-Stack")
    ap.add_argument("--port", type=int, default=4173)
    args = ap.parse_args()
    prefix = "/" + args.prefix.strip("/")
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", args.port), make_handler(args.root, prefix)
    )
    print(f"serving {args.root} at http://127.0.0.1:{args.port}{prefix}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
