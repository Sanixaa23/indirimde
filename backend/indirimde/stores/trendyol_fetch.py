"""The fragile half of the Trendyol adapter: actually getting the page.

Trendyol answers a plain HTTP request with 403, so we render the page in a real
Chromium (via Playwright) and read the same embedded JSON the browser does.
Everything here is best-effort and fails closed: any timeout, block, or missing
blob returns None, and the pure parser in `trendyol.py` turns that into "no
price" rather than a guess.

Each call launches and closes its own browser. That is slower than pooling but
keeps the fetcher stateless and safe to call from FastAPI's thread pool, where
several polls may run at once. If the bundled Chromium gets challenged by the
bot wall, set INDIRIMDE_BROWSER_CHANNEL=chrome to drive the installed Google
Chrome instead, which is harder to tell apart from a human's browser.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional
from urllib.parse import quote

# Playwright is imported lazily so the pure parser and the test suite do not
# need it installed; only live fetching does.
SEARCH_URL = "https://www.trendyol.com/sr?q={q}"

_SEARCH_STATE = "window['__single-search-result__PROPS']"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@contextmanager
def _page(timeout_ms: int = 25000) -> Iterator["object"]:
    """Open a page in a fresh Chromium, yield it, always clean up."""
    from playwright.sync_api import sync_playwright

    channel = os.environ.get("INDIRIMDE_BROWSER_CHANNEL") or None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel=channel)
        try:
            context = browser.new_context(
                user_agent=_USER_AGENT,
                locale="tr-TR",
                viewport={"width": 1366, "height": 900},
            )
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            yield page
        finally:
            browser.close()


def fetch_search(query: str) -> Optional[dict]:
    """Render a Trendyol search and return its embedded `data` object.

    Returns None on any failure so the caller treats the store as unreachable.
    """
    url = SEARCH_URL.format(q=quote(query))
    try:
        with _page() as page:
            page.goto(url, wait_until="domcontentloaded")
            # The search state is injected after hydration; wait for it rather
            # than racing the parser against an empty page.
            page.wait_for_function(
                f"() => !!({_SEARCH_STATE} && {_SEARCH_STATE}.data "
                f"&& {_SEARCH_STATE}.data.products)",
                timeout=20000,
            )
            return page.evaluate(f"() => {_SEARCH_STATE}.data")
    except Exception:
        return None


# The live price a buyer pays is published on the product page as JSON-LD
# (schema.org Product -> offers.price), which Trendyol keeps current and
# accurate. We read that rather than the page's private React state, which has
# changed shape over time (it is now split across many `__envoy_*__PROPS`
# blobs and no longer exposes a single product.price). JSON-LD is the stable
# contract: `price` is the current selling price, `priceCurrency` its ISO code.
_LD_PRICE_JS = r"""() => {
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (const s of scripts) {
    let data;
    try { data = JSON.parse(s.textContent); } catch (e) { continue; }
    const nodes = Array.isArray(data) ? data : [data];
    for (const node of nodes) {
      if (!node) continue;
      let offer = node.offers;
      if (Array.isArray(offer)) offer = offer[0];
      if (offer && offer.price != null) {
        return { price: String(offer.price),
                 priceCurrency: offer.priceCurrency || "TRY" };
      }
    }
  }
  return null;
}"""


def fetch_price_by_url(url: str) -> Optional[dict]:
    """Open a product page and return its live price as a JSON-LD offer dict
    ({"price": "987.00", "priceCurrency": "TRY"}), or None if unreadable.

    Fails closed: a timeout, a block, or a page with no JSON-LD offer returns
    None, which the pure parser turns into "no price" rather than a guess.
    """
    try:
        with _page() as page:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function(f"() => !!({_LD_PRICE_JS})()", timeout=20000)
            return page.evaluate(_LD_PRICE_JS)
    except Exception:
        return None


def make_fetchers():
    """Return (search_fetcher, price_fetcher) ready to inject into the store.

    The price fetcher takes a product's absolute URL; the store passes it from
    the Product it already holds.
    """
    return fetch_search, fetch_price_by_url
