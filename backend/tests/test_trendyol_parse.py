import json
from pathlib import Path

from indirimde.money import Money
from indirimde.stores.trendyol import (
    TrendyolStore,
    parse_ld_offer,
    parse_price,
    parse_search,
)

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "trendyol_search_kulaklik.json"


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_all_three_products():
    products = parse_search(load())
    assert len(products) == 3


def test_tracks_discounted_price_not_sticker():
    # First listing: discountedPriceText 884,45 is what the buyer pays, even
    # though `current` says 931.
    first = parse_search(load())[0]
    assert first.price.sale == Money(88445, "TRY")
    assert first.price.was is None


def test_reads_struck_through_former_price():
    # Xiaomi listing: old 739 -> now 719.
    xiaomi = [p for p in parse_search(load()) if p.store_id == "855229295"][0]
    assert xiaomi.price.sale == Money(71900, "TRY")
    assert xiaomi.price.was == Money(73900, "TRY")


def test_urls_are_absolute():
    for p in parse_search(load()):
        assert p.url.startswith("https://www.trendyol.com/")


def test_key_combines_store_and_id():
    first = parse_search(load())[0]
    assert first.key == "trendyol:819066262"


def test_unreadable_price_is_dropped_not_guessed():
    assert parse_price({"discountedPriceText": ""}) is None
    assert parse_price({}) is None


def test_store_without_fetcher_fails_closed():
    store = TrendyolStore()
    assert store.search("kulaklik") == []


def test_ld_offer_price_parsed_exactly():
    # The product page's JSON-LD offer: a plain dot-decimal, not Turkish text.
    price = parse_ld_offer({"price": "987.00", "priceCurrency": "TRY"})
    assert price is not None
    assert price.sale == Money(98700, "TRY")
    assert price.was is None  # LD carries no struck-through former price


def test_ld_offer_default_currency_is_try():
    price = parse_ld_offer({"price": "1.5"})  # dot-decimal -> 1,50 TL
    assert price.sale == Money(150, "TRY")


def test_parse_price_routes_ld_shape_through_offer_parser():
    # fetch_price_by_url returns this shape; parse_price must accept it.
    price = parse_price({"price": "649.90", "priceCurrency": "TRY"})
    assert price is not None and price.sale == Money(64990, "TRY")


def test_ld_offer_missing_price_is_none():
    assert parse_ld_offer({"priceCurrency": "TRY"}) is None
    assert parse_ld_offer({}) is None
