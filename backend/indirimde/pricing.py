"""The price model and the one decision the whole app turns on: did it drop?

A store listing carries two numbers that matter: the price you actually pay
today (the sale price) and, sometimes, a struck-through former price. We track
the sale price. The drop decision compares the last sale price we recorded with
the one we just read and reports a drop only when it clears the user's
thresholds — so a one-lira wiggle or a rounding artefact never fires a
notification.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .money import Money


@dataclass(frozen=True)
class Price:
    """What a listing costs right now.

    `sale` is the amount the buyer pays. `was` is the former/struck-through
    price when the store shows one, else None; it is for display and for
    computing "percent off the list price", never for the drop decision, which
    only ever compares successive `sale` values we have seen ourselves.
    """

    sale: Money
    was: Optional[Money] = None

    def __post_init__(self) -> None:
        if self.was is not None and self.was.currency != self.sale.currency:
            raise ValueError("sale and was must share a currency")

    @property
    def currency(self) -> str:
        return self.sale.currency


@dataclass(frozen=True)
class DropRule:
    """When a change counts as a drop worth a notification.

    Both thresholds must be met: the price must fall by at least `min_pct`
    percent *and* by at least `min_minor` units. Defaults: a 1% and 1 TL fall.
    Set a threshold to 0 to disable it.
    """

    min_pct: Decimal = Decimal("1")
    min_minor: int = 100  # 1,00 TL

    def __post_init__(self) -> None:
        if self.min_pct < 0 or self.min_minor < 0:
            raise ValueError("thresholds cannot be negative")


@dataclass(frozen=True)
class Drop:
    """A confirmed drop: enough to tell the user about."""

    was: Money
    now: Money
    amount: Money  # how much it fell, always positive
    pct: Decimal  # percent of the previous price, rounded to 0.1


def evaluate(previous: Money, current: Price, rule: DropRule) -> Optional[Drop]:
    """Return a Drop when `current.sale` is meaningfully below `previous`.

    `previous` is the last sale price we stored for this watch. Returns None
    when the price rose, held, or fell by less than the rule requires — the
    caller notifies only on a non-None result, so "no drop" and "could not
    read the price" stay distinct (the latter never reaches here).
    """
    if previous.currency != current.sale.currency:
        raise ValueError("previous and current prices are in different currencies")

    fall = previous.minor - current.sale.minor
    if fall <= 0:
        return None

    if rule.min_minor and fall < rule.min_minor:
        return None

    # Percent of the previous price, rounded to one decimal place.
    pct = (Decimal(fall) * 100 / Decimal(previous.minor)).quantize(Decimal("0.1"))
    if rule.min_pct and pct < rule.min_pct:
        return None

    return Drop(
        was=previous,
        now=current.sale,
        amount=Money(fall, current.sale.currency),
        pct=pct,
    )
