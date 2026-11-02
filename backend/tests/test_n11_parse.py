import json
from pathlib import Path

from indirimde.money import Money
from indirimde.stores.n11 import N11Store, parse_product, parse_search

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "n11_search_kulaklik.json"


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_fixture_products():
    products = parse_search(load())
    assert len(products) == 3


def test_first_product_fields():
    first = parse_search(load())[0]
    assert first.store == "n11"
    assert first.store_id == "59266704"       # trailing id from the url
    assert first.key == "n11:59266704"
    assert first.brand == "Apple"
    assert "AirPods 4" in first.name


def test_sale_and_list_price():
    first = parse_search(load())[0]
    # offers.price 6395 is the sale; priceSpecification ListPrice 15000 is `was`.
    assert first.price.sale == Money(639500, "TRY")
    assert first.price.was == Money(1500000, "TRY")


def test_urls_are_n11():
    for p in parse_search(load()):
        assert p.url.startswith("https://www.n11.com/urun/")


def test_list_price_not_above_sale_leaves_was_none():
    item = {
        "@type": "Product",
        "name": "X",
        "url": "https://www.n11.com/urun/x-123",
        "offers": {
            "price": "100",
            "priceCurrency": "TRY",
            "priceSpecification": {"price": "100"},  # same as sale -> no was
        },
    }
    p = parse_product(item)
    assert p.price.sale == Money(10000, "TRY")
    assert p.price.was is None


def test_listitem_wrapper_is_unwrapped():
    element = {"@type": "ListItem", "position": 1, "item": {
        "@type": "Product", "name": "Y",
        "url": "https://www.n11.com/urun/y-999",
        "offers": {"price": "50", "priceCurrency": "TRY"}}}
    p = parse_product(element)
    assert p is not None and p.store_id == "999"


def test_missing_price_is_dropped():
    assert parse_product({"name": "n", "url": "https://www.n11.com/urun/z-1"}) is None


def test_store_without_fetcher_fails_closed():
    assert N11Store().search("kulaklik") == []
