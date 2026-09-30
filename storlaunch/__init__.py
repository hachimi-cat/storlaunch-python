"""Official Python SDK for Storlaunch.

Mirrors the Node SDK (``@forjio/storlaunch-node``) surface 1:1:

- An API key (``sk_live_…`` / ``sk_test_…``) sent as ``Authorization: Bearer``.
- Auto-generated idempotency keys for unsafe mutations.
- Resource namespaces covering payment, storefront, account, analytics,
  billing, modules, manual orders, onboarding, shipping, inventory, ledger,
  reports, payouts and discount codes, plus ``client.api``: every feature
  route, generated from the API spec.
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

__version__ = "0.2.0"
