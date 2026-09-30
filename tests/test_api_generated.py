"""client.api: every feature route, one method each, generated from the API spec
(scripts/apigen.sh). Calls carry the same API key as every other request."""

from __future__ import annotations

import json
from typing import List
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from storlaunch import StorlaunchClient


def _client(seen: List[httpx.Request]) -> StorlaunchClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = {"data": {"ok": True}, "error": None, "meta": {"requestId": "r"}}
        return httpx.Response(200, content=json.dumps(body).encode())

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return StorlaunchClient(api_key="sk_test_gen", base_url="https://storlaunch.test", http=http)


def test_create_sends_the_fields_storlaunch_validates_with_the_api_key() -> None:
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.api.discount_codes_create(code="SPRING10", type_="percent", value=10, currency="IDR", public=False)
    request = seen[0]
    assert (request.method, request.url.path) == ("POST", "/api/v1/discount-codes")
    assert json.loads(request.content) == {"code": "SPRING10", "type": "percent", "value": 10, "currency": "IDR", "public": False}
    assert request.headers["authorization"] == "Bearer sk_test_gen"
    assert request.headers["x-idempotency-key"].startswith("idem_")
    assert request.headers.get("idempotency-key", "").startswith("idem_")


def test_path_and_query() -> None:
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.api.discount_codes_get("dc 1")
    client.api.discount_codes_list(limit=5, active=True)
    assert seen[0].url.raw_path.decode() == "/api/v1/discount-codes/dc%201"
    assert "idempotency-key" not in seen[0].headers
    assert seen[1].url.path == "/api/v1/discount-codes"
    assert parse_qs(urlsplit(str(seen[1].url)).query) == {"limit": ["5"], "active": ["true"]}


def test_a_field_read_from_query_or_body_is_sent_once_in_the_body() -> None:
    seen: List[httpx.Request] = []
    client = _client(seen)
    client.api.checkout_cart_merge(account_slug="acme", items=[])
    assert seen[0].url.query == b""
    assert json.loads(seen[0].content) == {"accountSlug": "acme", "items": []}


def test_a_required_field_is_asked_for() -> None:
    client = _client([])
    with pytest.raises(ValueError, match="needs code"):
        client.api.discount_codes_create(type_="percent", value=10, currency="IDR")


def test_every_feature_route_has_a_method() -> None:
    methods = [n for n in dir(_client([]).api) if not n.startswith("_")]
    assert len(methods) > 290
