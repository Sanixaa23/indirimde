"""The fragile half of the n11 adapter: rendering the page and reading JSON-LD.

n11 serves a bot wall to plain requests, so the page is rendered in Chromium
and its schema.org JSON-LD is read: an `ItemList` on the search page, a
`Product` offer on the product page. Both go through the shared helpers and
fail closed (None) on any block, timeout, or missing blob.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote_plus

from .ld import fetch_ld_itemlist, fetch_ld_price

SEARCH_URL = "https://www.n11.com/arama?q={q}"


def fetch_search(query: str) -> Optional[List[dict]]:
    """Render an n11 search and return its JSON-LD ItemList elements, or None."""
    return fetch_ld_itemlist(SEARCH_URL.format(q=quote_plus(query)))


def fetch_price_by_url(url: str) -> Optional[dict]:
    """Live price of one n11 product as a JSON-LD offer dict, or None."""
    return fetch_ld_price(url)


def make_fetchers():
    return fetch_search, fetch_price_by_url
