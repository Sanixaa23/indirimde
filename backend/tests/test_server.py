"""The HTTP surface and the poll loop, wired to a fake store (no network).

These prove the thin server does not change any decision: search passes the
store's products through, a watch stores the baseline the user saw, and a later
lower price produces exactly one push — while an unreachable store produces
none and leaves the baseline alone.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from indirimde.models import Product
from indirimde.money import Money
from indirimde.pricing import Price
from indirimde.server.app import create_app
from indirimde.server.repo import Repo


class FakeStore:
    name = "trendyol"

    def __init__(self, products, price=None):
        self._products = products
        self.price = price  # what fetch_price returns; None = unreachable

    def search(self, query, limit=20):
        return self._products[:limit]

    def fetch_price(self, product):
        return self.price


def make_product(sale_minor, was_minor=None):
    return Product(
        store="trendyol",
        store_id="123",
        name="Redmi Buds 6 Play",
        url="https://www.trendyol.com/p/123",
        price=Price(
            sale=Money(sale_minor, "TRY"),
            was=Money(was_minor, "TRY") if was_minor else None,
        ),
        brand="Xiaomi",
    )


@pytest.fixture
def ctx(tmp_path):
    repo = Repo(str(tmp_path / "data.json"))
    sent = []  # (token, PushMessage)
    store = FakeStore([make_product(69900, 71900)])

    def transport(token, message):
        sent.append((token, message))

    app = create_app(
        store=store, repo=repo, transport=transport, start_scheduler=False
    )
    client = TestClient(app)
    return client, store, repo, sent


def test_health(ctx):
    client = ctx[0]
    assert client.get("/health").json()["ok"] is True


def test_search_passes_store_products_through(ctx):
    client = ctx[0]
    r = client.post("/search", json={"query": "kulaklik"})
    products = r.json()["products"]
    assert len(products) == 1
    assert products[0]["key"] == "trendyol:123"
    assert products[0]["saleText"] == "699,00 TL"
    assert products[0]["wasText"] == "719,00 TL"


def _add_watch(client, sale_minor, was_minor=71900):
    client.post("/devices", json={"userId": "u1", "token": "tok-1"})
    product = {
        "store": "trendyol",
        "storeId": "123",
        "name": "Redmi Buds 6 Play",
        "url": "https://www.trendyol.com/p/123",
        "saleMinor": sale_minor,
        "wasMinor": was_minor,
        "currency": "TL",
    }
    return client.post("/watches", json={"userId": "u1", "product": product})


def test_add_and_list_watch(ctx):
    client = ctx[0]
    r = _add_watch(client, 69900)
    assert r.json()["key"] == "trendyol:123"
    watches = client.get("/watches", params={"userId": "u1"}).json()["watches"]
    assert len(watches) == 1
    assert watches[0]["lastSeenMinor"] == 69900  # baseline = price user saw


def test_poll_notifies_once_on_a_real_drop(ctx):
    client, store, repo, sent = ctx
    _add_watch(client, 69900)            # baseline 699,00
    store.price = Price(sale=Money(64900, "TRY"))  # now 649,00 -> a drop
    summary = client.post("/poll").json()
    assert summary["drops"] == 1
    assert summary["reachable"] == 1
    assert len(sent) == 1
    token, message = sent[0]
    assert token == "tok-1"
    assert "649,00 TL" in message.body
    # baseline advanced to the new price
    watches = client.get("/watches", params={"userId": "u1"}).json()["watches"]
    assert watches[0]["lastSeenMinor"] == 64900


def test_poll_no_notification_when_price_holds(ctx):
    client, store, repo, sent = ctx
    _add_watch(client, 69900)
    store.price = Price(sale=Money(69900, "TRY"))  # unchanged
    summary = client.post("/poll").json()
    assert summary["drops"] == 0
    assert sent == []


def test_unreachable_store_keeps_baseline_and_is_silent(ctx):
    client, store, repo, sent = ctx
    _add_watch(client, 69900)
    store.price = None  # store down
    summary = client.post("/poll").json()
    assert summary["unreachable"] == 1
    assert summary["drops"] == 0
    assert sent == []
    watches = client.get("/watches", params={"userId": "u1"}).json()["watches"]
    assert watches[0]["lastSeenMinor"] == 69900  # untouched


def test_small_wiggle_below_threshold_does_not_notify(ctx):
    client, store, repo, sent = ctx
    _add_watch(client, 69900)
    store.price = Price(sale=Money(69850, "TRY"))  # 0,50 TL fall < 1 TL rule
    summary = client.post("/poll").json()
    assert summary["drops"] == 0
    assert sent == []


def test_remove_watch(ctx):
    client = ctx[0]
    _add_watch(client, 69900)
    r = client.request("DELETE", "/watches", json={"userId": "u1", "key": "trendyol:123"})
    assert r.json()["ok"] is True
    watches = client.get("/watches", params={"userId": "u1"}).json()["watches"]
    assert watches == []


def _add_pct_watch(client, min_pct):
    client.post("/devices", json={"userId": "u1", "token": "tok-1"})
    product = {
        "store": "trendyol", "storeId": "123", "name": "X",
        "url": "https://www.trendyol.com/p/123", "saleMinor": 100000, "currency": "TL",
    }
    client.post("/watches", json={"userId": "u1", "product": product, "minPct": min_pct})


def test_custom_pct_rule_blocks_small_fall(ctx):
    # 10% rule, a 5% fall from the 100000 baseline must not fire.
    client, store, repo, sent = ctx
    _add_pct_watch(client, "10")
    store.price = Price(sale=Money(95000, "TRY"))  # 5% off baseline
    assert client.post("/poll").json()["drops"] == 0
    assert sent == []


def test_custom_pct_rule_fires_on_big_fall(ctx):
    # 10% rule, an 11% fall from the 100000 baseline fires in one cycle.
    client, store, repo, sent = ctx
    _add_pct_watch(client, "10")
    store.price = Price(sale=Money(89000, "TRY"))  # 11% off baseline
    assert client.post("/poll").json()["drops"] == 1
    assert len(sent) == 1
