"""Shared schema.org JSON-LD helpers used by every store adapter.

Turkish shops publish their product data as JSON-LD in the page
(`<script type="application/ld+json">`): a product page carries a `Product`
with an `offers.price` (the live selling price), and a search page often
carries an `ItemList` of `Product`s. JSON-LD is a stable, buyer-facing contract
— far steadier than each site's private React/Vue state — so the adapters read
it wherever a site provides it. Everything here fails closed: a missing or
malformed blob yields None/empty, never a guessed price.
"""

from __future__ import annotations

from typing import List, Optional

from ..money import from_major
from ..pricing import Price
from .browser import page

# Returns the first Product's offer as {price, priceCurrency}, or null.
LD_PRICE_JS = r"""() => {
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (const s of scripts) {
    let data;
    try { data = JSON.parse(s.textContent); } catch (e) { continue; }
    const nodes = Array.isArray(data) ? data : [data];
    for (const node of nodes) {
      if (!node) continue;
      if (node['@type'] === 'Product' && node.offers) {
        let o = node.offers;
        if (Array.isArray(o)) o = o[0];
        if (o && o.price != null) {
          return { price: String(o.price),
                   priceCurrency: o.priceCurrency || "TRY" };
        }
      }
    }
  }
  return null;
}"""

# Returns an ItemList's itemListElement array (list of {item:{Product}}), or null.
LD_ITEMLIST_JS = r"""() => {
  const scripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (const s of scripts) {
    let data;
    try { data = JSON.parse(s.textContent); } catch (e) { continue; }
    const nodes = Array.isArray(data) ? data : [data];
    for (const node of nodes) {
      if (node && node['@type'] === 'ItemList' && node.itemListElement) {
        return node.itemListElement;
      }
    }
  }
  return null;
}"""


def parse_ld_offer(offer: dict) -> Optional[Price]:
    """Turn a schema.org offer ({"price":"987.00","priceCurrency":"TRY"}) into a
    Price (sale only), or None. The amount is a plain dot-decimal string parsed
    exactly via `from_major`, never the Turkish text parser."""
    if not isinstance(offer, dict):
        return None
    amount = offer.get("price")
    if amount is None:
        return None
    currency = offer.get("priceCurrency") or offer.get("currency") or "TRY"
    try:
        return Price(sale=from_major(str(amount), currency))
    except (ValueError, TypeError):
        return None


def fetch_ld_price(url: str, timeout_ms: int = 20000) -> Optional[dict]:
    """Open a product page and return its live JSON-LD offer dict, or None.

    Shared by every adapter whose product pages carry schema.org Product
    markup. Fails closed on timeout, block, or a page with no offer.
    """
    try:
        with page() as pg:
            pg.goto(url, wait_until="domcontentloaded")
            pg.wait_for_function(f"() => !!({LD_PRICE_JS})()", timeout=timeout_ms)
            return pg.evaluate(LD_PRICE_JS)
    except Exception:
        return None


def fetch_ld_itemlist(url: str, timeout_ms: int = 20000) -> Optional[List[dict]]:
    """Open a search page and return its JSON-LD ItemList elements, or None."""
    try:
        with page() as pg:
            pg.goto(url, wait_until="domcontentloaded")
            pg.wait_for_function(f"() => !!({LD_ITEMLIST_JS})()", timeout=timeout_ms)
            return pg.evaluate(LD_ITEMLIST_JS)
    except Exception:
        return None
