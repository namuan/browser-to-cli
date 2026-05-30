#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
Generate an OpenAPI 3.0 spec from a captured network requests log file.

Usage:
./generate_spec.py <path/to/log.json>
./generate_spec.py -v <path/to/log.json>   # Log INFO messages
./generate_spec.py -vv <path/to/log.json>  # Log DEBUG messages
"""
import json
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse


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
        "log_file",
        help="Path to the captured requests log file (JSON)",
    )
    return parser.parse_args()


def is_api_request(entry):
    resource_type = entry.get("resource_type", "")
    if resource_type in ("xhr", "fetch"):
        return True

    response_headers = entry.get("response_headers", {})
    content_type = response_headers.get("content-type", "")
    if "json" in content_type.lower():
        return True

    url = entry.get("url", "")
    parsed = urlparse(url)
    if "/api/" in parsed.path.lower():
        return True

    post_data = entry.get("post_data")
    if post_data:
        return True

    return False


def normalize_path_group(requests_group):
    if len(requests_group) <= 1:
        return urlparse(requests_group[0]["url"]).path

    paths = sorted({urlparse(r["url"]).path for r in requests_group})
    segments_list = [p.strip("/").split("/") for p in paths]

    normalized = []
    for i in range(len(segments_list[0])):
        values = {s[i] if i < len(s) else "" for s in segments_list}
        if len(values) > 1 or values == {""}:
            normalized.append(f"{{param{i}}}")
        else:
            normalized.append(list(values)[0])

    return "/" + "/".join(normalized)


def extract_query_params(requests_group):
    params = {}
    for r in requests_group:
        parsed = urlparse(r["url"])
        qs = parse_qs(parsed.query)
        for key, values in qs.items():
            if key not in params:
                params[key] = values[0] if len(values) == 1 else values
    return params


def infer_response_schema(requests_group):
    schema = {"type": "object"}
    for r in requests_group:
        body = r.get("response_body")
        if not body:
            continue
        if isinstance(body, str) and body.startswith("{"):
            try:
                data = json.loads(body)
                schema = infer_schema_from_value(data)
                return schema
            except Exception:
                pass
    return schema


def infer_schema_from_value(value):
    if value is None:
        return {"type": "string", "nullable": True}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        if not value:
            return {"type": "array", "items": {"type": "string"}}
        item_schema = infer_schema_from_value(value[0])
        return {"type": "array", "items": item_schema}
    if isinstance(value, dict):
        properties = {}
        for k, v in value.items():
            properties[k] = infer_schema_from_value(v)
        return {"type": "object", "properties": properties}
    return {"type": "string"}


def infer_request_schema(requests_group):
    for r in requests_group:
        post_data = r.get("post_data")
        if post_data:
            return {"type": "string", "description": post_data[:200]}
    return None


def build_openapi_spec(url, api_requests):
    requests_by_key = {}
    for r in api_requests:
        method = r["method"].lower()
        parsed = urlparse(r["url"])
        base = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path
        key = f"{method}:{base}:{path}"
        if key not in requests_by_key:
            requests_by_key[key] = []
        requests_by_key[key].append(r)

    by_base = {}
    for key, group in requests_by_key.items():
        method, base, path = key.split(":", 2)
        if base not in by_base:
            by_base[base] = {}
        by_base[base][(method, path)] = group

    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": f"API Spec for {urlparse(url).netloc or 'unknown'}",
            "version": datetime.now().strftime("%Y-%m-%d"),
            "description": f"Auto-generated from captured network traffic at {url}",
        },
        "servers": [],
        "paths": {},
    }

    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}" if url and urlparse(url).scheme else ""
    if base_url:
        spec["servers"].append({"url": base_url})

    seen_servers = set()
    for base, path_groups in by_base.items():
        if base not in seen_servers:
            spec["servers"].append({"url": base})
            seen_servers.add(base)

        spec_paths = spec["paths"]

        combined_by_norm = {}
        for (method, path), group in path_groups.items():
            norm_path = normalize_path_group(group)
            combined_key = (method, norm_path)
            if combined_key not in combined_by_norm:
                combined_by_norm[combined_key] = group
            else:
                combined_by_norm[combined_key].extend(group)

        for (method, norm_path), group in combined_by_norm.items():
            if norm_path not in spec_paths:
                spec_paths[norm_path] = {}

            sorted_group = sorted(group, key=lambda r: r.get("status", 0), reverse=True)
            best = sorted_group[0] if sorted_group else group[0]

            path_item = {
                "operationId": f"{method}_{norm_path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}",
                "responses": {},
            }

            status = best.get("status")
            if status:
                path_item["responses"][str(status)] = {
                    "description": f"Response with status {status}",
                }
                response_schema = infer_response_schema(group)
                if response_schema.get("type") == "object" and response_schema.get("properties"):
                    path_item["responses"][str(status)]["content"] = {
                        "application/json": {"schema": response_schema}
                    }

            query_params = extract_query_params(group)
            if query_params:
                path_item["parameters"] = []
                for name, example in query_params.items():
                    param = {"name": name, "in": "query", "schema": {"type": "string"}}
                    if example:
                        param["example"] = example
                    path_item["parameters"].append(param)

            request_schema = infer_request_schema(group)
            if request_schema:
                path_item["requestBody"] = {
                    "content": {"application/json": {"schema": request_schema}}
                }

            spec_paths[norm_path][method] = path_item

    return spec


def generate_spec(log_file):
    log_path = Path(log_file)
    with open(log_path) as f:
        data = json.load(f)

    url = data.get("url", "")
    requests = data.get("requests", [])

    api_requests = [r for r in requests if is_api_request(r)]
    logging.info(f"Found {len(api_requests)} API requests out of {len(requests)} total")

    spec = build_openapi_spec(url, api_requests)

    specs_dir = Path("specs")
    specs_dir.mkdir(exist_ok=True)

    parsed = urlparse(url) if url else urlparse("localhost")
    safe_name = parsed.netloc.replace(".", "_")[:50]
    captured_at = data.get("captured_at", datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_file = specs_dir / f"{safe_name}_{captured_at}.json"

    with open(output_file, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"Generated OpenAPI spec with {len(spec['paths'])} paths -> {output_file}")


def main(args):
    generate_spec(args.log_file)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
