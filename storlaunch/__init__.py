"""Official Python SDK for Storlaunch.

Mirrors the Node SDK (``@forjio/storlaunch-node``) surface 1:1:

- HMAC-signed requests with ``Storlaunch-HMAC-SHA256`` Authorization.
- Partner-billing scoping via :meth:`StorlaunchClient.for_merchant` →
  ``X-Storlaunch-On-Behalf-Of`` header.
- Auto-generated ``Idempotency-Key`` headers for unsafe mutations.
- 47-route resource surface covering payment, storefront, account,
  analytics, billing, modules, manualOrders, onboarding, shipping,
  inventory, ledger, reports, payouts, discountCodes, inboundWebhooks,
  and buyer.
- Webhook signature verification (``X-Storlaunch-Signature`` HMAC).
"""

from .client import StorlaunchClient
from .errors import StorlaunchError
from .resources import (
    ApiEnvelope,
    ApiEnvelopeError,
    ApiEnvelopeMeta,
    CheckoutSession,
    Customer,
    CurrencyCode,
    Invoice,
    Plan,
    Product,
    Subscription,
    WebhookEvent,
)
from .webhooks import verify_webhook

__all__ = [
    # client
    "StorlaunchClient",
    # errors
    "StorlaunchError",
    # resources
    "ApiEnvelope",
    "ApiEnvelopeError",
    "ApiEnvelopeMeta",
    "CheckoutSession",
    "Customer",
    "CurrencyCode",
    "Invoice",
    "Plan",
    "Product",
    "Subscription",
    "WebhookEvent",
    # webhooks
    "verify_webhook",
]

__version__ = "0.1.0"
