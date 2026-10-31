"""Turning a confirmed drop into a push the user receives.

The decision to notify is made elsewhere (the poller, from the pure core); this
module only renders the message and hands it to a transport. The transport is
injected: in tests and demos it records the messages, in production it is
Firebase Cloud Messaging. That split means the message wording is tested
without any network, and swapping or stubbing FCM never touches the wording.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Protocol

from .models import Watch
from .pricing import Drop


@dataclass(frozen=True)
class PushMessage:
    """A rendered, transport-agnostic notification."""

    title: str
    body: str
    # Structured payload so the app can deep-link to the product.
    data: dict


def _short(name: str, limit: int = 48) -> str:
    name = name.strip()
    return name if len(name) <= limit else name[: limit - 1].rstrip() + "…"


def render(watch: Watch, drop: Drop) -> PushMessage:
    """Render the Turkish drop notification for one watch."""
    product = watch.product
    title = f"{_short(product.name)} indirimde"
    body = f"{drop.was.format()} → {drop.now.format()}  (%{drop.pct} indirim)"
    return PushMessage(
        title=title,
        body=body,
        data={
            "productKey": product.key,
            "url": product.url,
            "store": product.store,
            "now": str(drop.now.minor),
            "was": str(drop.was.minor),
            "currency": drop.now.currency,
        },
    )


class Notifier(Protocol):
    def notify(self, watch: Watch, drop: Drop) -> None: ...


# A function that actually delivers a rendered message to one device token.
Transport = Callable[[str, PushMessage], None]

# A function that returns the device tokens registered for a user.
TokenResolver = Callable[[str], List[str]]


@dataclass
class PushNotifier:
    """Renders the message and sends it to each of the user's device tokens.

    `transport` is the delivery mechanism (FCM in production); `tokens` maps a
    user to their registered devices. A user with no tokens is simply skipped —
    there is nowhere to deliver to, which is not an error.
    """

    transport: Transport
    tokens: TokenResolver

    def notify(self, watch: Watch, drop: Drop) -> None:
        message = render(watch, drop)
        for token in self.tokens(watch.user_id):
            self.transport(token, message)


@dataclass
class RecordingNotifier:
    """Keeps every message instead of sending it — for tests and dry runs."""

    sent: List[tuple] = field(default_factory=list)

    def notify(self, watch: Watch, drop: Drop) -> None:
        self.sent.append((watch.user_id, render(watch, drop)))
