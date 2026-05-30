# Browser to CLI - Network Request Capture

A command-line tool that captures all network requests from a website using Playwright and Chromium. Perfect for analyzing web traffic, debugging API calls, or understanding resource loading patterns.

## Features

- Captures all network requests (HTML, CSS, JS, images, fonts, XHR/fetch)
- Records request/response headers, status codes, and response bodies
- Handles JavaScript-rendered content
- Saves output as structured JSON
- Verbose logging modes for debugging

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/namuan/browser-to-cli.git
cd browser-to-cli
```

2. Install Playwright browsers:
```bash
uv run --script capture_requests.py --help
uv run python -m playwright install chromium
```

## Usage

Basic usage:
```bash
./capture_requests.py https://example.com
```

With verbose logging:
```bash
./capture_requests.py -v https://example.com   # INFO level
./capture_requests.py -vv https://example.com  # DEBUG level
```

### Command Line Options

```
positional arguments:
  url            URL to capture network requests from

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity of logging output
```

## Output

Requests are saved to `logs/<domain>_<timestamp>.json` with the following structure:

```json
{
  "url": "https://example.com",
  "captured_at": "20260530_081851",
  "requests": [
    {
      "method": "GET",
      "url": "https://example.com/",
      "resource_type": "document",
      "headers": {...},
      "post_data": null,
      "timestamp": "2026-05-30T08:18:51.123456",
      "status": 200,
      "response_headers": {...},
      "response_body": "<!DOCTYPE html>..."
    }
  ]
}
```

### Captured Data

For each request:
- **method**: HTTP method (GET, POST, etc.)
- **url**: Full request URL
- **resource_type**: Type of resource (document, stylesheet, script, image, font, xhr, fetch, etc.)
- **headers**: Request headers
- **post_data**: POST body (if applicable)
- **status**: HTTP response status code
- **response_headers**: Response headers
- **response_body**: Response body (text for text-based content, size indicator for binary)

## Example

```bash
$ ./capture_requests.py https://news.ycombinator.com
Captured 47 requests -> logs/news.ycombinator.com_20260530_120000.json
```

## Troubleshooting

### Browser crashes with SEGV or permission errors

On macOS, you may need to grant Full Disk Access to your terminal:
1. System Preferences → Privacy & Security → Full Disk Access
2. Add your terminal app (Terminal, iTerm2, etc.)

### Playwright browser not found

Install the browser:
```bash
uv run python -m playwright install chromium
```

### Network errors

Ensure you have internet connectivity and the URL is accessible.

## License

MIT

## Contributing

Issues and pull requests welcome!
