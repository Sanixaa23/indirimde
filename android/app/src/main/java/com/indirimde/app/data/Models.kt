package com.indirimde.app.data

import com.indirimde.app.core.DropRule
import com.indirimde.app.core.Money

/** One search hit from a store. */
data class Product(
    val store: String,
    val storeId: String,
    val name: String,
    val url: String,
    val saleMinor: Long,
    val wasMinor: Long? = null,
    val currency: String = "TRY",
    val brand: String = "",
    val image: String = "",
    val rating: Double? = null,
    val ratingCount: Int = 0,
) {
    val key: String get() = "$store:$storeId"
    val sale: Money get() = Money(saleMinor, currency)
}

/** One recorded price reading over time, for the little history line. */
data class PricePoint(val atMillis: Long, val minor: Long)

/**
 * A standing request to track one product. [baselineMinor] is the price the
 * drop decision compares against; it is null until the first successful check
 * sets it (so the add-time search price, which can differ from the product
 * page, never triggers a false drop). [addedMinor] is kept only for display.
 */
data class Watch(
    val product: Product,
    val addedMinor: Long,
    var baselineMinor: Long? = null,
    var lastCheckMillis: Long = 0L,
    var lastReachable: Boolean = true,
    val history: MutableList<PricePoint> = mutableListOf(),
    val rule: DropRule = DropRule(),
) {
    val currency: String get() = product.currency
}
