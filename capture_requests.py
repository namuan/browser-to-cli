#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "playwright",
# ]
# ///
"""
Capture network requests from a URL and save them to a JSON file.

Usage:
./capture_requests.py <url>
./capture_requests.py -v <url>   # Log INFO messages
./capture_requests.py -vv <url>  # Log DEBUG messages
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import json
import logging
import threading
from datetime import datetime

from playwright.sync_api import sync_playwright

from cli_utils import make_parser, safe_filename, setup_logging


TEXT_TYPES = frozenset({"text", "json", "javascript", "css", "xml"})


def save_logs(url, requests_log):
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = safe_filename(url)
    output_file = logs_dir / f"{safe_name}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump({"url": url, "captured_at": timestamp, "requests": requests_log}, f, indent=2)

    print(f"Captured {len(requests_log)} requests -> {output_file}")


def capture_requests(url):
    requests_log = []
    requests_by_url = {}
    lock = threading.Lock()
    xhr_fetch_count = 0

    def handle_request(request):
        nonlocal xhr_fetch_count
        entry = {
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "headers": dict(request.headers),
            "post_data": request.post_data,
            "timestamp": datetime.now().isoformat(),
        }
        logging.debug(f"Request: {request.method} {request.url}")
        with lock:
            requests_log.append(entry)
            requests_by_url.setdefault(request.url, []).append(entry)
            if request.resource_type in ("xhr", "fetch"):
                xhr_fetch_count += 1

    def handle_response(response):
        with lock:
            candidates = requests_by_url.get(response.url, [])
            for entry in reversed(candidates):
                if "status" not in entry:
                    entry["status"] = response.status
                    entry["response_headers"] = dict(response.headers)
                    content_type = response.headers.get("content-type", "")
                    if any(t in content_type for t in TEXT_TYPES):
                        try:
                            entry["response_body"] = response.text()
                        except Exception:
                            logging.warning("Failed to read response text", exc_info=True)
                            entry["response_body"] = None
                    else:
                        content_length = response.headers.get("content-length")
                        if content_length:
                            entry["response_body"] = f"<binary {content_length} bytes>"
                        else:
                            entry["response_body"] = "<binary unknown size>"
                    logging.debug(f"Response: {response.status} {response.url}")
                    break

    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.on("request", handle_request)
        page.on("response", handle_response)

        logging.info(f"Navigating to {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        stop_signal = threading.Event()

        def wait_for_enter():
            input()
            stop_signal.set()

        input_thread = threading.Thread(target=wait_for_enter, daemon=True)
        input_thread.start()

        print("\nBrowser opened. Interact with the page.")
        print("Press Enter in this terminal when done to save and exit...")
        prev_total = 0
        while not stop_signal.is_set():
            page.wait_for_timeout(500)
            with lock:
                total = len(requests_log)
                api = xhr_fetch_count
            if total != prev_total:
                print(f"\rRequests captured: {total} (XHR/Fetch: {api})  ", end="", flush=True)
                prev_total = total

        print()

        with lock:
            save_logs(url, requests_log)

        try:
            browser.close()
        except Exception:
            logging.warning("Failed to close browser", exc_info=True)
    finally:
        playwright.stop()


def main(args):
    capture_requests(args.url)


if __name__ == "__main__":
    parser = make_parser("url", "URL to capture network requests from", __doc__)
    args = parser.parse_args()
    setup_logging(args.verbose)
    main(args)
