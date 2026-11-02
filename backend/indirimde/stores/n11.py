"""n11 adapter.

n11 publishes its search results as a schema.org JSON-LD `ItemList` embedded in
the page, and each product page as a JSON-LD `Product`. Both are read through
the shared helpers in `ld.py`. The pure parser below turns an ItemList element
into a `Product`; it is what the tests exercise, against a response captured
from the live site (`fixtures/n11_search_kulaklik.json`).

Price fields on an n11 offer:
  offers.price                              what the buyer pays  -> Price.sale
  offers.priceSpecification.price (ListPrice) the list price     -> Price.was
`was` is kept only when the list price is genuinely above the sale price, so an
undiscounted listing never shows a fake struck-through figure.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import Product
from ..money import from_major
from ..pricing import Price
from .base import register
from .ld import parse_ld_offer

# The product id is the trailing number of an n11 product URL, e.g.
# .../apple-airpods-4-...-59266704 -> 59266704
_ID_RE = re.compile(r"-(\d+)(?:[/?#]|$)")


def _first(value) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return "" if value is None else str(value)


def _store_id(url: str, sku) -> str:
    m = _ID_RE.search(url or "")
    if m:
        return m.group(1)
    return str(sku) if sku else ""


def parse_offer_with_was(offers: dict) -> Optional[Price]:
    """Sale from offers.price, plus the ListPrice as `was` when it is higher."""
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return None
    base = parse_ld_offer(offers)  # sale only
    if base is None:
        return None
    spec = offers.get("priceSpecification") or {}
    list_price = spec.get("price")
    if list_price is None:
        return base
    currency = offers.get("priceCurrency") or "TRY"
    try:
        was = from_major(str(list_price), currency)
    except (ValueError, TypeError):
        return base
    if was > base.sale:
        return Price(sale=base.sale, was=was)
    return base


def parse_product(item: dict) -> Optional[Product]:
    """Turn one JSON-LD Product (an ItemList element's `item`) into a Product."""
    if not isinstance(item, dict):
        return None
    # An ItemList element wraps the product under `item`; accept either shape.
    if item.get("@type") == "ListItem" and isinstance(item.get("item"), dict):
        item = item["item"]
    name = item.get("name")
    url = item.get("url")
    if not name or not url:
        return None
    price = parse_offer_with_was(item.get("offers") or {})
    if price is None:
        return None
    brand = item.get("brand") or {}
    brand_name = brand.get("name", "") if isinstance(brand, dict) else str(brand)
    store_id = _store_id(str(url), item.get("sku"))
    if not store_id:
        return None
    return Product(
        store="n11",
        store_id=store_id,
        name=str(name),
        url=str(url),
        price=price,
        brand=str(brand_name),
        image=_first(item.get("image")),
    )


def parse_search(itemlist) -> List[Product]:
    """Turn an n11 JSON-LD ItemList into a list of products.

    Accepts the `itemListElement` array (list of ListItem) directly. Listings
    whose price cannot be read are dropped, not guessed.
    """
    if not isinstance(itemlist, list):
        return []
    out = []
    for element in itemlist:
        product = parse_product(element)
        if product is not None:
            out.append(product)
    return out


class N11Store:
    """The n11 adapter; I/O goes through injected fetchers so the parser stays
    testable and the store fails closed when none is wired."""

    name = "n11"

    def __init__(self, search_fetcher=None, price_fetcher=None) -> None:
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
        offer = self._price_fetcher(product.url)
        if offer is None:
            return None
        return parse_ld_offer(offer)


register(N11Store())
