"""High-level Storlaunch client mirroring ``@forjio/storlaunch-node``.

Auth = HMAC-SHA256 partner-billing (Pattern 2, Shopify-Apps style).
Every request is signed with the caller's ``keyId``+``secret`` and may
be scoped to a merchant via ``for_merchant(account_id)`` which forwards
the merchant id in the ``X-Storlaunch-On-Behalf-Of`` header.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
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

    def archive(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/payment/plans/{id}/archive", body={})


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

    def cancel(self, id: str, input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.request(
            "POST", f"/api/v1/payment/subscriptions/{id}/cancel", body=input or {}
        )


class _PaymentInvoices:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/payment/invoices{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/payment/invoices/{id}")

    def finalize(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/payment/invoices/{id}/finalize", body={})

    def pay(self, id: str) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            f"/api/v1/payment/invoices/{id}/pay",
            body={},
            idempotency_key=self._c._gen_idem(),
        )

    def void(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/payment/invoices/{id}/void", body={})


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


class _PaymentPlugipaySettings:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def get(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/payment/plugipay-settings")

    def update(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/payment/plugipay-settings", body=patch)


class _PaymentPortalSessions:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def create(self, *, customer_id: str, return_url: str) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/payment/portal-sessions",
            body={"customerId": customer_id, "returnUrl": return_url},
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
        self.plugipay_settings = _PaymentPlugipaySettings(c)
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

    def list_files(self, product_id: str) -> List[Any]:
        return self._c.request("GET", f"/api/v1/storefront/products/{product_id}/files")

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

    def revoke(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/storefront/licenses/{id}/revoke", body={})


class _StorefrontDeliveries:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/storefront/deliveries{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/storefront/deliveries/{id}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/storefront/deliveries",
            body=input,
            idempotency_key=self._c._gen_idem(),
        )


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

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
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

    def update_program(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("PATCH", "/api/v1/account/referrals", body=patch)


class _AccountApiKeys:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/account/api-keys")

    def create(self, input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.request(
            "POST",
            "/api/v1/account/api-keys",
            body=input or {},
            idempotency_key=self._c._gen_idem(),
        )

    def revoke(self, id: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/account/api-keys/{id}/revoke", body={})


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

    def storefront(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/analytics/storefront{_qs(params)}")

    def funnel(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/analytics/funnel{_qs(params)}")


class _Billing:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def plans(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/billing/plans")

    def current_plan(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/billing/plan")

    def subscription(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/billing/subscription")

    def usage(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/billing/usage")

    def invoices(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/billing/invoices{_qs(params)}")

    def checkout(
        self,
        *,
        plan_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"planId": plan_id}
        if success_url is not None:
            body["successUrl"] = success_url
        if cancel_url is not None:
            body["cancelUrl"] = cancel_url
        return self._c.request("POST", "/api/v1/billing/checkout", body=body)

    def cancel(self) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/billing/cancel", body={})


class _Modules:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/modules")

    def enable(self, name: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/modules/{name}/enable", body={})

    def disable(self, name: str) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/modules/{name}/disable", body={})

    def status(self, name: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/modules/{name}")


class _ManualOrders:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/manual-orders{_qs(params)}")

    def create(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/manual-orders", body=input, idempotency_key=self._c._gen_idem()
        )

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/manual-orders/{id}")


class _Onboarding:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def status(self) -> Dict[str, Any]:
        return self._c.request("GET", "/api/v1/onboarding")

    def complete_step(self, step: str, input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._c.request("POST", f"/api/v1/onboarding/{step}", body=input or {})


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

    def levels(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/inventory/levels{_qs(params)}")

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
        return self._c.request("GET", f"/api/v1/ledger{_qs(params)}")

    def balances(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/ledger/balances")

    def adjust(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/ledger/adjust", body=input, idempotency_key=self._c._gen_idem()
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

    def export_ledger(
        self, *, from_: str, to: str, format: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"from": from_, "to": to}
        if format is not None:
            params["format"] = format
        return self._c.request("GET", f"/api/v1/reports/export-ledger{_qs(params)}")


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

    def validate(self, *, code: str) -> Dict[str, Any]:
        return self._c.request(
            "POST", "/api/v1/discount-codes/validate", body={"code": code}
        )


class _InboundWebhooks:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/webhooks{_qs(params)}")

    def get(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/webhooks/{id}")


class _Buyer:
    def __init__(self, c: "StorlaunchClient") -> None:
        self._c = c

    def list_orders(self, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        return self._c.request("GET", f"/api/v1/checkout/orders{_qs(params)}")

    def get_order(self, id: str) -> Dict[str, Any]:
        return self._c.request("GET", f"/api/v1/checkout/orders/{id}")

    def list_addresses(self) -> List[Any]:
        return self._c.request("GET", "/api/v1/checkout/addresses")

    def add_address(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._c.request("POST", "/api/v1/checkout/addresses", body=input)

    def delete_address(self, id: str) -> Dict[str, Any]:
        return self._c.request("DELETE", f"/api/v1/checkout/addresses/{id}")


class StorlaunchClient:
    """Sync Storlaunch API client.

    Parameters
    ----------
    key_id:
        HMAC access-key id, e.g. ``"AKIASTOR<random>"``.
    secret:
        HMAC secret. Used to sign every request; never sent in plaintext.
    base_url:
        API base URL. Defaults to ``https://storlaunch.com``.
    on_behalf_of:
        Optional default merchant ``accountId`` — forwarded as
        ``X-Storlaunch-On-Behalf-Of``. Only allowed when ``key_id`` holds
        the ``storlaunch:platform:admin`` scope. Prefer
        :meth:`for_merchant` for per-merchant scoping.
    timeout_ms:
        Per-request timeout. Default 30 000ms.
    http:
        Optional pre-built ``httpx.Client`` (used for testing /
        connection-pooling). If omitted, the SDK creates and owns one.
    """

    def __init__(
        self,
        *,
        key_id: str,
        secret: str,
        base_url: str = "https://storlaunch.com",
        on_behalf_of: Optional[str] = None,
        timeout_ms: int = 30_000,
        http: Optional[httpx.Client] = None,
    ) -> None:
        if not key_id or not secret:
            raise ValueError("StorlaunchClient: key_id and secret are required")
        self._key_id = key_id
        self._secret = secret
        self._base_url = base_url.rstrip("/")
        self._default_on_behalf_of = on_behalf_of
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
        self.inbound_webhooks = _InboundWebhooks(self)
        self.buyer = _Buyer(self)

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "StorlaunchClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ─── Merchant scoping ────────────────────────────────────────────────

    def for_merchant(self, account_id: str) -> "StorlaunchClient":
        """Return a new client that scopes every request to ``account_id``.

        Sends ``X-Storlaunch-On-Behalf-Of: <account_id>`` on every call.
        The underlying ``httpx.Client`` is shared so the cloned client
        does not need its own connection pool.
        """
        clone = StorlaunchClient(
            key_id=self._key_id,
            secret=self._secret,
            base_url=self._base_url,
            on_behalf_of=account_id,
            timeout_ms=self._timeout_ms,
            http=self._http,
        )
        return clone

    # ─── Signing ─────────────────────────────────────────────────────────

    def _sign(
        self,
        *,
        method: str,
        path: str,
        body: Optional[str],
        idempotency_key: Optional[str],
    ) -> Dict[str, str]:
        ts = str(int(time.time()))
        body_hash = hashlib.sha256((body or "").encode("utf-8")).hexdigest()
        idem = f"\n{idempotency_key}" if idempotency_key else ""
        string_to_sign = f"{method.upper()}\n{path}\n{ts}\n{body_hash}{idem}"
        signature = hmac.new(
            self._secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {"signature": signature, "timestamp": ts}

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
        on_behalf_of: Optional[str] = None,
    ) -> Any:
        body_json = json.dumps(body, separators=(",", ":")) if body is not None else None
        signed = self._sign(
            method=method, path=path, body=body_json, idempotency_key=idempotency_key
        )
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Authorization": (
                f"Storlaunch-HMAC-SHA256 keyId={self._key_id}, scope=*, "
                f"signature={signed['signature']}"
            ),
            "X-Storlaunch-Timestamp": signed["timestamp"],
        }
        if body_json is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        effective_obo = on_behalf_of if on_behalf_of is not None else self._default_on_behalf_of
        if effective_obo:
            headers["X-Storlaunch-On-Behalf-Of"] = effective_obo

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
        try:
            env = json.loads(text) if text else {}
        except ValueError as e:
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

    def passthrough(
        self, method: str, path: str, body: Any = None
    ) -> Any:
        """Generic escape hatch for routes not yet typed."""
        return self.request(method, path, body=body)


__all__ = ["StorlaunchClient"]
