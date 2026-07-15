# storlaunch (Python SDK)

Official Python SDK for [Storlaunch](https://storlaunch.com) — full
parity with the Node SDK (`@forjio/storlaunch-node`).

## Install

```bash
pip install storlaunch
```

## Quick start

```python
from storlaunch import StorlaunchClient

client = StorlaunchClient(
    key_id="AKIASTOR...",
    secret="...",
    base_url="https://storlaunch.com",  # default
)

# Platform-level call
products = client.storefront.products.list({"limit": 20})

# Partner scoped (Pattern 2 partner billing)
merchant = client.for_merchant("acc_xyz")
orders = merchant.payment.checkout_sessions.list()
```

## Auth (HMAC SHA-256)

Every request is signed locally with `key_id` + `secret`. The signed
string is `METHOD\nPATH\nTIMESTAMP\nSHA256(body)[\nIDEMPOTENCY_KEY]`.
The resulting hex digest is sent as

```
Authorization: Storlaunch-HMAC-SHA256 keyId=<key_id>, scope=*, signature=<hex>
X-Storlaunch-Timestamp: <unix_seconds>
```

`for_merchant("acc_xyz")` returns a new client that adds
`X-Storlaunch-On-Behalf-Of: acc_xyz` to every request — used for
Pattern 2 (Shopify-Apps-style) partner billing where the platform
admin key acts on behalf of a customer workspace.

## Idempotency

Unsafe mutations (create checkout session, pay invoice, issue license,
adjust inventory, request payout, etc.) auto-generate an
`Idempotency-Key: idem_<uuid>` header. To pin one yourself, drop down
to `client.request(...)`.

## Webhooks

```python
from storlaunch import verify_webhook

raw = request.get_data()  # bytes — DO NOT re-serialise JSON
sig = request.headers.get("X-Storlaunch-Signature", "")
if not verify_webhook(raw, sig, secret):
    abort(400)
```

## Resource surface

| Namespace | Methods |
|---|---|
| `payment` | checkout_sessions, plans, subscriptions, invoices, receipts, customers, plugipay_settings, portal_sessions, webhook_endpoints, webhook_events |
| `storefront` | products (+files), licenses, deliveries, public |
| `account` | profile, pixels, abandoned_cart, feeds, blog, referrals, api_keys, audit_log, domains |
| top-level | analytics, billing, modules, manual_orders, onboarding, shipping, inventory, ledger, reports, payouts, discount_codes, inbound_webhooks, buyer |

For anything not yet typed, use `client.passthrough(method, path, body)`.

## Errors

All API failures raise `StorlaunchError(status, code, message, request_id)`.
Transport failures (DNS, connect refused, timeout) raise the same class
with `status=0` and `code` in `{"timeout", "network_error",
"invalid_response"}`.

## Dev

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
```
