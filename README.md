# Browser to CLI - Network Request Capture & API Spec Generator

A set of command-line tools to capture network requests from a website, generate OpenAPI specs from the captured traffic, and view the specs in a browser.

## Workflow

```
capture_requests.py  →  generate_spec.py  →  view_spec.py
     (capture)            (generate)           (view)
     logs/*.json          specs/*.json        views/*.html
```

## Scripts

### 1. Capture Network Requests

Opens a visible Chromium browser so you can interact with the page. All network requests (including XHR/fetch) are captured in real time. Press Enter when done to save.

```bash
./capture_requests.py https://example.com
```

A live counter shows captured requests while you browse:
```
Browser opened. Interact with the page.
Press Enter in this terminal when done to save and exit...
Requests captured: 47 (XHR/Fetch: 12)
```

### 2. Generate OpenAPI Spec

Takes a captured log file and generates an OpenAPI 3.0 spec from the API calls found in it.

```bash
./generate_spec.py logs/example.com_20260530_120000.json
```

Output: `specs/<domain>_<timestamp>.json`

### 3. View Spec in Browser

Opens the generated OpenAPI spec in Swagger UI.

```bash
./view_spec.py specs/example_com_20260530_120000.json
```

Output: `views/<spec_name>.html` (opens automatically in your browser)

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- Playwright Chromium browser

## Installation

```bash
git clone https://github.com/namuan/browser-to-cli.git
cd browser-to-cli
uv run --script capture_requests.py --help
uv run python -m playwright install chromium
```

## Full Example

```bash
# 1. Capture traffic from a site (interact with the page, then press Enter)
./capture_requests.py https://some-site.com
# Captured 83 requests -> logs/some-site.com_20260530_120000.json

# 2. Generate OpenAPI spec from the captured log
./generate_spec.py logs/some-site.com_20260530_120000.json
# Generated OpenAPI spec with 8 paths -> specs/some-site_com_20260530_120000.json

# 3. View the spec in your browser
./view_spec.py specs/some-site_com_20260530_120000.json
# Opened spec in browser: views/some-site_com_20260530_120000.html
```

## Verbose Logging

All scripts support `-v` / `-vv` flags:

```bash
./capture_requests.py -v https://example.com    # INFO
./capture_requests.py -vv https://example.com   # DEBUG
./generate_spec.py -vv logs/example.json
./view_spec.py -v specs/example.json
```

## Tips

- **No XHR/Fetch requests captured?** Interact more with the page — click tabs, scroll, navigate — to trigger API calls. The live counter helps you see when they come in.
- **Empty spec (0 paths)?** The captured session may not have triggered any API calls. Try a more interactive session.

## License

[MIT](LICENSE)
