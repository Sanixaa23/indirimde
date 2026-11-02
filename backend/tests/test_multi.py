"""MultiStore: fan-out search merges every shop; price reads route by store."""

from __future__ import annotations

from indirimde.models import Product
from indirimde.money import Money
from indirimde.pricing import Price
from indirimde.stores.multi import MultiStore


def product(store, pid, sale):
    return Product(
        store=store, store_id=pid, name=f"{store}-{pid}",
        url=f"https://{store}.example/p/{pid}",
        price=Price(sale=Money(sale, "TRY")),
    )


class FakeStore:
    def __init__(self, name, products, price=None, boom=False):
        self.name = name
        self._products = products
        self.price = price
        self._boom = boom

    def search(self, query, limit=20):
        if self._boom:
            raise RuntimeError("blocked")
        return self._products[:limit]

    def fetch_price(self, p):
        return self.price


def test_search_merges_and_interleaves():
    ty = FakeStore("trendyol", [product("trendyol", "1", 100), product("trendyol", "2", 200)])
    n11 = FakeStore("n11", [product("n11", "9", 900)])
    multi = MultiStore({"trendyol": ty, "n11": n11})
    results = multi.search("x", limit=10)
    keys = [p.key for p in results]
    # one from each first (round-robin), then the rest
    assert keys[0] == "trendyol:1"
    assert keys[1] == "n11:9"
    assert "trendyol:2" in keys
    assert len(results) == 3


def test_one_store_blocking_does_not_sink_others():
    good = FakeStore("n11", [product("n11", "9", 900)])
    bad = FakeStore("trendyol", [], boom=True)
    multi = MultiStore({"trendyol": bad, "n11": good})
    results = multi.search("x", limit=10)
    assert [p.key for p in results] == ["n11:9"]


def test_fetch_price_routes_to_the_products_store():
    ty = FakeStore("trendyol", [], price=Price(sale=Money(111, "TRY")))
    n11 = FakeStore("n11", [], price=Price(sale=Money(999, "TRY")))
    multi = MultiStore({"trendyol": ty, "n11": n11})
    assert multi.fetch_price(product("n11", "9", 0)).sale == Money(999, "TRY")
    assert multi.fetch_price(product("trendyol", "1", 0)).sale == Money(111, "TRY")


def test_fetch_price_unknown_store_is_none():
    multi = MultiStore({"n11": FakeStore("n11", [])})
    assert multi.fetch_price(product("hepsiburada", "1", 0)) is None


def test_limit_is_respected_across_stores():
    ty = FakeStore("trendyol", [product("trendyol", str(i), i) for i in range(10)])
    n11 = FakeStore("n11", [product("n11", str(i), i) for i in range(10)])
    multi = MultiStore({"trendyol": ty, "n11": n11})
    assert len(multi.search("x", limit=5)) == 5


def test_store_names():
    multi = MultiStore({"trendyol": FakeStore("trendyol", []), "n11": FakeStore("n11", [])})
    assert multi.store_names == ["trendyol", "n11"]
