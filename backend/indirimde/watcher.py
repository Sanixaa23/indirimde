"""Polling one watch: read the price, decide, update, maybe notify.

This is where the pure core meets the fragile store. Every reading either
updates the watch's baseline or is discarded; the baseline only ever moves to a
price we actually read, so a store outage can never be mistaken for a price
change. The first successful reading sets the baseline and never notifies —
there is nothing yet to compare against.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Watch
from .notify import Notifier
from .pricing import Drop, evaluate
from .stores.base import StoreAdapter


@dataclass(frozen=True)
class PollResult:
    """What one poll did, so callers can log and the history can grow."""

    reachable: bool
    drop: Optional[Drop] = None
    # True only on the reading that first established the baseline.
    baseline_set: bool = False


def poll_once(watch: Watch, store: StoreAdapter, notifier: Notifier) -> PollResult:
    """Poll a single watch once.

    Returns reachable=False and changes nothing when the store could not give a
    price. Otherwise records the new price, notifies if it dropped past the
    watch's rule, and returns the outcome.
    """
    price = store.fetch_price(watch.product)
    if price is None:
        return PollResult(reachable=False)

    if watch.last_seen is None:
        watch.last_seen = price.sale
        return PollResult(reachable=True, baseline_set=True)

    drop = evaluate(watch.last_seen, price, watch.rule)
    watch.last_seen = price.sale
    if drop is not None:
        notifier.notify(watch, drop)
    return PollResult(reachable=True, drop=drop)
