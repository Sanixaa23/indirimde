"""Turning the core's records into JSON the API and the store can round-trip.

Money is always carried as integer minor units plus a currency, never a float,
so a price survives serialization byte-for-byte. A stored product keeps enough
to re-fetch its live price (the url) and to render a notification (name, store,
key), plus the last price we saw for display.
"""

from __future__ import annotations

from typing import Optional

from ..models import Product
from ..money import _SYMBOL_TO_CODE, Money
from ..pricing import Price


def normalize_currency(value: Optional[str]) -> str:
    """Accept either an ISO code (TRY) or a store symbol (TL, ₺) and return
    the ISO code Money stores. Unknown values default to TRY."""
    if not value:
        return "TRY"
    return _SYMBOL_TO_CODE.get(value, value if value in ("TRY", "USD", "EUR") else "TRY")


def money_to_minor(m: Optional[Money]) -> Optional[int]:
    return None if m is None else m.minor


def product_to_dict(p: Product) -> dict:
    return {
        "store": p.store,
        "storeId": p.store_id,
        "name": p.name,
        "url": p.url,
        "brand": p.brand,
        "image": p.image,
        "saleMinor": p.price.sale.minor,
        "wasMinor": money_to_minor(p.price.was),
        "currency": p.price.sale.currency,
        "rating": p.rating,
        "ratingCount": p.rating_count,
    }


def product_from_dict(d: dict) -> Product:
    currency = normalize_currency(d.get("currency"))
    was_minor = d.get("wasMinor")
    price = Price(
        sale=Money(int(d["saleMinor"]), currency),
        was=Money(int(was_minor), currency) if was_minor is not None else None,
    )
    return Product(
        store=d["store"],
        store_id=str(d["storeId"]),
        name=d["name"],
        url=d["url"],
        price=price,
        brand=d.get("brand", ""),
        image=d.get("image", ""),
        rating=d.get("rating"),
        rating_count=int(d.get("ratingCount", 0) or 0),
    )
