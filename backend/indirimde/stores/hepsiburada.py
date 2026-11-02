"""Hepsiburada adapter.

Hepsiburada is the hostile one: it serves a "Güvenlik" bot wall to a plain or
headless request and exposes no JSON-LD or state blob on its search page. Only
a real, headful Google Chrome gets through, and the data must be read from the
rendered DOM. So this adapter's fetcher normalises each product card into a
small dict `{id, url, title, finalPriceText, oldPriceText, image}` and the pure
parser below turns those into `Product`s — tested against a captured fixture
(`fixtures/hepsiburada_search_kulaklik.json`).

Price text comes straight from the card ("579 TL", "1.174,85 TL") and is parsed
by the Turkish text parser. `oldPriceText`, when the card shows a struck price,
becomes `was`; otherwise `was` is None (display only — the drop decision never
needs it).
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import Product
from ..money import parse_tr
from ..pricing import Price
from .base import register
from .ld import parse_ld_offer

_ID_RE = re.compile(r"-p-([A-Z0-9]+)", re.IGNORECASE)


def _store_id(url: str, given) -> str:
    if given:
        return str(given)
    m = _ID_RE.search(url or "")
    return m.group(1) if m else ""


def parse_card(card: dict) -> Optional[Product]:
    """Turn one normalised Hepsiburada card dict into a Product, or None."""
    if not isinstance(card, dict):
        return None
    name = card.get("title")
    url = card.get("url")
    final_text = card.get("finalPriceText")
    if not name or not url or not final_text:
        return None
    try:
        sale = parse_tr(str(final_text), "TL")
    except (ValueError, TypeError):
        return None
    was = None
    old_text = card.get("oldPriceText")
    if old_text:
        try:
            candidate = parse_tr(str(old_text), "TL")
            if candidate > sale:
                was = candidate
        except (ValueError, TypeError):
            was = None
    store_id = _store_id(str(url), card.get("id"))
    if not store_id:
        return None
    return Product(
        store="hepsiburada",
        store_id=store_id,
        name=str(name),
        url=str(url),
        price=Price(sale=sale, was=was),
        image=str(card.get("image", "")),
    )


def parse_search(cards) -> List[Product]:
    """Turn the fetcher's list of card dicts into products; drop unreadable."""
    if not isinstance(cards, list):
        return []
    out = []
    for card in cards:
        product = parse_card(card)
        if product is not None:
            out.append(product)
    return out


class HepsiburadaStore:
    """The Hepsiburada adapter; I/O through injected fetchers, fails closed."""

    name = "hepsiburada"

    def __init__(self, search_fetcher=None, price_fetcher=None) -> None:
        self._search_fetcher = search_fetcher
        self._price_fetcher = price_fetcher

    def search(self, query: str, limit: int = 20) -> List[Product]:
        if self._search_fetcher is None:
            return []
        cards = self._search_fetcher(query)
        if cards is None:
            return []
        return parse_search(cards)[:limit]

    def fetch_price(self, product: Product) -> Optional[Price]:
        if self._price_fetcher is None:
            return None
        result = self._price_fetcher(product.url)
        if not result:
            return None
        # JSON-LD offer (dot-decimal) when the PDP has it, else DOM price text.
        if result.get("price") is not None:
            return parse_ld_offer(result)
        text = result.get("priceText")
        if not text:
            return None
        try:
            return Price(sale=parse_tr(str(text), "TL"))
        except (ValueError, TypeError):
            return None


register(HepsiburadaStore())
