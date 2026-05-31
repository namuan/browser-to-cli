#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "websockets",
# ]
# ///
"""
Capture network requests from a browser via the companion extension.
Requests are saved per host — each site you visit gets its own log file.

Usage:
./capture_ws.py
./capture_ws.py -v    # Log INFO messages
./capture_ws.py -vv   # Log DEBUG messages
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
import logging
import threading
from datetime import datetime
from urllib.parse import urlparse

import websockets

from cli_utils import safe_filename, setup_logging

WS_HOST = "localhost"
WS_PORT = 9223

TEXT_TYPES = frozenset({"text", "json", "javascript", "css", "xml"})


def get_host(request_data):
    page_url = request_data.get("page_url", "")
    if page_url:
        try:
            return urlparse(page_url).hostname or "unknown"
        except Exception:
            pass
    try:
        return urlparse(request_data.get("url", "")).hostname or "unknown"
    except Exception:
        return "unknown"


def _site_url(entries, host):
    for e in entries:
        if e.get("page_url"):
            return e["page_url"]
    for e in entries:
        if e.get("url"):
            return e["url"]
    return f"https://{host}"


def save_logs(requests_by_host):
    if not requests_by_host:
        print("No requests captured.")
        return

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = 0

    for host, entries in sorted(requests_by_host.items()):
        if not entries:
            continue
        safe_name = safe_filename(f"https://{host}")
        output_file = logs_dir / f"{safe_name}_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(
                {"url": _site_url(entries, host), "captured_at": timestamp, "requests": entries},
                f,
                indent=2,
            )

        print(f"  {host}: {len(entries)} requests -> {output_file.name}")
        total += len(entries)

    print(f"\nCaptured {total} requests across {len(requests_by_host)} site(s)")


def build_entry(request_data):
    entry = {
        "method": request_data.get("method"),
        "url": request_data.get("url"),
        "page_url": request_data.get("page_url"),
        "resource_type": request_data.get("resource_type", "xhr"),
        "headers": request_data.get("headers", {}),
        "post_data": request_data.get("body"),
        "timestamp": request_data.get("timestamp", datetime.now().isoformat()),
    }
    response = request_data.get("response")
    if response:
        entry["status"] = response.get("status")
        entry["response_headers"] = response.get("headers", {})
        body = response.get("body")
        content_type = (response.get("headers") or {}).get("content-type", "")
        if any(t in content_type for t in TEXT_TYPES) or body is not None:
            entry["response_body"] = body
        else:
            entry["response_body"] = "<binary unknown size>"
    return entry


async def handler(websocket, requests_by_host, lock):
    async for message in websocket:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "request":
            entry = build_entry(data)
            host = get_host(data)
            with lock:
                requests_by_host.setdefault(host, []).append(entry)
            logging.debug(f"Captured [{host}]: {entry['method']} {entry['url']}")
        elif data.get("type") == "ping":
            await websocket.send(json.dumps({"type": "pong"}))


async def run_server(requests_by_host, lock, stop_event):
    async with websockets.serve(
        lambda ws: handler(ws, requests_by_host, lock),
        WS_HOST,
        WS_PORT,
    ):
        print(f"Listening on ws://{WS_HOST}:{WS_PORT}")
        print("Load the extension in your browser and navigate to the target page.")
        print("Press Enter in this terminal when done to save and exit...\n")

        prev_total = 0
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
            with lock:
                total = sum(len(v) for v in requests_by_host.values())
            if total != prev_total:
                print(f"\rRequests captured: {total}  ", end="", flush=True)
                prev_total = total

        print()
        with lock:
            save_logs(dict(requests_by_host))


def capture_ws():
    requests_by_host = {}
    lock = threading.Lock()
    stop_event = threading.Event()

    def wait_for_enter():
        input()
        stop_event.set()

    threading.Thread(target=wait_for_enter, daemon=True).start()

    try:
        asyncio.run(run_server(requests_by_host, lock, stop_event))
    except KeyboardInterrupt:
        print()
        with lock:
            save_logs(dict(requests_by_host))


def main():
    try:
        capture_ws()
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"Port {WS_PORT} is already in use. Is capture_ws already running?")
        else:
            raise


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    args = parser.parse_args()
    setup_logging(args.verbose)
    main()
