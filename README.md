# Geo IP Intelligence

Geo enriches IPv4 and IPv6 addresses with ASN ownership and GeoLite2 city data. It works as a conventional HTTP API, an MCP tool, and a Lambda function invoked by other workloads.

Each successful lookup includes:

- `asn.id`, `asn.org`, and `asn.net` from GeoLite2 ASN.
- `geo.country`, `geo.state`, `geo.city`, and `geo.cidr` from GeoLite2 City.
- Version timestamps, serving region, and the required MaxMind attribution.

Invalid addresses are returned in order with an entry-level `error`, so batch callers can retain their input-to-output mapping.

## HTTP API

The public endpoint is `https://api.lukach.io/geo`.

```bash
curl 'https://api.lukach.io/geo?ip=1.1.1.1'
curl 'https://api.lukach.io/geo?ip=1.1.1.1,2606:4700:4700::1111'
curl 'https://api.lukach.io/geo/1.1.1.1'
```

`GET /geo` without an IP looks up the request source address. Query parameters accept `ip`, `ipAddress`, or `query`; they may be repeated or comma-separated.

`POST` accepts a JSON object containing `ip`, `ipAddress`, `query`, or `ips`.

```bash
curl --request POST 'https://api.lukach.io/geo' \
    --header 'content-type: application/json' \
    --data '{"ips":["1.1.1.1","8.8.8.8"]}'
```

An HTTP response has an API Gateway status code and a JSON body. Empty input and too many addresses return `400`; an oversized request body returns `413`; a request too close to the Lambda timeout returns `503`.

## MCP

The handler supports MCP JSON-RPC `POST` requests using protocol version `2025-03-26`. The MCP tool is named `geo_lookup`.
The public MCP gateway is `https://api.lukach.io/mcp?endpoint=geo`.

```json
{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "geo_lookup",
        "arguments": {
            "ips": ["1.1.1.1", "2606:4700:4700::1111"]
        }
    }
}
```

Supported methods are `initialize`, `notifications/initialized`, `tools/list`, and `tools/call`. `geo_lookup` accepts either `ip` (one address) or `ips` (an array). Successful tool calls return both MCP text content and `structuredContent`, allowing MCP clients to use the result without parsing text.

## Direct Lambda Invocation

The deployed function is named `search`. A direct event contains the same input keys as HTTP JSON, and returns the enrichment payload directly rather than an API Gateway envelope.

```python
import boto3
import json

client = boto3.client("lambda", region_name="us-east-1")
response = client.invoke(
        FunctionName="search",
        InvocationType="RequestResponse",
        Payload=json.dumps({"ips": ["1.1.1.1", "8.8.8.8"]}),
)
payload = json.load(response["Payload"])
```

The caller's Lambda execution role needs `lambda:InvokeFunction` for the `search` function ARN. The CDK stacks grant invoke access to principals in the configured AWS Organization; cross-organization callers require an explicit resource-policy grant.

For in-process Python callers, import `lookup` from `search.search` and call `lookup({"ips": [...]})`.

## Response

```json
{
    "results": [
        {
            "ip": "1.1.1.1",
            "asn": {
                "id": 13335,
                "org": "Cloudflare, Inc.",
                "net": "1.1.1.0/24"
            },
            "geo": {
                "country": "Australia - AU",
                "state": "Queensland",
                "city": "South Brisbane",
                "cidr": "1.1.1.0/24"
            }
        }
    ],
    "requested_count": 1,
    "attribution": "This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com.",
    "timestamp_utc": "2026-08-19T00:00:00Z",
    "region": "us-east-1"
}
```

The `geolite2-asn.mmdb` and `geolite2-city.mmdb` fields are included when database metadata is available.

## Limits and Development

The defaults are 300 IPs per request, a 256 KiB request body, and a 1.5 second minimum remaining Lambda execution budget. Configure these with `MAX_IPS_PER_REQUEST`, `MAX_REQUEST_BODY_BYTES`, and `MIN_REMAINING_TIME_MS`.

Run the focused handler tests with:

```bash
python -m unittest tests/test_search.py -v
```

GeoLite2 data is created by MaxMind. See the [GeoLite2 documentation](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) for database details and licensing.

