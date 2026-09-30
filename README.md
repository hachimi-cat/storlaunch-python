# storlaunch (Python SDK)

Official Python SDK for [Storlaunch](https://storlaunch.com) — full
parity with the Node SDK (`@forjio/storlaunch-node`).

## Install

```bash
pip install forjio-storlaunch
```

## Quick start

```python
import os
from storlaunch import StorlaunchClient

client = StorlaunchClient(
    api_key=os.environ["STORLAUNCH_API_KEY"],  # sk_live_… or sk_test_… (the default source)
    base_url="https://storlaunch.com",  # default
)

products = client.storefront.products.list({"limit": 20})

# Every feature route, one method each (generated from the API spec)
codes = client.api.discount_codes_list(limit=5)
```

## Auth

Mint a secret key in the dashboard under **Settings → API keys**:
`sk_live_…` (production) or `sk_test_…` (sandbox). Every request carries it
as a bearer token, and nothing else authenticates:

```
Authorization: Bearer sk_live_…
```

A key belongs to one workspace and acts as its owner. Two things it cannot
do: create or revoke API keys (that needs a signed-in session, so
`client.account.api_keys.create/revoke` answer 403 to a key), and call the
shopper routes under `/api/v1/checkout`, which take the shopper's own
storefront session.

Until 0.2.0 this SDK signed requests (`key_id` + `secret`,
`Storlaunch-HMAC-SHA256`) and scoped them with `for_merchant()` /
`X-Storlaunch-On-Behalf-Of`. The API never accepted either, so they are gone.

## Idempotency

Unsafe mutations (create checkout session, create subscription, issue
license, adjust inventory, request payout, etc.) auto-generate an
idempotency key, sent as both `X-Idempotency-Key` (what Storlaunch's replay
guard reads) and `Idempotency-Key` (what it forwards to Plugipay). To pin one
yourself, drop down to `client.request(...)`.

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
