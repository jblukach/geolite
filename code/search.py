import base64
import importlib
import ipaddress
import json
import os
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qs, unquote


IP_INPUT_KEYS = ("ip", "ipAddress", "query")
MAX_IPS_PER_REQUEST_ENV = "MAX_IPS_PER_REQUEST"
MAX_IPS_PER_REQUEST_DEFAULT = 300
MAX_REQUEST_BODY_BYTES_ENV = "MAX_REQUEST_BODY_BYTES"
MAX_REQUEST_BODY_BYTES_DEFAULT = 262144
MIN_REMAINING_TIME_MS_ENV = "MIN_REMAINING_TIME_MS"
MIN_REMAINING_TIME_MS_DEFAULT = 1500
ATTRIBUTION_TEXT = "This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com."


def _max_ips_per_request() -> int:
    raw_value = os.environ.get(MAX_IPS_PER_REQUEST_ENV, str(MAX_IPS_PER_REQUEST_DEFAULT)).strip()
    if not raw_value:
        return MAX_IPS_PER_REQUEST_DEFAULT
    value = int(raw_value)
    if value <= 0:
        raise RuntimeError(f"{MAX_IPS_PER_REQUEST_ENV} must be greater than zero")
    return value


def _max_request_body_bytes() -> int:
    raw_value = os.environ.get(MAX_REQUEST_BODY_BYTES_ENV, str(MAX_REQUEST_BODY_BYTES_DEFAULT)).strip()
    if not raw_value:
        return MAX_REQUEST_BODY_BYTES_DEFAULT
    value = int(raw_value)
    if value <= 0:
        raise RuntimeError(f"{MAX_REQUEST_BODY_BYTES_ENV} must be greater than zero")
    return value


def _min_remaining_time_ms() -> int:
    raw_value = os.environ.get(MIN_REMAINING_TIME_MS_ENV, str(MIN_REMAINING_TIME_MS_DEFAULT)).strip()
    if not raw_value:
        return MIN_REMAINING_TIME_MS_DEFAULT
    value = int(raw_value)
    if value <= 0:
        raise RuntimeError(f"{MIN_REMAINING_TIME_MS_ENV} must be greater than zero")
    return value


def _has_processing_budget(context: Any, min_remaining_ms: int) -> bool:
    if context is None:
        return True

    remaining_time_fn = getattr(context, "get_remaining_time_in_millis", None)
    if not callable(remaining_time_fn):
        return True

    try:
        remaining_ms = int(remaining_time_fn())
    except (TypeError, ValueError):
        return True

    return remaining_ms >= min_remaining_ms


def _append_ip_values(values: list[str], candidate: Any) -> None:
    if candidate is None:
        return
    if isinstance(candidate, str):
        parts = [part.strip() for part in candidate.split(",") if part.strip()]
        values.extend(parts)
        return
    if isinstance(candidate, list):
        for item in candidate:
            _append_ip_values(values, item)


def _decoded_body(event: dict[str, Any]) -> str:
    body = event.get("body")
    if not isinstance(body, str):
        return ""

    if not event.get("isBase64Encoded"):
        return body

    try:
        return base64.b64decode(body).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""


