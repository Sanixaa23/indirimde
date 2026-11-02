"""The fragile half of the Trendyol adapter: actually getting the page.

Trendyol answers a plain HTTP request with 403, so we render the page in a real
Chromium (via Playwright) and read the embedded JSON the browser does.
Everything here is best-effort and fails closed: any timeout, block, or missing
blob returns None, and the pure parser in `trendyol.py` turns that into "no
price" rather than a guess.

Search reads Trendyol's own hydrated state blob (it is richer than the page's
JSON-LD — it carries the struck-through former price). The live price of one
tracked product uses the shared JSON-LD offer fetcher, which is stable across
Trendyol's React-state changes.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from .browser import page
from .ld import fetch_ld_price

# Kept as `_page` for the adapter's own use and existing imports.
_page = page

SEARCH_URL = "https://www.trendyol.com/sr?q={q}"
_SEARCH_STATE = "window['__single-search-result__PROPS']"


def fetch_search(query: str) -> Optional[dict]:
    """Render a Trendyol search and return its embedded `data` object.

    Returns None on any failure so the caller treats the store as unreachable.
    """
    url = SEARCH_URL.format(q=quote(query))
    try:
        with page() as pg:
            pg.goto(url, wait_until="domcontentloaded")
            # The search state is injected after hydration; wait for it rather
            # than racing the parser against an empty page.
            pg.wait_for_function(
                f"() => !!({_SEARCH_STATE} && {_SEARCH_STATE}.data "
                f"&& {_SEARCH_STATE}.data.products)",
                timeout=20000,
            )
            return pg.evaluate(f"() => {_SEARCH_STATE}.data")
    except Exception:
        return None


def fetch_price_by_url(url: str) -> Optional[dict]:
    """Live price of one Trendyol product as a JSON-LD offer dict, or None."""
    return fetch_ld_price(url)


def make_fetchers():
    """Return (search_fetcher, price_fetcher) ready to inject into the store.

    The price fetcher takes a product's absolute URL; the store passes it from
    the Product it already holds.
    """
    return fetch_search, fetch_price_by_url
