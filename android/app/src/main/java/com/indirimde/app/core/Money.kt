package com.indirimde.app.core

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * An exact amount, stored as whole minor units (88445 = 884,45 TL) rather than
 * a float. This is the Kotlin port of the backend's money type, and it exists
 * for the same reason: the app's whole job is to compare one price with another
 * and decide whether it dropped, so the two must compare exactly — which binary
 * floating point cannot promise.
 */
data class Money(val minor: Long, val currency: String = "TRY") : Comparable<Money> {

    override fun compareTo(other: Money): Int {
        require(currency == other.currency) {
            "cannot compare $currency with ${other.currency}"
        }
        return minor.compareTo(other.minor)
    }

    /** Turkish-style text: 1.234,56 TL. */
    fun format(): String {
        val sign = if (minor < 0) "-" else ""
        val abs = Math.abs(minor)
        val whole = abs / 100
        val frac = abs % 100
        val grouped = StringBuilder()
        val digits = whole.toString()
        for (i in digits.indices) {
            if (i > 0 && (digits.length - i) % 3 == 0) grouped.append('.')
            grouped.append(digits[i])
        }
        val symbol = if (currency == "TRY") "TL" else currency
        return "%s%s,%02d %s".format(sign, grouped.toString(), frac, symbol)
    }

    companion object {
        /**
         * Parse a Turkish-formatted price into Money, or null when the text is
         * not a price. Turkish uses '.' for thousands and ',' for the decimal:
         * "1.234,56" is 123456 kuruş; a bare "987" is 98700. Returning null
         * rather than throwing keeps a parse failure distinct from a price of
         * zero — the caller treats null as "could not read", never as free.
         */
        fun parseTr(text: String?, currency: String = "TRY"): Money? {
            if (text == null) return null
            var raw = text.trim()
            if (raw.isEmpty()) return null

            // Strip a trailing currency word/symbol.
            raw = raw.removeSuffix("TL").removeSuffix("TRY").removeSuffix("₺").trim()
            raw = raw.trimStart('₺', '$', '€').trim()
            if (raw.isEmpty()) return null

            val normalized: String = if (raw.contains(',')) {
                val whole = raw.substringBeforeLast(',').replace(".", "")
                val frac = raw.substringAfterLast(',')
                "$whole.$frac"
            } else {
                raw.replace(".", "")
            }

            return try {
                val dec = BigDecimal(normalized)
                val scaled = dec.movePointRight(2).setScale(0, RoundingMode.HALF_UP)
                Money(scaled.toLong(), currency)
            } catch (e: NumberFormatException) {
                null
            }
        }
    }
}
