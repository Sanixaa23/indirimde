"""Searching several stores at once, and routing a price read to the right one.

The app tracks products across many Turkish shops, so a search fans out to
every store and the results are merged; a price re-check for one tracked
product goes only to the store that product came from (`product.store`).

Fan-out runs the stores concurrently — each live fetch launches its own browser
and takes many seconds, so doing them in parallel keeps a multi-store search
about as fast as a single one. A store that blocks us or errors contributes
nothing and never sinks the others (each adapter already fails closed).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from ..models import Product
from ..pricing import Price
from .base import StoreAdapter


def _interleave(groups: List[List[Product]], limit: int) -> List[Product]:
    """Round-robin the per-store result lists so the merged list shows a mix
    of shops rather than all of one then all of another."""
    out: List[Product] = []
    i = 0
    while len(out) < limit:
        took = False
        for group in groups:
            if i < len(group):
                out.append(group[i])
                took = True
                if len(out) >= limit:
                    break
        if not took:
            break
        i += 1
    return out


class MultiStore:
    """Fans search out across the given stores; routes price reads by store."""

    name = "multi"

    def __init__(self, stores: Dict[str, StoreAdapter]) -> None:
        self._stores = stores

    @property
    def store_names(self) -> List[str]:
        return list(self._stores.keys())

    def search(self, query: str, limit: int = 20) -> List[Product]:
        stores = list(self._stores.values())
        if not stores:
            return []

        def one(store: StoreAdapter) -> List[Product]:
            try:
                return store.search(query, limit=limit)
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=max(1, len(stores))) as pool:
            groups = list(pool.map(one, stores))
        return _interleave(groups, limit)

    def fetch_price(self, product: Product) -> Optional[Price]:
        store = self._stores.get(product.store)
        if store is None:
            return None
        try:
            return store.fetch_price(product)
        except Exception:
            return None


def build_live_stores() -> Dict[str, StoreAdapter]:
    """Every store wired with its live (Playwright) fetchers.

    Hepsiburada is included only when INDIRIMDE_HEPSIBURADA=1, because it needs a
    headful Google Chrome and a desktop session; off by default so a plain or
    headless deployment does not spawn visible windows that will just be blocked.
    """
    import os

    from .n11 import N11Store
    from .n11_fetch import make_fetchers as n11_fetchers
    from .trendyol import TrendyolStore
    from .trendyol_fetch import make_fetchers as trendyol_fetchers

    stores: Dict[str, StoreAdapter] = {
        "trendyol": TrendyolStore(*trendyol_fetchers()),
        "n11": N11Store(*n11_fetchers()),
    }
    if os.environ.get("INDIRIMDE_HEPSIBURADA") == "1":
        from .hepsiburada import HepsiburadaStore
        from .hepsiburada_fetch import make_fetchers as hb_fetchers

        stores["hepsiburada"] = HepsiburadaStore(*hb_fetchers())
    return stores


def build_live_multistore() -> MultiStore:
    return MultiStore(build_live_stores())
