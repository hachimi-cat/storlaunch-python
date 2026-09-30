"""Test surface for the Storlaunch Python SDK.

Mirrors the Node SDK's `resources.test.ts` plus extra coverage for
the API-key header, idempotency, and webhook signature verification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import httpx
import pytest
import respx

from storlaunch import StorlaunchClient, StorlaunchError, verify_webhook


BASE = "https://storlaunch.test"


def _envelope(data):
    return {
        "data": data,
        "error": None,
        "meta": {"requestId": "req_1", "timestamp": "2026-01-01T00:00:00Z"},
    }


def _make_client(**overrides):
    return StorlaunchClient(
        api_key="sk_test_abc",
        base_url=BASE,
        **overrides,
    )


# ─── Construction ────────────────────────────────────────────────────────


def test_requires_an_api_key(monkeypatch):
    monkeypatch.delenv("STORLAUNCH_API_KEY", raising=False)
    with pytest.raises(ValueError, match="api_key is required"):
        StorlaunchClient()
    monkeypatch.setenv("STORLAUNCH_API_KEY", "sk_live_env")
    assert StorlaunchClient()._api_key == "sk_live_env"


def test_old_key_id_and_secret_say_what_changed():
    with pytest.raises(TypeError, match="removed in 0.2.0"):
        StorlaunchClient(key_id="AKIA", secret="s")


def test_base_url_trailing_slash_normalised():
    c = StorlaunchClient(api_key="sk_test_abc", base_url="https://x.test/")
    assert c._base_url == "https://x.test"


def test_context_manager_closes_owned_http():
    with _make_client() as c:
        assert c._owns_http is True
    # Calling again is harmless after close — but underlying client should be closed.
    assert c._http.is_closed is True


def test_external_http_not_closed():
    h = httpx.Client()
    c = StorlaunchClient(api_key="sk_test_abc", base_url=BASE, http=h)
    c.close()
    assert h.is_closed is False
    h.close()


# ─── Wire-level: headers + routing ───────────────────────────────────────


@respx.mock
def test_api_key_sent_as_bearer_and_nothing_else_to_authenticate():
    route = respx.get(f"{BASE}/api/v1/analytics/overview").mock(
        return_value=httpx.Response(200, json=_envelope({"ok": True}))
    )
    with _make_client() as c:
        c.analytics.overview()
    headers = route.calls.last.request.headers
    assert headers["Authorization"] == "Bearer sk_test_abc"
    assert not [h for h in headers if h.lower().startswith("x-storlaunch")]


# ─── Idempotency keys ────────────────────────────────────────────────────


@respx.mock
def test_create_auto_adds_idempotency_key():
    route = respx.post(f"{BASE}/api/v1/payment/checkout-sessions").mock(
        return_value=httpx.Response(200, json=_envelope({"id": "cs_1"}))
    )
    with _make_client() as c:
        c.payment.checkout_sessions.create({"amount": 10000, "currency": "IDR"})
    req = route.calls.last.request
    assert req.headers["X-Idempotency-Key"].startswith("idem_")
    assert req.headers["Idempotency-Key"] == req.headers["X-Idempotency-Key"]
    assert req.headers["Content-Type"] == "application/json"


@respx.mock
def test_get_does_not_add_idempotency_key():
    route = respx.get(f"{BASE}/api/v1/payment/checkout-sessions/cs_1").mock(
        return_value=httpx.Response(200, json=_envelope({"id": "cs_1"}))
    )
    with _make_client() as c:
        c.payment.checkout_sessions.get("cs_1")
    assert "Idempotency-Key" not in route.calls.last.request.headers
    assert "X-Idempotency-Key" not in route.calls.last.request.headers


@respx.mock
def test_two_creates_use_distinct_idempotency_keys():
    route = respx.post(f"{BASE}/api/v1/payment/checkout-sessions").mock(
        return_value=httpx.Response(200, json=_envelope({"id": "cs_1"}))
    )
    with _make_client() as c:
        c.payment.checkout_sessions.create({"amount": 1, "currency": "IDR"})
        c.payment.checkout_sessions.create({"amount": 2, "currency": "IDR"})
    k1 = route.calls[0].request.headers["Idempotency-Key"]
    k2 = route.calls[1].request.headers["Idempotency-Key"]
    assert k1 != k2


# ─── Route coverage (mirrors node test suite) ────────────────────────────


@respx.mock
def test_payment_subscriptions_cancel_deletes():
    at_period_end = respx.delete(f"{BASE}/api/v1/payment/subscriptions/sub_1").mock(
        return_value=httpx.Response(204)
    )
    now = respx.delete(
        f"{BASE}/api/v1/payment/subscriptions/sub_2", params={"immediate": "true"}
    ).mock(return_value=httpx.Response(204))
    with _make_client() as c:
        assert c.payment.subscriptions.cancel("sub_1") is None
        c.payment.subscriptions.cancel("sub_2", immediate=True)
    assert at_period_end.called and now.called


@respx.mock
def test_storefront_products_archive_deletes():
    route = respx.delete(f"{BASE}/api/v1/storefront/products/p_1").mock(
        return_value=httpx.Response(200, json=_envelope({"ok": True}))
    )
    with _make_client() as c:
        c.storefront.products.archive("p_1")
    assert route.called


@respx.mock
def test_account_blog_publish_posts():
    route = respx.post(f"{BASE}/api/v1/account/blog/posts/post_1/publish").mock(
        return_value=httpx.Response(200, json=_envelope({"ok": True}))
    )
    with _make_client() as c:
        c.account.blog.publish("post_1")
    assert route.called


@respx.mock
def test_modules_enable_posts_the_toggle():
    route = respx.post(f"{BASE}/api/v1/modules").mock(
        return_value=httpx.Response(200, json=_envelope({"ok": True}))
    )
    with _make_client() as c:
        c.modules.enable("marketing")
    assert json.loads(route.calls.last.request.content) == {"module": "marketing", "enabled": True}


@respx.mock
def test_csv_export_returns_the_text():
    route = respx.get(f"{BASE}/api/v1/ledger/entries.csv").mock(
        return_value=httpx.Response(200, text="id,amount\nle_1,100\n", headers={"content-type": "text/csv"})
    )
    with _make_client() as c:
        assert c.reports.export_ledger() == "id,amount\nle_1,100\n"
    assert route.called


@respx.mock
def test_reports_pnl_query_string():
    route = respx.get(
        f"{BASE}/api/v1/reports/pnl",
        params={"from": "2026-01-01", "to": "2026-06-30"},
    ).mock(return_value=httpx.Response(200, json=_envelope({"ok": True})))
    with _make_client() as c:
        c.reports.pnl(from_="2026-01-01", to="2026-06-30")
    assert route.called


@respx.mock
def test_passthrough_escape_hatch():
    route = respx.get(f"{BASE}/api/v1/custom/route").mock(
        return_value=httpx.Response(200, json=_envelope({"ok": True}))
    )
    with _make_client() as c:
        c.passthrough("GET", "/api/v1/custom/route")
    assert route.called


# ─── Error handling ──────────────────────────────────────────────────────


@respx.mock
def test_enveloped_error_raises_storlaunch_error():
    respx.get(f"{BASE}/api/v1/analytics/overview").mock(
        return_value=httpx.Response(
            400,
            json={
                "data": None,
                "error": {"code": "bad_request", "message": "nope"},
                "meta": {"requestId": "req_x", "timestamp": ""},
            },
        )
    )
    with _make_client() as c:
        with pytest.raises(StorlaunchError) as ei:
            c.analytics.overview()
    err = ei.value
    assert err.status == 400
    assert err.code == "bad_request"
    assert err.message == "nope"
    assert err.request_id == "req_x"


@respx.mock
def test_non_json_response_raises_invalid_response():
    respx.get(f"{BASE}/api/v1/analytics/overview").mock(
        return_value=httpx.Response(200, text="<html>oops</html>", headers={"content-type": "text/html"})
    )
    with _make_client() as c:
        with pytest.raises(StorlaunchError) as ei:
            c.analytics.overview()
    assert ei.value.code == "invalid_response"


# ─── Webhook signature verification ──────────────────────────────────────


def _sign_webhook(body: bytes, secret: str, ts: int) -> str:
    payload = f"{ts}.".encode() + body
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_verify_webhook_accepts_valid_signature():
    secret = "whsec_xyz"
    body = b'{"id":"evt_1"}'
    ts = int(time.time())
    sig = _sign_webhook(body, secret, ts)
    assert verify_webhook(body, f"t={ts},v1={sig}", secret) is True


def test_verify_webhook_rejects_tampered_body():
    secret = "whsec_xyz"
    ts = int(time.time())
    sig = _sign_webhook(b'{"id":"evt_1"}', secret, ts)
    assert verify_webhook(b'{"id":"evt_2"}', f"t={ts},v1={sig}", secret) is False


def test_verify_webhook_rejects_stale_timestamp():
    secret = "whsec_xyz"
    body = b'{"id":"evt_1"}'
    ts = int(time.time()) - 10_000
    sig = _sign_webhook(body, secret, ts)
    assert verify_webhook(body, f"t={ts},v1={sig}", secret) is False


def test_verify_webhook_accepts_str_body():
    secret = "whsec_xyz"
    body = '{"id":"evt_1"}'
    ts = int(time.time())
    sig = _sign_webhook(body.encode(), secret, ts)
    assert verify_webhook(body, f"t={ts},v1={sig}", secret) is True


def test_verify_webhook_rejects_malformed_header():
    secret = "whsec_xyz"
    assert verify_webhook(b"{}", "garbage", secret) is False
    assert verify_webhook(b"{}", "", secret) is False
    assert verify_webhook(b"{}", "t=abc,v1=zz", secret) is False
