#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
End-to-end test suite for generate_spec using captured log files as source data.

Usage:
./test_generate_spec.py
./test_generate_spec.py -v   # Show test details
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_spec import (
    build_openapi_spec,
    extract_query_params,
    infer_request_schema,
    infer_response_schema,
    infer_schema_from_value,
    is_api_request,
    normalize_path_group,
)

LOG_DIR = Path(__file__).parent / "logs"
passed = 0
failed = 0


def assert_eq(name, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    expected: {expected}")
        print(f"    actual:   {actual}")


def assert_true(name, value):
    assert_eq(name, value, True)


def assert_false(name, value):
    assert_eq(name, value, False)


def assert_in(name, item, collection):
    global passed, failed
    if item in collection:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    {item!r} not found in {collection!r}")


def assert_gt(name, value, threshold):
    global passed, failed
    if value > threshold:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {name}")
        print(f"    {value} is not greater than {threshold}")


def load_log_file():
    log_files = sorted(LOG_DIR.glob("*.json"))
    if not log_files:
        print("No log files found in logs/")
        sys.exit(1)
    with open(log_files[-1]) as f:
        return json.load(f)


def test_is_api_request():
    print("is_api_request")
    assert_true("xhr is API", is_api_request({"resource_type": "xhr"}))
    assert_true("fetch is API", is_api_request({"resource_type": "fetch"}))
    assert_false("image is not API", is_api_request({"resource_type": "image"}))
    assert_false("stylesheet is not API", is_api_request({"resource_type": "stylesheet"}))
    assert_false("script is not API", is_api_request({"resource_type": "script"}))
    assert_true(
        "json content-type is API",
        is_api_request({"resource_type": "document", "response_headers": {"content-type": "application/json"}}),
    )
    assert_true(
        "/api/ path is API",
        is_api_request({"resource_type": "document", "url": "https://example.com/api/users", "response_headers": {}}),
    )
    assert_true(
        "POST with body is API",
        is_api_request({"resource_type": "other", "url": "https://example.com/submit", "response_headers": {}, "post_data": '{"key": "val"}'}),
    )
    assert_false(
        "GET image with no json is not API",
        is_api_request({"resource_type": "image", "url": "https://example.com/img.png", "response_headers": {"content-type": "image/png"}}),
    )


def test_infer_schema_from_value():
    print("infer_schema_from_value")
    assert_eq("string", infer_schema_from_value("hello"), {"type": "string"})
    assert_eq("integer", infer_schema_from_value(42), {"type": "integer"})
    assert_eq("number", infer_schema_from_value(3.14), {"type": "number"})
    assert_eq("boolean", infer_schema_from_value(True), {"type": "boolean"})
    assert_eq("null", infer_schema_from_value(None), {"type": "string", "nullable": True})
    assert_eq(
        "empty array",
        infer_schema_from_value([]),
        {"type": "array", "items": {"type": "string"}},
    )
    assert_eq(
        "array of ints",
        infer_schema_from_value([1, 2, 3]),
        {"type": "array", "items": {"type": "integer"}},
    )
    assert_eq(
        "simple object",
        infer_schema_from_value({"name": "test", "count": 5}),
        {"type": "object", "properties": {"name": {"type": "string"}, "count": {"type": "integer"}}},
    )
    assert_eq(
        "nested object",
        infer_schema_from_value({"user": {"id": 1}}),
        {"type": "object", "properties": {"user": {"type": "object", "properties": {"id": {"type": "integer"}}}}},
    )
    assert_eq(
        "array of objects",
        infer_schema_from_value([{"id": 1}]),
        {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}}}},
    )


def test_normalize_path_group():
    print("normalize_path_group")
    single = [{"url": "https://api.example.com/users/123"}]
    assert_eq("single path unchanged", normalize_path_group(single), "/users/123")

    group = [
        {"url": "https://api.example.com/users/1"},
        {"url": "https://api.example.com/users/2"},
        {"url": "https://api.example.com/users/3"},
    ]
    result = normalize_path_group(group)
    assert_eq("varying segment parametrized", result, "/users/{param1}")

    same = [
        {"url": "https://api.example.com/health"},
        {"url": "https://api.example.com/health"},
    ]
    assert_eq("identical paths unchanged", normalize_path_group(same), "/health")


def test_extract_query_params():
    print("extract_query_params")
    group = [
        {"url": "https://api.example.com/search?q=hello&page=1"},
        {"url": "https://api.example.com/search?q=world&page=2"},
    ]
    params = extract_query_params(group)
    assert_eq("extracts q param", params.get("q"), "hello")
    assert_eq("extracts page param", params.get("page"), "1")


def test_infer_response_schema():
    print("infer_response_schema")
    group_json_obj = [{"response_body": '{"name": "test", "items": [1, 2]}'}]
    schema = infer_response_schema(group_json_obj)
    assert_true("json object has type", schema is not None and schema.get("type") == "object")
    assert_true("json object has properties", "properties" in (schema or {}))

    group_json_arr = [{"response_body": '[{"id": 1}, {"id": 2}]'}]
    schema = infer_response_schema(group_json_arr)
    assert_true("json array has type array", schema is not None and schema.get("type") == "array")

    group_no_body = [{"response_body": None}]
    schema = infer_response_schema(group_no_body)
    assert_eq("no body returns None", schema, None)

    group_binary = [{"response_body": "<binary 1234 bytes>"}]
    schema = infer_response_schema(group_binary)
    assert_eq("binary body returns None", schema, None)


