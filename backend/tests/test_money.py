from decimal import Decimal

import pytest

from indirimde.money import Money, from_major, parse_tr


def test_parse_plain_integer():
    assert parse_tr("931") == Money(93100, "TRY")


def test_parse_turkish_decimal():
    assert parse_tr("884,45") == Money(88445, "TRY")


def test_parse_thousands_and_decimal():
    assert parse_tr("1.234,56") == Money(123456, "TRY")


def test_parse_thousands_only():
    assert parse_tr("1.299") == Money(129900, "TRY")


def test_parse_with_trailing_symbol():
    assert parse_tr("455,90 TL") == Money(45590, "TRY")


def test_parse_rejects_empty():
    with pytest.raises(ValueError):
        parse_tr("")


def test_parse_rejects_letters():
    with pytest.raises(ValueError):
        parse_tr("fiyat yok")


def test_from_major_rejects_float():
    # 12.5 as a float is not exactly 12.50; the API must refuse it.
    with pytest.raises(TypeError):
        from_major(12.5)


def test_from_major_string_is_exact():
    assert from_major("884.45") == Money(88445, "TRY")


def test_from_major_rounds_half_up():
    assert from_major(Decimal("10.005")) == Money(1001, "TRY")


def test_unknown_currency_rejected():
    with pytest.raises(ValueError):
        Money(100, "XXX")


def test_format_turkish():
    assert Money(123456, "TRY").format() == "1.234,56 TL"


def test_ordering_same_currency():
    assert Money(45590, "TRY") < Money(88445, "TRY")


def test_ordering_cross_currency_raises():
    with pytest.raises(ValueError):
        Money(100, "TRY") < Money(100, "USD")
