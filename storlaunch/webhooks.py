"""HMAC-SHA256 signature verifier for Storlaunch webhooks.

Storlaunch signs every delivery with::

    X-Storlaunch-Signature: t=<unix_seconds>,v1=<hex>

where ``<hex>`` is ``HMAC-SHA256(secret, f"{t}.{rawBody}")``. The raw
bytes of the request body matter — verifying the already-parsed JSON
will re-serialise with different whitespace and the signature will
never match.

Flask example::

    from flask import Flask, request, abort
    from storlaunch import verify_webhook
    import os

    app = Flask(__name__)
    SECRET = os.environ["STORLAUNCH_WEBHOOK_SECRET"]

    @app.post("/webhooks/storlaunch")
    def storlaunch_webhook():
        raw = request.get_data()  # bytes, unparsed
        sig = request.headers.get("X-Storlaunch-Signature", "")
        if not verify_webhook(raw, sig, SECRET):
            abort(400)
        event = request.get_json()
        # handle event...
        return "", 204
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional, Tuple, Union


def _parse_signature(header: str) -> Optional[Tuple[int, str]]:
    timestamp: Optional[int] = None
    v1: Optional[str] = None
    for part in header.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        if k == "t":
            try:
                timestamp = int(v)
            except ValueError:
                return None
        elif k == "v1":
            v1 = v
    if timestamp is None or v1 is None:
        return None
    return timestamp, v1


def verify_webhook(
    raw_body: Union[bytes, str],
    signature_header: str,
    secret: str,
    *,
    tolerance_seconds: int = 300,
    now: Optional[float] = None,
) -> bool:
    """Return True iff the signature is valid and within the replay window.

    Parameters
    ----------
    raw_body:
        The *unparsed* request body as received over the wire. If you
        pass a ``str``, it's encoded as UTF-8 before hashing.
    signature_header:
        The value of the ``X-Storlaunch-Signature`` header.
    secret:
        The subscription signing secret (typically starts with ``whsec_``).
    tolerance_seconds:
        Reject signatures older than this many seconds. Default 300
        (5 minutes) — matches Stripe/GitHub conventions.
    now:
        Inject a clock for tests; seconds since epoch.
    """
    if not signature_header or not secret:
        return False
    parsed = _parse_signature(signature_header)
    if parsed is None:
        return False
    timestamp, expected_v1 = parsed

    current = now if now is not None else time.time()
    if abs(current - timestamp) > tolerance_seconds:
        return False

    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    payload = f"{timestamp}.".encode("utf-8") + body_bytes
    computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed, expected_v1)


__all__ = ["verify_webhook"]
