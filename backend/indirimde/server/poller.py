"""One poll cycle over every stored watch.

This is the server-side equivalent of the Android WorkManager job: walk the
watches, poll each through the same pure `poll_once`, and write back the new
baseline so the next cycle compares against it. A store outage leaves the
baseline untouched (poll_once returns reachable=False), exactly as on-device.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..notify import Notifier
from ..stores.base import StoreAdapter
from ..watcher import poll_once
from .repo import Repo


@dataclass
class CycleSummary:
    checked: int = 0
    reachable: int = 0
    unreachable: int = 0
    baselines: int = 0
    drops: int = 0


def poll_all(repo: Repo, store: StoreAdapter, notifier: Notifier) -> CycleSummary:
    """Poll every watch once; persist new baselines; return what happened."""
    summary = CycleSummary()
    for watch in repo.all_watches():
        summary.checked += 1
        result = poll_once(watch, store, notifier)
        if not result.reachable:
            summary.unreachable += 1
            continue
        summary.reachable += 1
        # watch.last_seen was advanced by poll_once to the price just read.
        if watch.last_seen is not None:
            repo.set_last_seen(watch.user_id, watch.product.key, watch.last_seen)
        if result.baseline_set:
            summary.baselines += 1
        if result.drop is not None:
            summary.drops += 1
    return summary
