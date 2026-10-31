"""End-to-end over the deterministic path: a scripted price series drives a
watch and we assert exactly when a notification fires. No network, no real FCM
— the store and the transport are fakes — so the result is reproducible."""

from typing import List, Optional

from indirimde.money import Money
from indirimde.models import Product, Watch
from indirimde.notify import RecordingNotifier
from indirimde.pricing import Price
from indirimde.watcher import poll_once


class ScriptedStore:
    """A store that returns a pre-set sequence of prices; None means it was
    unreachable on that poll."""

    name = "fake"

    def __init__(self, series: List[Optional[Price]]):
        self._series = list(series)
        self._i = 0

    def search(self, query, limit=20):
        return []

    def fetch_price(self, product):
        price = self._series[self._i]
        self._i += 1
        return price


def tl(minor):
    return Money(minor, "TRY")


def make_watch():
    product = Product(
        store="fake",
        store_id="1",
        name="Redmi Buds 6 Play Kulaklık",
        url="https://example/p/1",
        price=Price(sale=tl(80000)),
    )
    return Watch(user_id="u1", product=product)


def test_notifies_once_on_the_drop_and_survives_an_outage():
    series = [
        Price(sale=tl(80000)),  # baseline 800,00
        Price(sale=tl(80000)),  # unchanged
        Price(sale=tl(72000)),  # drop to 720,00 -> fire
        None,                   # store down
        Price(sale=tl(72000)),  # back, unchanged
    ]
    store = ScriptedStore(series)
    notifier = RecordingNotifier()
    watch = make_watch()

    results = [poll_once(watch, store, notifier) for _ in series]

    assert results[0].baseline_set is True
    assert results[1].drop is None
    assert results[2].drop is not None
    assert results[3].reachable is False
    assert results[4].drop is None

    # Exactly one push, with the drop rendered in Turkish.
    assert len(notifier.sent) == 1
    _, msg = notifier.sent[0]
    assert msg.title == "Redmi Buds 6 Play Kulaklık indirimde"
    assert msg.body == "800,00 TL → 720,00 TL  (%10.0 indirim)"
    assert msg.data["productKey"] == "fake:1"

    # The outage did not move the baseline off the real last price.
    assert watch.last_seen == tl(72000)


def test_first_poll_unreachable_sets_no_baseline():
    store = ScriptedStore([None])
    watch = make_watch()
    result = poll_once(watch, store, RecordingNotifier())
    assert result.reachable is False
    assert result.baseline_set is False
    assert watch.last_seen is None
