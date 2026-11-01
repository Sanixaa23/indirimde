"""The server's small durable state: which devices track which products.

A JSON file, guarded by a lock and written atomically (temp file + replace) so
a crash mid-write cannot corrupt it. This is deliberately not a database: the
state is tiny, a handful of watches per user, and keeping it a plain file keeps
the server a single process with nothing to provision.

Everything the drop decision needs still comes from the pure core; this only
remembers users' intentions between polls and restarts.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from ..models import Product, Watch
from ..money import Money
from ..pricing import DropRule
from .serial import product_from_dict, product_to_dict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repo:
    """Device tokens and watches, persisted to one JSON file."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.RLock()
        # devices: user_id -> [token, ...]   watches: list of watch dicts
        self._state: Dict[str, object] = {"devices": {}, "watches": []}
        self._load()

    # ---- persistence -----------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._state["devices"] = data.get("devices", {})
                self._state["watches"] = data.get("watches", [])
        except (OSError, ValueError):
            # A corrupt or unreadable file is treated as empty rather than
            # crashing the server; the next write rewrites it cleanly.
            pass

    def _save(self) -> None:
        directory = os.path.dirname(self._path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._state, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # ---- devices ---------------------------------------------------------
    def register_device(self, user_id: str, token: str) -> None:
        with self._lock:
            devices: dict = self._state["devices"]  # type: ignore[assignment]
            tokens = devices.setdefault(user_id, [])
            if token not in tokens:
                tokens.append(token)
                self._save()

    def unregister_device(self, user_id: str, token: str) -> None:
        with self._lock:
            devices: dict = self._state["devices"]  # type: ignore[assignment]
            tokens = devices.get(user_id, [])
            if token in tokens:
                tokens.remove(token)
                self._save()

    def tokens_for(self, user_id: str) -> List[str]:
        with self._lock:
            devices: dict = self._state["devices"]  # type: ignore[assignment]
            return list(devices.get(user_id, []))

    # ---- watches ---------------------------------------------------------
    def _watches(self) -> List[dict]:
        return self._state["watches"]  # type: ignore[return-value]

    def upsert_watch(
        self,
        user_id: str,
        product: Product,
        rule: DropRule,
        baseline: Optional[Money],
    ) -> None:
        """Create a watch, or update its rule if it already exists.

        `baseline` seeds last_seen so the very next poll can already detect a
        drop against the price the user saw when adding it. An existing watch
        keeps its own last_seen (we do not reset history on a rule change).
        """
        with self._lock:
            for w in self._watches():
                if w["userId"] == user_id and w["productKey"] == product.key:
                    w["minPct"] = str(rule.min_pct)
                    w["minMinor"] = rule.min_minor
                    w["product"] = product_to_dict(product)
                    self._save()
                    return
            self._watches().append(
                {
                    "userId": user_id,
                    "productKey": product.key,
                    "product": product_to_dict(product),
                    "minPct": str(rule.min_pct),
                    "minMinor": rule.min_minor,
                    "lastSeenMinor": None if baseline is None else baseline.minor,
                    "createdAt": _now_iso(),
                }
            )
            self._save()

    def remove_watch(self, user_id: str, product_key: str) -> bool:
        with self._lock:
            before = len(self._watches())
            self._state["watches"] = [
                w
                for w in self._watches()
                if not (w["userId"] == user_id and w["productKey"] == product_key)
            ]
            removed = len(self._watches()) != before
            if removed:
                self._save()
            return removed

    def set_last_seen(self, user_id: str, product_key: str, money: Money) -> None:
        with self._lock:
            for w in self._watches():
                if w["userId"] == user_id and w["productKey"] == product_key:
                    w["lastSeenMinor"] = money.minor
                    self._save()
                    return

    def _to_watch(self, w: dict) -> Watch:
        product = product_from_dict(w["product"])
        rule = DropRule(
            min_pct=Decimal(str(w.get("minPct", "1"))),
            min_minor=int(w.get("minMinor", 100)),
        )
        last_minor = w.get("lastSeenMinor")
        watch = Watch(user_id=w["userId"], product=product, rule=rule)
        if last_minor is not None:
            watch.last_seen = Money(int(last_minor), product.price.sale.currency)
        return watch

    def list_watches(self, user_id: str) -> List[Watch]:
        with self._lock:
            return [self._to_watch(w) for w in self._watches() if w["userId"] == user_id]

    def all_watches(self) -> List[Watch]:
        with self._lock:
            return [self._to_watch(w) for w in self._watches()]
