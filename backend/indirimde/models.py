"""The plain records passed between the parser, the store, the API and the app.

These are data, not behaviour: a `Product` is one search hit, a `Watch` is a
user asking to be told when a product drops, and a `PricePoint` is one reading
stored over time. Keeping them free of logic lets the pure core and the store
adapters share them without either depending on the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .money import Money
from .pricing import DropRule, Price


@dataclass(frozen=True)
class Product:
    """One result from a store search.

    `store` plus `store_id` identifies the listing uniquely; `url` is the
    absolute page a human (or our live fetcher) can open.
    """

    store: str
    store_id: str
    name: str
    url: str
    price: Price
    brand: str = ""
    image: str = ""
    rating: Optional[float] = None
    rating_count: int = 0

    @property
    def key(self) -> str:
        """Stable identity used as the watch key and dedupe key."""
        return f"{self.store}:{self.store_id}"


@dataclass
class Watch:
    """A user's standing request to track one product.

    `last_seen` is the price the drop decision compares against; it is updated
    after every successful reading. `rule` is this watch's own threshold so one
    user can ask for 5%-off alerts while another wants any fall.
    """

    user_id: str
    product: Product
    rule: DropRule = field(default_factory=DropRule)
    last_seen: Optional[Money] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PricePoint:
    """One price reading at a point in time, for the history graph."""

    at: datetime
    price: Money
