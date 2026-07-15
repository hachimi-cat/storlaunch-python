"""Typed dataclasses for common Storlaunch API resources.

The on-the-wire shape is JSON; the SDK returns plain ``dict`` / ``list``
values from each request. These dataclasses are provided for callers who
want light static typing — they accept the raw envelope ``data`` payloads
and ignore unknown fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ApiEnvelopeMeta:
    request_id: str
    timestamp: str
    cursor: Optional[str] = None
    has_more: Optional[bool] = None


@dataclass
class ApiEnvelopeError:
    code: str
    message: str
    doc_url: Optional[str] = None


@dataclass
class ApiEnvelope:
    """The standard `{ data, error, meta }` response envelope."""

    data: Any = None
    error: Optional[ApiEnvelopeError] = None
    meta: Optional[ApiEnvelopeMeta] = None


@dataclass
class CheckoutSession:
    id: str
    status: str
    amount: int
    currency: str
    url: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CheckoutSession":
        known = {"id", "status", "amount", "currency", "url"}
        return cls(
            id=d["id"],
            status=d["status"],
            amount=int(d["amount"]),
            currency=d["currency"],
            url=d.get("url"),
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class Plan:
    id: str
    name: str
    amount: int
    currency: str
    interval: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Plan":
        known = {"id", "name", "amount", "currency", "interval"}
        return cls(
            id=d["id"],
            name=d["name"],
            amount=int(d["amount"]),
            currency=d["currency"],
            interval=d.get("interval"),
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class Subscription:
    id: str
    status: str
    plan_id: str
    customer_id: str
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Subscription":
        known = {"id", "status", "planId", "customerId"}
        return cls(
            id=d["id"],
            status=d["status"],
            plan_id=d["planId"],
            customer_id=d["customerId"],
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class Invoice:
    id: str
    status: str
    amount: int
    currency: str
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Invoice":
        known = {"id", "status", "amount", "currency"}
        return cls(
            id=d["id"],
            status=d["status"],
            amount=int(d["amount"]),
            currency=d["currency"],
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class Product:
    id: str
    slug: str
    name: str
    price: int
    currency: str
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Product":
        known = {"id", "slug", "name", "price", "currency"}
        return cls(
            id=d["id"],
            slug=d["slug"],
            name=d["name"],
            price=int(d["price"]),
            currency=d["currency"],
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class Customer:
    id: str
    email: str
    name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Customer":
        known = {"id", "email", "name"}
        return cls(
            id=d["id"],
            email=d["email"],
            name=d.get("name"),
            extra={k: v for k, v in d.items() if k not in known},
        )


@dataclass
class WebhookEvent:
    id: str
    type: str
    data: Dict[str, Any]
    created_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WebhookEvent":
        return cls(
            id=d["id"],
            type=d["type"],
            data=d.get("data", {}),
            created_at=d.get("createdAt"),
        )


CurrencyCode = str  # "IDR" | "USD" — kept loose for forward compat.


__all__ = [
    "ApiEnvelope",
    "ApiEnvelopeError",
    "ApiEnvelopeMeta",
    "CheckoutSession",
    "Plan",
    "Subscription",
    "Invoice",
    "Product",
    "Customer",
    "WebhookEvent",
    "CurrencyCode",
]
