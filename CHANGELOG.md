# Changelog

## 0.2.0
- **Published on PyPI as `forjio-storlaunch`** (`pip install forjio-storlaunch`); the import is still `import storlaunch`. The old `storlaunch` 0.1.0 upload belongs to an account Forjio no longer publishes from (like `forjio-linksnap`).
- **Auth is an API key now.** Pass `api_key`: an `sk_live_…` / `sk_test_…` key from Settings → API keys (default: env `STORLAUNCH_API_KEY`), sent as `Authorization: Bearer <key>`. The `key_id`/`secret` request signing and `for_merchant()`/`on_behalf_of` (`X-Storlaunch-On-Behalf-Of`) are removed: the API never accepted them, so every call answered 401. A key belongs to one workspace.
- Writes send their idempotency key as `X-Idempotency-Key` (what Storlaunch's replay guard reads; subscription and portal-session creates require it) and `Idempotency-Key` (what it forwards to Plugipay).
- A 204 returns None; a CSV export returns its text.
- Methods now call the route the API really has: `payment.plans.archive` → `DELETE /payment/plans/{id}`; `payment.subscriptions.cancel(id, immediate=True)` → `DELETE /payment/subscriptions/{id}`; `storefront.licenses.revoke(key)` → `DELETE /storefront/licenses/{key}`; `account.api_keys.revoke` → `DELETE /account/api-keys/{id}` and `create` takes `name` + `environment`; `account.referrals.update_program` → `PUT`; `billing.checkout(plan=, interval=, currency=)` → `POST /billing/plugipay-invoice`; `modules.enable/disable` → `POST /modules {module, enabled}`; `inventory.levels({"variantId": …})` → `GET /inventory/stock`; `ledger.list/balances/adjust` → `/ledger/entries`, `/ledger/balance`, `/ledger/adjustments`; `reports.export_ledger()` → `GET /ledger/entries.csv`; `onboarding.complete_step` → `onboarding.complete(enable_payment=)`.
- Removed, because the API has no such route: `payment.invoices.finalize/pay/void`, `payment.plugipay_settings`, `storefront.products.list_files` (files come with `products.get`), `storefront.deliveries.create`, `analytics.storefront/funnel`, `billing.current_plan` (use `billing.subscription`), `modules.status` (use `modules.list`), `manual_orders.create`, `discount_codes.validate`, `inbound_webhooks`. Also removed: `buyer`, whose shopper routes take the shopper's storefront session, never an API key.
- `account.blog.list` is annotated as what it returns, a dict `{"posts": [...]}`.
- A test checks every hand-written method's route against the API spec (`backend/openapi.json`).

## 0.1.1
- `client.api`: every feature route of the Storlaunch API, one method each (`client.api.<area>_<action>(...)`), generated from the API spec and signed like every other call.

## 0.1.0
- Initial tracked release.