def _input_ips(event: dict[str, Any]) -> list[str]:
    values: list[str] = []

    path_parameters = event.get("pathParameters") or {}
    path_parameter_supplied = False
    if isinstance(path_parameters, dict):
        if path_parameters.get("ip") is not None or path_parameters.get("proxy") is not None:
            path_parameter_supplied = True
        _append_ip_values(values, path_parameters.get("ip"))
        _append_ip_values(values, path_parameters.get("proxy"))

    raw_path = event.get("rawPath")
    if not path_parameter_supplied and isinstance(raw_path, str) and raw_path.strip():
        path = raw_path.strip().rstrip("/")
        if "/geo/" in path:
            _append_ip_values(values, unquote(path.rsplit("/", 1)[-1]))

    raw_query = event.get("rawQueryString")
    raw_query_values: dict[str, list[str]] = {}
    if isinstance(raw_query, str) and raw_query.strip():
        raw_query_values = parse_qs(raw_query, keep_blank_values=False)
        for key in IP_INPUT_KEYS:
            for raw_value in raw_query_values.get(key, []):
                _append_ip_values(values, raw_value)

    multi_value_query_params = event.get("multiValueQueryStringParameters") or {}
    if isinstance(multi_value_query_params, dict):
        for key in IP_INPUT_KEYS:
            _append_ip_values(values, multi_value_query_params.get(key))

    query_params = event.get("queryStringParameters") or {}
    if isinstance(query_params, dict):
        for key in IP_INPUT_KEYS:
            if key in raw_query_values:
                continue
            _append_ip_values(values, query_params.get(key))

    for key in IP_INPUT_KEYS:
        _append_ip_values(values, event.get(key))
    _append_ip_values(values, event.get("ips"))

    body = _decoded_body(event)
    if body.strip():
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for key in IP_INPUT_KEYS:
                _append_ip_values(values, payload.get(key))
            _append_ip_values(values, payload.get("ips"))
        if isinstance(payload, list):
            _append_ip_values(values, payload)

    if values:
        return values

    request_context = event.get("requestContext") or {}
    if isinstance(request_context, dict):
        http_context = request_context.get("http") or {}
        if isinstance(http_context, dict):
            method = str(http_context.get("method", "")).upper()
            source_ip = http_context.get("sourceIp")
            cleaned_raw_path = str(event.get("rawPath", "")).rstrip("/")
            if method == "GET" and cleaned_raw_path == "/geo":
                _append_ip_values(values, source_ip)

    return values


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, indent=4),
    }


def _error_payload(message: str) -> dict[str, Any]:
    return {"error": message}


def _compact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    compacted = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        compacted[key] = value
    return compacted


def _read_metadata_file(file_name: str) -> str | None:
    for path in (file_name, f"/opt/{file_name}", f"/var/task/{file_name}"):
        try:
            with open(path, "r", encoding="utf-8") as file_handle:
                value = file_handle.read().strip()
            if value:
                return value
        except OSError:
            continue
    return None


def _format_utc_timestamp(raw_value: str | None) -> str | None:
    if not raw_value:
        return None

    value = raw_value.strip()
    if not value:
        return None

    try:
        parsed_http_date = parsedate_to_datetime(value)
        if parsed_http_date.tzinfo is None:
            parsed_http_date = parsed_http_date.replace(tzinfo=UTC)
        return parsed_http_date.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        pass

    try:
        parsed_iso = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed_iso.tzinfo is None:
            parsed_iso = parsed_iso.replace(tzinfo=UTC)
        return parsed_iso.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def _mmdb_path(file_name: str) -> str:
    for path in (file_name, f"/opt/{file_name}", f"/var/task/{file_name}"):
        if os.path.isfile(path):
            return path
    return file_name


