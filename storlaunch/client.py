"""High-level Storlaunch client mirroring ``@forjio/storlaunch-node``.

Auth = a secret API key (``sk_live_…`` / ``sk_test_…``) sent as
``Authorization: Bearer <key>``. A key belongs to one workspace.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from .errors import StorlaunchError


def _qs(params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return ""
    entries = [(k, v) for k, v in params.items() if v is not None]
    if not entries:
        return ""
    return "?" + urlencode([(k, str(v)) for k, v in entries])


class _PaymentCheckoutSessions:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/checkout-sessions{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/checkout-sessions/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/payment/checkout-sessions",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )


class _PaymentPlans:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/plans{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/plans/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/payment/plans", body=input, idempotency_key=self._c._gen_idem()
        )

    def update(self, id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", f"/api/v1/payment/plans/{id}", body=patch)

    def archive(self, id: str) -> None:
        """Archives the plan (DELETE /payment/plans/{id}); existing subscribers keep it."""
        return self._c.request("DELETE", f"/api/v1/payment/plans/{id}")


class _PaymentSubscriptions:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/subscriptions{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/subscriptions/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/payment/subscriptions",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def cancel(self, id: str, *, immediate: bool = False) -> None:
        """Cancels at the end of the current period, or now with ``immediate=True``."""
        suffix = "?immediate=true" if immediate else ""
        return self._c.request("DELETE", f"/api/v1/payment/subscriptions/{id}{suffix}")


class _PaymentInvoices:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/invoices{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/invoices/{id}")


class _PaymentReceipts:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/receipts{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/receipts/{id}")


class _PaymentCustomers:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/customers{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/customers/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/payment/customers",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def update(self, id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", f"/api/v1/payment/customers/{id}", body=patch)


class _PaymentPortalSessions:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def create(self, *, customer_id: str, return_url: str) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/payment/portal-sessions",
            body={"customerId": customer_id, "returnUrl": return_url},
            idempotency_key=self._c._gen_idem(),
        )


class _PaymentWebhookEndpoints:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/payment/webhook-endpoints")

    def create(
        self, *, url: str, events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"url": url}
        if events is not None:
            body["events"] = events
        return self._c.request(
            "POST",
            "/api/v1/payment/webhook-endpoints",
            body=body,
            idempotency_key=self._c._gen_idem(),
        )

    def delete(self, id: str) -> Dict[str, Any]:
        return self._c.request("DELETE", f"/api/v1/payment/webhook-endpoints/{id}")


class _PaymentWebhookEvents:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/webhook-events{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/webhook-events/{id}")


class _Payment:
    def __init__(self, c: "StorlaunchClient") -> None:
        self.checkout_sessions = _PaymentCheckoutSessions(c)
        self.plans = _PaymentPlans(c)
        self.subscriptions = _PaymentSubscriptions(c)
        self.invoices = _PaymentInvoices(c)
        self.receipts = _PaymentReceipts(c)
        self.customers = _PaymentCustomers(c)
        self.portal_sessions = _PaymentPortalSessions(c)
        self.webhook_endpoints = _PaymentWebhookEndpoints(c)
        self.webhook_events = _PaymentWebhookEvents(c)


class _StorefrontProducts:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/storefront/products{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/storefront/products/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/storefront/products",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def update(self, id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", f"/api/v1/storefront/products/{id}", body=patch)

    def archive(self, id: str) -> Dict[str, Any]:
        return self._c.request("DELETE", f"/api/v1/storefront/products/{id}")

    def add_file(self, product_id: str, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", f"/api/v1/storefront/products/{product_id}/files", body=input
        )

    def remove_file(self, product_id: str, file_id: str) -> Dict[str, Any]:
        return self._c.request(
            "DELETE", f"/api/v1/storefront/products/{product_id}/files/{file_id}"
        )


class _StorefrontLicenses:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/storefront/licenses{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/storefront/licenses/{id}")

    def issue(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/storefront/licenses",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def revoke(self, key: str) -> None:
        """Revokes a license by its key (DELETE /storefront/licenses/{key})."""
        return self._c.request("DELETE", f"/api/v1/storefront/licenses/{key}")


class _StorefrontDeliveries:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/storefront/deliveries{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/storefront/deliveries/{id}")


class _StorefrontPublic:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get(self, slug: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/storefront/public/{slug}")


class _Storefront:
    def __init__(self, c: "StorlaunchClient") -> None:
        self.products = _StorefrontProducts(c)
        self.licenses = _StorefrontLicenses(c)
        self.deliveries = _StorefrontDeliveries(c)
        self.public = _StorefrontPublic(c)


class _AccountPixels:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/account/pixels")

    def update(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/account/pixels", body=patch)


class _AccountAbandonedCart:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get_config(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/account/abandoned-cart")

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/account/abandoned-cart", body=patch)


class _AccountFeeds:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get_config(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/account/feeds")

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/account/feeds", body=patch)


class _AccountBlog:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """``{"posts": [...]}``."""
        return self._c.request("GET", f"/api/v1/account/blog/posts{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/account/blog/posts/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/account/blog/posts", body=input)

    def update(self, id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", f"/api/v1/account/blog/posts/{id}", body=patch)

    def publish(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/account/blog/posts/{id}/publish", body={})

    def delete(self, id: str) -> Dict[str, Any]:
        return self._c.request("DELETE", f"/api/v1/account/blog/posts/{id}")


class _AccountReferrals:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get_program(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/account/referrals")

    def update_program(self, program: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PUT", "/api/v1/account/referrals", body=program)


class _AccountApiKeys:
    """Creating and revoking keys needs a signed-in session; an API key gets 403."""

    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/account/api-keys")

    def create(self, *, name: str, environment: str) -> Dict[str, Any]:
        """``environment``: ``"production"`` (an ``sk_live_`` key) or ``"sandbox"`` (``sk_test_``)."""
        return self._c.request(
            "POST",
            "/api/v1/account/api-keys",
            body={"name": name, "environment": environment},
            idempotency_key=self._c._gen_idem(),
        )

    def revoke(self, id: str) -> None:
        return self._c.request("DELETE", f"/api/v1/account/api-keys/{id}")


class _AccountAuditLog:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/account/audit-log{_qs(params)}")


class _AccountDomains:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/account/domains")

    def add(self, *, domain: str) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/account/domains", body={"domain": domain})

    def verify(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/account/domains/{id}/verify", body={})

    def remove(self, id: str) -> Dict[str, Any]:
        return self._c.request("DELETE", f"/api/v1/account/domains/{id}")


class _Account:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c
        self.pixels = _AccountPixels(c)
        self.abandoned_cart = _AccountAbandonedCart(c)
        self.feeds = _AccountFeeds(c)
        self.blog = _AccountBlog(c)
        self.referrals = _AccountReferrals(c)
        self.api_keys = _AccountApiKeys(c)
        self.audit_log = _AccountAuditLog(c)
        self.domains = _AccountDomains(c)

    def profile(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/account")

    def update_profile(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/account", body=patch)


class _Analytics:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def overview(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/analytics/overview")


class _Billing:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def plans(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/billing/plans")

    def subscription(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/billing/subscription")

    def usage(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/billing/usage")

    def invoices(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/billing/invoices{_qs(params)}")

    def checkout(
        self,
        *,
        plan: str,
        interval: Optional[str] = None,
        currency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upgrade: starts a Plugipay subscription for the tier (``"pro"``, ``"business"``
        or ``"scale"``; ``interval`` ``"month"`` or ``"year"``) and returns where to pay."""
        body: Dict[str, Any] = {"plan": plan}
        if interval is not None:
            body["interval"] = interval
        if currency is not None:
            body["currency"] = currency
        return self._c.request(
            "POST", "/api/v1/billing/plugipay-invoice", body=body, idempotency_key=self._c._gen_idem()
        )

    def cancel(self) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/billing/cancel", body={})


