"""Trendyol adapter.

Trendyol serves its search results as a JSON blob embedded in the page
(`window["__single-search-result__PROPS"].data`), not through a public API we
can call from a server — a plain request is answered with 403. So the fragile
half renders the page in a real browser and hands us that blob; the pure half
below turns the blob into `Product`s and is what the tests exercise, against a
response captured from the live site.

Price fields on a Trendyol listing:
  discountedPriceText  what the buyer pays today      -> Price.sale
  oldText (when old>0) the struck-through former price -> Price.was
`current`/`originalPrice` are list/sticker figures that do not match what is
charged, so we ignore them.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from ..models import Product
from ..money import parse_tr
from ..pricing import Price
from .base import register
from .ld import parse_ld_offer

BASE = "https://www.trendyol.com"

# A function that, given a search query, returns Trendyol's embedded search
# `data` object (or None if it could not be fetched). Injected so the pure
# parser can be tested without a browser, and so the live renderer can be
# swapped without touching this file. The price fetcher takes a product's
# absolute URL — the product page is where a single listing's live price lives.
SearchFetcher = Callable[[str], Optional[dict]]
PriceFetcher = Callable[[str], Optional[dict]]


def _abs_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return BASE + path


def parse_price(price: dict) -> Optional[Price]:
    """Turn a Trendyol `price` object into a Price, or None if unreadable.

    Accepts two shapes: the search-results price object (with
    `discountedPriceText` and an optional struck-through `oldText`), and the
    product page's JSON-LD offer (a plain `price` decimal). Returns None rather
    than raising so one malformed listing cannot blow up a whole page of
    results, and so a missing price is never read as free.
    """
    if not isinstance(price, dict):
        return None
    # JSON-LD offer shape: a bare decimal `price`, no discountedPriceText.
    if "discountedPriceText" not in price and price.get("price") is not None:
        return parse_ld_offer(price)
    sale_text = price.get("discountedPriceText")
    symbol = price.get("currencySymbol") or price.get("currency") or "TL"
    if not sale_text:
        return None
    try:
        sale = parse_tr(str(sale_text), symbol)
    except (ValueError, TypeError):
        return None

    was = None
    old = price.get("old")
    old_text = price.get("oldText")
    if old and str(old) not in ("0", "0.0") and old_text:
        try:
            was = parse_tr(str(old_text), symbol)
        except (ValueError, TypeError):
            was = None

    return Price(sale=sale, was=was)


def parse_product(raw: dict) -> Optional[Product]:
    """Turn one raw Trendyol product into a Product, or None if unusable."""
    store_id = raw.get("id")
    name = raw.get("name")
    url = raw.get("url")
    if store_id is None or not name or not url:
        return None
    price = parse_price(raw.get("price", {}))
    if price is None:
        return None

    rating = raw.get("ratingScore") or {}
    return Product(
        store="trendyol",
        store_id=str(store_id),
        name=str(name),
        url=_abs_url(str(url)),
        price=price,
        brand=str(raw.get("brand", "")),
        image=str(raw.get("image", "")),
        rating=rating.get("averageRating"),
        rating_count=int(rating.get("totalCount", 0) or 0),
    )


def parse_search(payload: dict) -> List[Product]:
    """Turn Trendyol's embedded search data into a list of products.

    Accepts either the `data` object directly or the whole PROPS object that
    wraps it. Listings whose price cannot be read are dropped, not guessed.
    """
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", payload)
    raws = data.get("products") or []
    out = []
    for raw in raws:
        product = parse_product(raw)
        if product is not None:
            out.append(product)
    return out


class TrendyolStore:
    """The adapter the registry holds. I/O goes through injected fetchers so
    the store stays testable and fails closed when none is wired yet."""

    name = "trendyol"

    def __init__(
        self,
        search_fetcher: Optional[SearchFetcher] = None,
        price_fetcher: Optional[PriceFetcher] = None,
    ) -> None:
        self._search_fetcher = search_fetcher
        self._price_fetcher = price_fetcher

    def search(self, query: str, limit: int = 20) -> List[Product]:
        if self._search_fetcher is None:
            return []
        data = self._search_fetcher(query)
        if data is None:
            return []
        return parse_search(data)[:limit]

    def fetch_price(self, product: Product) -> Optional[Price]:
        if self._price_fetcher is None:
            return None
        price_dict = self._price_fetcher(product.url)
        if price_dict is None:
            return None
        return parse_price(price_dict)


# Registered with no fetchers yet: search/fetch_price fail closed (empty/None)
# until the live browser renderer is wired in. Parsing is available regardless.
register(TrendyolStore())
