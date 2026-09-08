"""Serve deterministic synthetic website events for local development."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


EVENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "source" / "api" / "events.json"


class EventsHandler(BaseHTTPRequestHandler):
    def send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - HTTP method name required by stdlib
        request = urlsplit(self.path)
        if request.path != "/events":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found"})
            return

        parameters = parse_qs(request.query, keep_blank_values=True)
        limits = parameters.get("limit", [])
        if len(limits) > 1:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "limit must be supplied once"})
            return
        try:
            limit = int(limits[0]) if limits else None
            if limit is not None and limit < 0:
                raise ValueError
        except ValueError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "limit must be a non-negative integer"})
            return

        try:
            with EVENTS_PATH.open(encoding="utf-8") as handle:
                events = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Event source is unavailable"})
            return

        selected_events = events if limit is None else events[:limit]
        self.send_json(
            HTTPStatus.OK,
            {"events": selected_events, "count": len(selected_events), "total": len(events)},
        )

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local synthetic events API.")
    parser.add_argument("--host", default="127.0.0.1", help="Local bind address (default: 127.0.0.1)")
    parser.add_argument("--port", default=8000, type=int, help="Local port (default: 8000)")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), EventsHandler)
    print(f"Serving synthetic events at http://{args.host}:{args.port}/events")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
