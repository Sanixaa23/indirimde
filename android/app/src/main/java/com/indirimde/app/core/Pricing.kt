package com.indirimde.app.core

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * When a change counts as a drop worth notifying. Both thresholds must be met:
 * the price must fall by at least [minPct] percent and by at least [minMinor]
 * units. Defaults to a 1% and 1,00 TL fall, so a rounding wiggle never fires.
 */
data class DropRule(val minPct: BigDecimal = BigDecimal("1"), val minMinor: Long = 100)

/** A confirmed drop: enough to tell the user about. */
data class Drop(val was: Money, val now: Money, val amount: Money, val pct: BigDecimal)

/**
 * Return a [Drop] when [currentSale] is meaningfully below [previous], else
 * null. This is the port of the backend's one real decision; the caller
 * notifies only on a non-null result.
 */
fun evaluateDrop(previous: Money, currentSale: Money, rule: DropRule = DropRule()): Drop? {
    require(previous.currency == currentSale.currency) { "currency mismatch" }
    val fall = previous.minor - currentSale.minor
    if (fall <= 0) return null
    if (rule.minMinor > 0 && fall < rule.minMinor) return null

    val pct = BigDecimal(fall).multiply(BigDecimal(100))
        .divide(BigDecimal(previous.minor), 1, RoundingMode.HALF_UP)
    if (rule.minPct.signum() > 0 && pct < rule.minPct) return null

    return Drop(
        was = previous,
        now = currentSale,
        amount = Money(fall, currentSale.currency),
        pct = pct,
    )
}
