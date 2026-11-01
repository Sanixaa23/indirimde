"""Delivering a rendered push through Firebase Cloud Messaging.

firebase-admin is imported lazily and only when credentials are actually
present. With no credentials the server still runs end to end — the transport
falls back to logging each push instead of sending it — so the whole flow
(search, watch, poll, drop decision, render) is exercisable without a Firebase
project. Wiring real FCM is then only a matter of dropping in a service account.

Credentials are looked up, in order:
  1. INDIRIMDE_FCM_CREDENTIALS           (path to a service-account JSON)
  2. GOOGLE_APPLICATION_CREDENTIALS      (the Google standard)
  3. ./service-account.json              (next to where the server is run)
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from ..notify import PushMessage, Transport

log = logging.getLogger("indirimde.fcm")


def _credentials_path() -> Optional[str]:
    for env in ("INDIRIMDE_FCM_CREDENTIALS", "GOOGLE_APPLICATION_CREDENTIALS"):
        path = os.environ.get(env)
        if path and os.path.exists(path):
            return path
    default = os.path.join(os.getcwd(), "service-account.json")
    return default if os.path.exists(default) else None


def _log_transport(reason: str) -> Transport:
    def send(token: str, message: PushMessage) -> None:
        log.warning(
            "FCM not configured (%s) - would send to %s: %s / %s",
            reason,
            token[:12] + "…" if len(token) > 12 else token,
            message.title,
            message.body,
        )

    return send


def make_transport() -> Tuple[Transport, str]:
    """Return (transport, human-readable status).

    Never raises: if Firebase cannot be set up for any reason, returns the
    logging stub so the server starts regardless.
    """
    path = _credentials_path()
    if path is None:
        return _log_transport("no credentials"), "stub (no credentials)"

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        return _log_transport("firebase-admin not installed"), "stub (no firebase-admin)"

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(path))
    except Exception as exc:  # bad/invalid credentials file
        return _log_transport(f"init failed: {exc}"), f"stub (init failed)"

    def send(token: str, message: PushMessage) -> None:
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=message.title, body=message.body
            ),
            data={k: str(v) for k, v in message.data.items()},
        )
        try:
            messaging.send(msg)
        except Exception as exc:
            # One dead token must not sink a poll cycle.
            log.warning("FCM send failed for %s: %s", token[:12], exc)

    return send, f"firebase ({os.path.basename(path)})"
