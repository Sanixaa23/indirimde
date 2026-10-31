"""Money as whole minor units — never a float.

A price of 884,45 TL is stored as 88445 kuruş. Prices arrive from stores as
both Turkish-formatted text ("1.234,56") and bare JSON numbers, and the whole
point of the app is to compare two of them and decide whether one dropped, so
they must compare exactly. Binary floating point cannot promise that
(884.45 is not representable), so every amount becomes an integer count of the
currency's smallest unit as early as possible and stays one.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Currencies we handle, with how many minor units make one major unit.
_MINOR_DIGITS = {"TRY": 2, "USD": 2, "EUR": 2}

# Symbols a store might attach to an amount, mapped to the ISO code we store.
_SYMBOL_TO_CODE = {
    "TL": "TRY",
    "₺": "TRY",
    "TRY": "TRY",
    "$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
}


@functools.total_ordering
@dataclass(frozen=True)
class Money:
    """An exact amount: `minor` units of `currency` (e.g. 88445 kuruş, TRY).

    Ordering compares `minor`, so two TRY amounts sort by value; mixing
    currencies in a comparison is a programming error and raises. The remaining
    comparison operators are filled in from `__lt__` and the dataclass
    `__eq__` by `functools.total_ordering`.
    """

    minor: int
    currency: str

    def __post_init__(self) -> None:
        if self.currency not in _MINOR_DIGITS:
            raise ValueError(f"unknown currency: {self.currency!r}")
        if not isinstance(self.minor, int):
            raise TypeError("minor must be int")

    def __lt__(self, other: "Money") -> bool:
        self._same_currency(other)
        return self.minor < other.minor

    def _same_currency(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise TypeError("can only compare Money with Money")
        if self.currency != other.currency:
            raise ValueError(
                f"cannot compare {self.currency} with {other.currency}"
            )

    @property
    def major(self) -> Decimal:
        """The amount as a Decimal major unit, for display only."""
        return Decimal(self.minor) / (10 ** _MINOR_DIGITS[self.currency])

    def format(self) -> str:
        """Turkish-style text: 1.234,56 TL."""
        digits = _MINOR_DIGITS[self.currency]
        sign = "-" if self.minor < 0 else ""
        whole, frac = divmod(abs(self.minor), 10 ** digits)
        grouped = f"{whole:,}".replace(",", ".")
        symbol = "TL" if self.currency == "TRY" else self.currency
        return f"{sign}{grouped},{frac:0{digits}d} {symbol}"

    def __str__(self) -> str:
        return self.format()


def _code_for(currency: str) -> str:
    code = _SYMBOL_TO_CODE.get(currency.strip())
    if code is None:
        raise ValueError(f"unknown currency: {currency!r}")
    return code


def from_major(amount: Decimal | int | str, currency: str = "TRY") -> Money:
    """Build Money from a major-unit amount (12.50 -> 1250 kuruş).

    `amount` may be a Decimal, an int, or an exact decimal string. A float is
    rejected on purpose: 12.5 as a float is not exactly 12.50, and silently
    accepting it reintroduces the rounding error this module exists to avoid.
    Pass str(x) if a float is all you have.
    """
    code = _code_for(currency)
    if isinstance(amount, float):
        raise TypeError("pass a Decimal or an exact string, not a float")
    try:
        dec = Decimal(amount) if not isinstance(amount, Decimal) else amount
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {amount!r}") from exc
    scale = 10 ** _MINOR_DIGITS[code]
    scaled = (dec * scale).to_integral_value(rounding="ROUND_HALF_UP")
    return Money(int(scaled), code)


def parse_tr(text: str, currency: str = "TRY") -> Money:
    """Parse a Turkish-formatted price string into Money.

    Turkish uses '.' for thousands and ',' for the decimal: "1.234,56" is one
    thousand two hundred thirty-four lira and 56 kuruş. A bare "931" is 931,00.
    A trailing currency symbol ("884,45 TL") is read and overrides the default
    currency. Anything that is not a price — empty, letters, a second comma —
    raises, so a parse failure can never be mistaken for a price of zero.
    """
    if text is None:
        raise ValueError("no price text")
    raw = text.strip()
    if not raw:
        raise ValueError("empty price text")

    # Split off a currency word/symbol if present, keep the numeric part.
    code = _code_for(currency)
    for symbol, mapped in _SYMBOL_TO_CODE.items():
        if raw.endswith(symbol):
            code = mapped
            raw = raw[: -len(symbol)].strip()
            break
    raw = raw.lstrip("₺$€").strip()

    if not raw:
        raise ValueError("no numeric part in price text")

    # Normalise the Turkish grouping/decimal marks to a plain decimal string.
    if "," in raw:
        whole, _, frac = raw.rpartition(",")
        whole = whole.replace(".", "")
        normalized = f"{whole}.{frac}"
    else:
        # No decimal comma: dots here are thousands separators ("1.234").
        normalized = raw.replace(".", "")

    if not normalized or not normalized.replace(".", "").isdigit():
        raise ValueError(f"not a Turkish price: {text!r}")

    return from_major(normalized, code)