def test_infer_request_schema():
    print("infer_request_schema")
    group_post = [{"post_data": '{"name": "test"}'}]
    schema = infer_request_schema(group_post)
    assert_true("POST body has schema", schema is not None)

    group_no_post = [{"post_data": None}]
    schema = infer_request_schema(group_no_post)
    assert_eq("no POST body returns None", schema, None)


def test_build_openapi_spec_structure():
    print("build_openapi_spec structure")
    api_requests = [
        {
            "method": "GET",
            "url": "https://api.example.com/users",
            "resource_type": "fetch",
            "headers": {},
            "status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"users": [{"id": 1, "name": "Alice"}]}',
        },
        {
            "method": "POST",
            "url": "https://api.example.com/users",
            "resource_type": "fetch",
            "headers": {},
            "post_data": '{"name": "Bob"}',
            "status": 201,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"id": 2, "name": "Bob"}',
        },
    ]
    spec = build_openapi_spec("https://api.example.com", api_requests)
    assert_eq("openapi version", spec["openapi"], "3.0.3")
    assert_true("has info", "info" in spec)
    assert_true("has servers", len(spec["servers"]) > 0)
    assert_true("has paths", len(spec["paths"]) > 0)
    assert_in("has /users path", "/users", spec["paths"])
    assert_in("has GET method", "get", spec["paths"]["/users"])
    assert_in("has POST method", "post", spec["paths"]["/users"])
    assert_in("GET has 200 response", "200", spec["paths"]["/users"]["get"]["responses"])
    assert_in("POST has 201 response", "201", spec["paths"]["/users"]["post"]["responses"])
    assert_true("POST has requestBody", "requestBody" in spec["paths"]["/users"]["post"])


def test_build_openapi_spec_with_path_params():
    print("build_openapi_spec path params")
    api_requests = [
        {
            "method": "GET",
            "url": "https://api.example.com/users/1",
            "resource_type": "fetch",
            "headers": {},
            "status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"id": 1, "name": "Alice"}',
        },
        {
            "method": "GET",
            "url": "https://api.example.com/users/2",
            "resource_type": "fetch",
            "headers": {},
            "status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"id": 2, "name": "Bob"}',
        },
    ]
    spec = build_openapi_spec("https://api.example.com", api_requests)
    paths = list(spec["paths"].keys())
    assert_gt("multiple similar paths generated", len(paths), 0)
    has_users_path = any("users" in p for p in paths)
    assert_true("has users path", has_users_path)


def test_build_openapi_spec_with_query_params():
    print("build_openapi_spec query params")
    api_requests = [
        {
            "method": "GET",
            "url": "https://api.example.com/search?q=hello&limit=10",
            "resource_type": "fetch",
            "headers": {},
            "status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": '{"results": []}',
        },
    ]
    spec = build_openapi_spec("https://api.example.com", api_requests)
    path_item = spec["paths"]["/search"]["get"]
    assert_true("has parameters", "parameters" in path_item)
    param_names = [p["name"] for p in path_item.get("parameters", [])]
    assert_in("has q param", "q", param_names)
    assert_in("has limit param", "limit", param_names)


def test_e2e_with_real_log():
    print("e2e with real log file")
    data = load_log_file()
    requests = data.get("requests", [])
    url = data.get("url", "")

    api_requests = [r for r in requests if is_api_request(r)]
    assert_gt("has API requests", len(api_requests), 0)

    spec = build_openapi_spec(url, api_requests)

    assert_eq("openapi version", spec["openapi"], "3.0.3")
    assert_true("has info", "info" in spec)
    assert_true("has servers", len(spec["servers"]) > 0)
    assert_gt("has paths", len(spec["paths"]), 0)

    for path, methods in spec["paths"].items():
        for method, path_item in methods.items():
            assert_true(f"{method} {path} has operationId", "operationId" in path_item)
            assert_true(f"{method} {path} has responses", "responses" in path_item)

    commentary_paths = [p for p in spec["paths"] if "commentary" in p.lower()]
    assert_gt("has commentary API paths", len(commentary_paths), 0)

    for path in commentary_paths:
        for method, path_item in spec["paths"][path].items():
            responses = path_item.get("responses", {})
            for status_code, response in responses.items():
                if "content" in response:
                    schema = response["content"].get("application/json", {}).get("schema")
                    assert_true(
                        f"{method} {path} {status_code} has response schema",
                        schema is not None,
                    )


def main():
    tests = [
        test_is_api_request,
        test_infer_schema_from_value,
        test_normalize_path_group,
        test_extract_query_params,
        test_infer_response_schema,
        test_infer_request_schema,
        test_build_openapi_spec_structure,
        test_build_openapi_spec_with_path_params,
        test_build_openapi_spec_with_query_params,
        test_e2e_with_real_log,
    ]

    for test in tests:
        test()

    print(f"\n{'=' * 40}")
    total = passed + failed
    print(f"Results: {passed}/{total} passed", end="")
    if failed:
        print(f", {failed} FAILED")
    else:
        print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