def _lookup_mmdb(readers: dict[str, Any], ip_text: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    asn_data = readers["asn"].get(ip_text) or {}
    city_data = readers["city"].get(ip_text) or {}

    asn_payload = _compact_dict(
        {
            "id": asn_data.get("autonomous_system_number"),
            "org": asn_data.get("autonomous_system_organization"),
            "net": asn_data.get("network"),
        }
    )

    country_name = ((city_data.get("country") or {}).get("names") or {}).get("en")
    country_iso = (city_data.get("country") or {}).get("iso_code")
    if country_name and country_iso:
        country_value = f"{country_name} - {country_iso}"
    else:
        country_value = country_name or country_iso

    subdivisions = city_data.get("subdivisions") or []
    subdivision = subdivisions[0] if subdivisions else {}
    city_payload = _compact_dict(
        {
            "country": country_value,
            "state": (subdivision.get("names") or {}).get("en"),
            "city": ((city_data.get("city") or {}).get("names") or {}).get("en"),
            "cidr": city_data.get("network"),
        }
    )

    return (asn_payload or None), (city_payload or None)


def handler(event, context):
    min_remaining_ms = _min_remaining_time_ms()

    body_text = _decoded_body(event or {})
    if body_text:
        raw_body_bytes = len(body_text.encode("utf-8"))
        max_body_bytes = _max_request_body_bytes()
        if raw_body_bytes > max_body_bytes:
            return _response(
                413,
                _error_payload(
                    f"Request body too large: {raw_body_bytes} bytes. Maximum allowed is {max_body_bytes}"
                ),
            )

    input_ips = _input_ips(event or {})
    if not input_ips:
        return _response(400, _error_payload("At least one IP address is required"))

    max_ips_per_request = _max_ips_per_request()
    if len(input_ips) > max_ips_per_request:
        return _response(
            400,
            _error_payload(
                f"Too many IPs requested: {len(input_ips)}. Maximum allowed is {max_ips_per_request}"
            ),
        )

    if not _has_processing_budget(context, min_remaining_ms):
        return _response(
            503,
            _error_payload("Insufficient processing time remaining. Reduce batch size and retry."),
        )

    parsed_entries: list[dict[str, Any]] = []
    for raw_ip in input_ips:
        try:
            parsed_entries.append({"ip": str(ipaddress.ip_address(raw_ip)), "valid": True})
        except ValueError:
            parsed_entries.append({"ip": str(raw_ip), "valid": False})

    unique_valid_ips: list[str] = []
    seen: set[str] = set()
    for entry in parsed_entries:
        if not entry["valid"]:
            continue
        ip_text = str(entry["ip"])
        if ip_text in seen:
            continue
        seen.add(ip_text)
        unique_valid_ips.append(ip_text)

    lookup_cache: dict[str, tuple[dict[str, Any] | None, dict[str, Any] | None]] = {}
    if unique_valid_ips:
        maxminddb = importlib.import_module("maxminddb")

        with maxminddb.open_database(_mmdb_path("GeoLite2-ASN.mmdb")) as asn_reader:
            with maxminddb.open_database(_mmdb_path("GeoLite2-City.mmdb")) as city_reader:
                readers = {"asn": asn_reader, "city": city_reader}
                for ip_text in unique_valid_ips:
                    if not _has_processing_budget(context, min_remaining_ms):
                        return _response(
                            503,
                            _error_payload(
                                "Insufficient processing time remaining. Reduce batch size and retry."
                            ),
                        )
                    lookup_cache[ip_text] = _lookup_mmdb(readers, ip_text)

    results: list[dict[str, Any]] = []
    for entry in parsed_entries:
        ip_text = str(entry["ip"])
        if not entry["valid"]:
            results.append({"ip": ip_text, "error": f"Invalid IP address: {ip_text}"})
            continue

        asn_data, city_data = lookup_cache.get(ip_text, (None, None))
        output: dict[str, Any] = {"ip": ip_text}
        if asn_data is not None:
            output["asn"] = asn_data
        if city_data is not None:
            output["geo"] = city_data
        results.append(output)

    response_payload: dict[str, Any] = {
        "results": results,
        "requested_count": len(input_ips),
        "attribution": ATTRIBUTION_TEXT,
    }

    asn_updated = _format_utc_timestamp(_read_metadata_file("asn.updated"))
    city_updated = _format_utc_timestamp(_read_metadata_file("city.updated"))
    if asn_updated is not None:
        response_payload["geolite2-asn.mmdb"] = asn_updated
    if city_updated is not None:
        response_payload["geolite2-city.mmdb"] = city_updated

    now_utc = datetime.fromtimestamp(time.time(), tz=UTC).isoformat().replace("+00:00", "Z")
    response_payload["timestamp_utc"] = now_utc
    response_payload["region"] = os.environ.get("AWS_REGION")

    return _response(200, _compact_dict(response_payload))