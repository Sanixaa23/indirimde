import json
from pathlib import Path

from indirimde.money import Money
from indirimde.stores.hepsiburada import HepsiburadaStore, parse_card, parse_search

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "hepsiburada_search_kulaklik.json"
)


def load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parses_fixture_cards():
    assert len(parse_search(load())) == 3


def test_first_card_fields():
    first = parse_search(load())[0]
    assert first.store == "hepsiburada"
    assert first.store_id == "HBCV000072PXK3"
    assert first.key == "hepsiburada:HBCV000072PXK3"
    assert "Redmi Buds 6 Play" in first.name
    # "579 TL" -> 579,00
    assert first.price.sale == Money(57900, "TRY")
    assert first.price.was is None


def test_grouped_and_bare_price_texts():
    products = parse_search(load())
    assert products[1].price.sale == Money(117485, "TRY")   # "1.174,85 TL"
    assert products[2].price.sale == Money(249900, "TRY")   # "2.499 TL"


def test_old_price_above_sale_becomes_was():
    card = {
        "id": "HBCV00000X",
        "url": "https://www.hepsiburada.com/x-p-HBCV00000X",
        "title": "X",
        "finalPriceText": "579 TL",
        "oldPriceText": "699 TL",
    }
    p = parse_card(card)
    assert p.price.sale == Money(57900, "TRY")
    assert p.price.was == Money(69900, "TRY")


def test_old_price_not_above_sale_ignored():
    card = {
        "id": "HBCV00000Y",
        "url": "https://www.hepsiburada.com/y-p-HBCV00000Y",
        "title": "Y", "finalPriceText": "579 TL", "oldPriceText": "579 TL",
    }
    assert parse_card(card).price.was is None


def test_id_falls_back_to_url_code():
    card = {
        "url": "https://www.hepsiburada.com/z-p-HBCV00000Z",
        "title": "Z", "finalPriceText": "100 TL",
    }
    assert parse_card(card).store_id == "HBCV00000Z"


def test_unreadable_price_is_dropped():
    assert parse_card({"url": "x-p-HBCV1", "title": "t", "finalPriceText": "—"}) is None
    assert parse_card({"url": "x-p-HBCV1", "title": "t"}) is None


def test_price_fetcher_parses_pricetext():
    store = HepsiburadaStore(price_fetcher=lambda url: {"priceText": "1.299,90 TL"})
    from indirimde.models import Product
    from indirimde.pricing import Price
    product = Product(store="hepsiburada", store_id="HBCV1", name="n",
                      url="https://www.hepsiburada.com/n-p-HBCV1",
                      price=Price(sale=Money(100, "TRY")))
    assert store.fetch_price(product).sale == Money(129990, "TRY")


def test_price_fetcher_parses_ld_offer():
    store = HepsiburadaStore(
        price_fetcher=lambda url: {"price": "579.00", "priceCurrency": "TRY"}
    )
    from indirimde.models import Product
    from indirimde.pricing import Price
    product = Product(store="hepsiburada", store_id="HBCV1", name="n",
                      url="https://www.hepsiburada.com/n-p-HBCV1",
                      price=Price(sale=Money(100, "TRY")))
    assert store.fetch_price(product).sale == Money(57900, "TRY")


def test_store_without_fetcher_fails_closed():
    assert HepsiburadaStore().search("kulaklik") == []
    assert HepsiburadaStore().fetch_price(None) is None
