"""Typed error classes for the Storlaunch SDK."""

from __future__ import annotations

from typing import Optional


class StorlaunchError(Exception):
    """Raised when a Storlaunch API call fails.

    Attributes
    ----------
    status:
        HTTP status code (0 for transport-level errors like timeouts).
    code:
        Machine-readable error code from the API envelope, or one of
        ``"timeout"``, ``"network_error"``, ``"invalid_response"`` for
        SDK-side failures.
    message:
        Human-readable description.
    request_id:
        The ``meta.requestId`` echoed by the API, when available.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.request_id = request_id

    def __repr__(self) -> str:
        return (
            f"StorlaunchError(status={self.status}, code={self.code!r}, "
            f"message={self.message!r}, request_id={self.request_id!r})"
        )
