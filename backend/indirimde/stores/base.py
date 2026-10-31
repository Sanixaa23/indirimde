"""The contract every store adapter honours, and the registry of them.

A store must do two things: turn a search query into a list of products, and
read the current price of one product we already know. Both may fail — the
store can block us, rate-limit us, or change its page — and the contract says
how: `search` returns an empty list, `fetch_price` returns None. Neither ever
raises for an expected outside-world failure and neither ever invents a price.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from ..models import Product
from ..pricing import Price


@runtime_checkable
class StoreAdapter(Protocol):
    """What the scheduler and API expect from any store."""

    # Short lowercase id, e.g. "trendyol". Used as the first half of a key.
    name: str

    def search(self, query: str, limit: int = 20) -> List[Product]:
        """Products matching `query`. Empty list on any failure."""
        ...

    def fetch_price(self, product: Product) -> Optional[Price]:
        """The listing's price now, or None if it could not be read."""
        ...


STORES: Dict[str, StoreAdapter] = {}


def register(adapter: StoreAdapter) -> StoreAdapter:
    """Add an adapter to the registry, keyed by its name."""
    STORES[adapter.name] = adapter
    return adapter


def get_store(name: str) -> StoreAdapter:
    try:
        return STORES[name]
    except KeyError:
        raise ValueError(f"unknown store: {name!r}") from None
