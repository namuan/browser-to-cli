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
import json
import logging
import tempfile
import webbrowser
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path


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
        "spec_file",
        help="Path to the OpenAPI spec JSON file",
    )
    return parser.parse_args()


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
    with open(spec_path) as f:
        spec_data = json.load(f)

    spec_json = json.dumps(spec_data, indent=2)
    html = SWAGGER_UI_HTML.replace("SPEC_PLACEHOLDER", spec_json)

    output_dir = Path("views")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{spec_path.stem}.html"

    with open(output_file, "w") as f:
        f.write(html)

    webbrowser.open(f"file://{output_file.resolve()}")
    print(f"Opened spec in browser: {output_file}")


def main(args):
    view_spec(args.spec_file)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
