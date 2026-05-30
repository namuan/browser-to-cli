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
import json
import logging
import os
import threading
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "url",
        help="URL to capture network requests from",
    )
    return parser.parse_args()


def save_logs(url, requests_log):
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = url.split("//")[-1].replace("/", "_")[:50]
    output_file = logs_dir / f"{safe_name}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump({"url": url, "captured_at": timestamp, "requests": requests_log}, f, indent=2)

    print(f"Captured {len(requests_log)} requests -> {output_file}")


def capture_requests(url):
    requests_log = []

    def handle_request(request):
        entry = {
            "method": request.method,
            "url": request.url,
            "resource_type": request.resource_type,
            "headers": dict(request.headers),
            "post_data": request.post_data,
            "timestamp": datetime.now().isoformat(),
        }
        logging.debug(f"Request: {request.method} {request.url}")
        requests_log.append(entry)

    def handle_response(response):
        for entry in reversed(requests_log):
            if entry["url"] == response.url and "status" not in entry:
                entry["status"] = response.status
                entry["response_headers"] = dict(response.headers)
                content_type = response.headers.get("content-type", "")
                if any(t in content_type for t in ("text", "json", "javascript", "css", "xml")):
                    try:
                        entry["response_body"] = response.text()
                    except Exception:
                        entry["response_body"] = None
                else:
                    try:
                        entry["response_body"] = f"<binary {len(response.body())} bytes>"
                    except Exception:
                        entry["response_body"] = None
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
        while not stop_signal.is_set():
            page.wait_for_timeout(500)
            total = len(requests_log)
            api = sum(1 for r in requests_log if r.get("resource_type") in ("xhr", "fetch"))
            print(f"\rRequests captured: {total} (XHR/Fetch: {api})  ", end="", flush=True)

        print()

        save_logs(url, requests_log)

        try:
            browser.close()
        except Exception:
            pass
    finally:
        timer = threading.Timer(3, lambda: os._exit(0))
        timer.start()
        playwright.stop()
        timer.cancel()


def main(args):
    capture_requests(args.url)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
