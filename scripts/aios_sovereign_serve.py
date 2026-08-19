#!/usr/bin/env python3
"""AIOS Sovereign Agent Web Server (aios.sovereign_serve.v1).

Hosts the ultra-minimalist single-prompt sovereign interface for end-users,
connecting directly to the unconstrained multi-model agent swarm.

Usage:
  python3 scripts/aios_sovereign_serve.py [--port 8888] [--host 127.0.0.1]
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
SOVEREIGN_APP_DIR = ROOT / "apps" / "sovereign"

try:
    from aios_stream_weaver import StreamWeaver
    from aios_hetero_council import HeteroCouncil
    from aios_evolutionary_graph import DynamicGraphEngine, create_default_genome
    from aios_cross_session_bus import CrossSessionBus
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from aios_stream_weaver import StreamWeaver
    from aios_hetero_council import HeteroCouncil
    from aios_evolutionary_graph import DynamicGraphEngine, create_default_genome
    from aios_cross_session_bus import CrossSessionBus


class SovereignHTTPHandler(BaseHTTPRequestHandler):
    weaver = StreamWeaver(timeout=35.0)
    bus = CrossSessionBus()

    def do_GET(self):
        url_path = self.path.split("?")[0]
        if url_path in ("/", "/index.html"):
            self._serve_file(SOVEREIGN_APP_DIR / "index.html", "text/html")
        elif url_path == "/styles.css":
            self._serve_file(SOVEREIGN_APP_DIR / "styles.css", "text/css")
        elif url_path == "/app.js":
            self._serve_file(SOVEREIGN_APP_DIR / "app.js", "application/javascript")
        elif url_path == "/api/status":
            self._send_json(200, {
                "status": "online",
                "system": "AIOS Sovereign v1.0",
                "registered_agents": len(self.bus.registry),
                "unconstrained": True,
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/sovereign/execute":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                goal = data.get("goal", "").strip()
                if not goal:
                    self._send_json(400, {"ok": False, "error": "Goal cannot be empty"})
                    return

                print(f"\n⚡ [Sovereign Server] Received User Goal: '{goal}'")
                t0 = time.time()
                res = self.weaver.weave_ideation_to_code(goal)

                # Log receipt to society bus
                self.bus.send_message(
                    sender_id="sovereign-core",
                    recipient_id="broadcast",
                    content=f"Executed goal: '{goal}'",
                    kind="receipt",
                )

                self._send_json(200, {
                    "ok": True,
                    "goal": goal,
                    "total_latency_s": res.get("total_latency_s", round(time.time() - t0, 2)),
                    "injected_invariants": res.get("injected_invariants", []),
                    "injected_falsifiers": res.get("injected_falsifiers", []),
                    "generated_code": res.get("generated_code", ""),
                    "critic_verdict": res.get("critic_verdict", ""),
                    "pipeline_trail": res.get("pipeline_trail", []),
                })
            except Exception as exc:
                self._send_json(500, {"ok": False, "error": str(exc)})
        else:
            self.send_error(404, "Endpoint Not Found")

    def _serve_file(self, path: Path, mime_type: str):
        if not path.exists():
            self.send_error(404, "File Not Found")
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, data: Dict[str, Any]):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Concise logging
        sys.stderr.write(f"[Sovereign HTTP] {self.address_string()} - {format % args}\n")


def run_server(host: str = "127.0.0.1", port: int = 8888):
    server = ThreadingHTTPServer((host, port), SovereignHTTPHandler)
    print("=" * 75)
    print(f"🌟 AIOS SOVEREIGN AGENT SERVER RUNNING")
    print(f"🔗 Local Web UI: http://{host}:{port}")
    print(f"⚡ Substrate: Unconstrained Open Source Multi-Model Swarm")
    print("=" * 75)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8888, help="Port to listen on (default 8888)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default 127.0.0.1)")
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
