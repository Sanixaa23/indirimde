from decimal import Decimal

import pytest

from indirimde.money import Money
from indirimde.pricing import DropRule, Price, evaluate


def tl(minor):
    return Money(minor, "TRY")


def test_drop_fires_when_below_thresholds():
    prev = tl(80000)  # 800,00
    now = Price(sale=tl(72000))  # 720,00, a 10% fall
    drop = evaluate(prev, now, DropRule())
    assert drop is not None
    assert drop.amount == tl(8000)
    assert drop.pct == Decimal("10.0")


def test_no_drop_when_price_rises():
    assert evaluate(tl(70000), Price(sale=tl(72000)), DropRule()) is None


def test_no_drop_when_price_equal():
    assert evaluate(tl(70000), Price(sale=tl(70000)), DropRule()) is None


def test_below_percent_threshold_is_ignored():
    # 0,50 TL off 800,00 is well under the default 1%.
    assert evaluate(tl(80000), Price(sale=tl(79950)), DropRule()) is None


def test_below_absolute_threshold_is_ignored():
    # A rule wanting at least 50,00 TL off; a 10,00 TL fall must not fire.
    rule = DropRule(min_pct=Decimal("0"), min_minor=5000)
    assert evaluate(tl(100000), Price(sale=tl(99000)), rule) is None


def test_meets_absolute_but_not_percent():
    rule = DropRule(min_pct=Decimal("20"), min_minor=100)
    # 10% fall clears the 1,00 TL minimum but not the 20% minimum.
    assert evaluate(tl(80000), Price(sale=tl(72000)), rule) is None


def test_currency_mismatch_raises():
    with pytest.raises(ValueError):
        evaluate(Money(100, "USD"), Price(sale=tl(50)), DropRule())


def test_price_sale_and_was_must_match_currency():
    with pytest.raises(ValueError):
        Price(sale=tl(100), was=Money(100, "USD"))
