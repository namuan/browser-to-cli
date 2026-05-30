#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
View an OpenAPI spec file in the browser using Swagger UI.

Usage:
./view_spec.py <path/to/spec.json>
./view_spec.py -v <path/to/spec.json>   # Log INFO messages
./view_spec.py -vv <path/to/spec.json>  # Log DEBUG messages
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import logging
import webbrowser

from cli_utils import make_parser, setup_logging


SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenAPI Spec Viewer</title>
<link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" >
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({
    spec: SPEC_PLACEHOLDER,
    dom_id: '#swagger-ui',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    layout: "BaseLayout"
})
</script>
</body>
</html>"""


def view_spec(spec_file):
    spec_path = Path(spec_file)
    spec_text = spec_path.read_text()
    html = SWAGGER_UI_HTML.replace("SPEC_PLACEHOLDER", spec_text)

    output_dir = Path("views")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{spec_path.stem}.html"

    output_file.write_text(html)
    webbrowser.open(f"file://{output_file.resolve()}")
    print(f"Opened spec in browser: {output_file}")


def main(args):
    view_spec(args.spec_file)


if __name__ == "__main__":
    parser = make_parser("spec_file", "Path to the OpenAPI spec JSON file", __doc__)
    args = parser.parse_args()
    setup_logging(args.verbose)
    main(args)