class _Modules:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> Dict[str, Any]:
        """``{modules, allowed, plan}``: each module's on/off state and which the plan allows."""
        return self._c.request("GET", "/api/v1/modules")

    def enable(self, name: str) -> Dict[str, Any]:
        """``name``: ``"payment"``, ``"fulfillment"`` or ``"marketing"``."""
        return self._c.request("POST", "/api/v1/modules", body={"module": name, "enabled": True})

    def disable(self, name: str) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/modules", body={"module": name, "enabled": False})


class _ManualOrders:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/manual-orders{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/manual-orders/{id}")


class _Onboarding:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def status(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/onboarding")

    def complete(self, *, enable_payment: Optional[bool] = None) -> Dict[str, Any]:
        """Marks onboarding done; ``enable_payment=True`` also turns on the Payment module."""
        body: Dict[str, Any] = {}
        if enable_payment is not None:
            body["enablePayment"] = enable_payment
        return self._c.request("POST", "/api/v1/onboarding/complete", body=body)


class _Shipping:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def couriers(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/shipping/couriers")

    def origin(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/shipping/origin")

    def set_origin(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/shipping/origin", body=input)

    def rates(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/shipping/rates", body=input)

    def list_shipments(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/shipping/shipments{_qs(params)}")

    def create_shipment(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/shipping/shipments",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )


class _Inventory:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def levels(self, params: Dict[str, Any]) -> List[Any]:
        """Stock levels of one variant: ``{"variantId": ...}`` is required."""
        return self._c.request("GET", f"/api/v1/inventory/stock{_qs(params)}")

    def movements(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/inventory/movements{_qs(params)}")

    def adjust(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/inventory/adjust",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def warehouses(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/inventory/warehouses")

    def add_warehouse(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/inventory/warehouses", body=input)


class _Ledger:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/ledger/entries{_qs(params)}")

    def balances(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/ledger/balance")

    def adjust(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/ledger/adjustments", body=input, idempotency_key=self._c._gen_idem()
        )


class _Reports:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def pnl(self, *, from_: str, to: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/reports/pnl{_qs({'from': from_, 'to': to})}")

    def cash_flow(self, *, from_: str, to: str) -> Dict[str, Any]:
        return self._c.request(
            "GET", f"/api/v1/reports/cash-flow{_qs({'from': from_, 'to': to})}"
        )

    def export_ledger(self) -> str:
        """The whole ledger as CSV text (GET /ledger/entries.csv)."""
        return self._c.request("GET", "/api/v1/ledger/entries.csv")


class _Payouts:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payouts{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payouts/{id}")

    def request_payout(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/payouts", body=input, idempotency_key=self._c._gen_idem()
        )

    def bank_account(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/payouts/bank-account")

    def update_bank_account(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/payouts/bank-account", body=input)


class _DiscountCodes:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/discount-codes{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/discount-codes/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/discount-codes",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )

    def update(self, id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", f"/api/v1/discount-codes/{id}", body=patch)


class StorlaunchClient:
    """Sync Storlaunch API client.

    Parameters
    ----------
    api_key:
        A secret API key from the dashboard (Settings → API keys):
        ``sk_live_…`` or ``sk_test_…``. Sent as ``Authorization: Bearer
        <api_key>`` on every request. Defaults to env ``STORLAUNCH_API_KEY``.
    base_url:
        API base URL. Defaults to ``https://storlaunch.com``.
    timeout_ms:
        Per-request timeout. Default 30 000ms.
    http:
        Optional pre-built ``httpx.Client`` (used for testing /
        connection-pooling). If omitted, the SDK creates and owns one.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = "https://storlaunch.com",
        timeout_ms: int = 30_000,
        http: Optional[httpx.Client] = None,
        **legacy: Any,
    ) -> None:
        key = api_key or os.environ.get("STORLAUNCH_API_KEY")
        if legacy:
            if set(legacy) <= {"key_id", "secret", "on_behalf_of"}:
                raise TypeError(
                    "StorlaunchClient: key_id/secret request signing and on_behalf_of were "
                    "removed in 0.2.0 (the API never accepted them). Pass api_key: an "
                    "sk_live_… or sk_test_… key from Settings → API keys."
                )
            raise TypeError(f"StorlaunchClient: unexpected argument(s) {sorted(legacy)}")
        if not key:
            raise ValueError(
                "StorlaunchClient: api_key is required (an sk_live_… or sk_test_… key from "
                "Settings → API keys), or set STORLAUNCH_API_KEY."
            )
        self._api_key = key
        self._base_url = base_url.rstrip("/")
        self._timeout_ms = timeout_ms
        self._http = http if http is not None else httpx.Client(timeout=timeout_ms / 1000)
        self._owns_http = http is None

        # Resource namespaces
        self.payment = _Payment(self)
        self.storefront = _Storefront(self)
        self.account = _Account(self)
        self.analytics = _Analytics(self)
        self.billing = _Billing(self)
        self.modules = _Modules(self)
        self.manual_orders = _ManualOrders(self)
        self.onboarding = _Onboarding(self)
        self.shipping = _Shipping(self)
        self.inventory = _Inventory(self)
        self.ledger = _Ledger(self)
        self.reports = _Reports(self)
        self.payouts = _Payouts(self)
        self.discount_codes = _DiscountCodes(self)
        # Every feature route, one method each (generated from the API spec).
        from .api_generated import GeneratedApi

        self.api = GeneratedApi(self)

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "StorlaunchClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _gen_idem(self) -> str:
        return f"idem_{uuid.uuid4()}"

    # ─── Core request ────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """One API call. Sends ``Authorization: Bearer <api_key>``, JSON bodies as
        ``Content-Type: application/json``, and on writes that carry one the
        idempotency key as both ``X-Idempotency-Key`` (what Storlaunch's own replay
        guard reads) and ``Idempotency-Key`` (what it forwards to Plugipay).
        Returns the envelope's ``data``; a 204 returns None and a non-JSON
        success (CSV exports) returns the text."""
        body_json = (
            json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            if body is not None
            else None
        )
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        if body_json is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
            headers["Idempotency-Key"] = idempotency_key

        url = f"{self._base_url}{path}"
        try:
            res = self._http.request(
                method,
                url,
                headers=headers,
                content=body_json,
            )
        except httpx.TimeoutException as e:
            raise StorlaunchError(
                0, "timeout", f"Storlaunch request timed out after {self._timeout_ms}ms"
            ) from e
        except httpx.HTTPError as e:
            raise StorlaunchError(0, "network_error", str(e)) from e

        text = res.text
        if res.is_success and not text:
            return None
        try:
            env = json.loads(text) if text else {}
        except ValueError as e:
            # A CSV export is text; a web page means the base URL is not the API.
            if res.is_success and not res.headers.get("content-type", "").startswith("text/html"):
                return text
            raise StorlaunchError(
                res.status_code, "invalid_response", f"Non-JSON response: {text[:200]}"
            ) from e

        err = env.get("error") if isinstance(env, dict) else None
        if res.is_error or err:
            err = err or {"code": "unknown", "message": f"HTTP {res.status_code}"}
            request_id = None
            if isinstance(env, dict):
                meta = env.get("meta") or {}
                request_id = meta.get("requestId") if isinstance(meta, dict) else None
            raise StorlaunchError(
                res.status_code,
                err.get("code", "unknown"),
                err.get("message", f"HTTP {res.status_code}"),
                request_id,
            )

        return env.get("data") if isinstance(env, dict) else env

    def _apigen_request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        body: Any = None,
    ) -> Any:
        """The call behind ``client.api.*`` (api_generated.py): the same request (API
        key, idempotency key on writes)."""
        entries = [
            (k, v if isinstance(v, str) else json.dumps(v, separators=(",", ":")))
            for k, v in (query or {}).items()
            if v is not None
        ]
        return self.request(
            method,
            path + ("?" + urlencode(entries) if entries else ""),
            body=body,
            idempotency_key=None if method.upper() == "GET" else self._gen_idem(),
        )

    def passthrough(
        self, method: str, path: str, body: Any = None
    ) -> Any:
        """Generic escape hatch for routes not yet typed."""
        return self.request(
            method,
            path,
            body=body,
            idempotency_key=None if method.upper() == "GET" else self._gen_idem(),
        )


__all__ = ["StorlaunchClient"]
