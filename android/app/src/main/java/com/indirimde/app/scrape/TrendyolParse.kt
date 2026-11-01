package com.indirimde.app.scrape

import com.indirimde.app.core.Money
import com.indirimde.app.data.Product
import org.json.JSONArray
import org.json.JSONObject

/**
 * Pure parsing of what the WebView pulled off the Trendyol page. Kept separate
 * from the WebView itself so the shape handling is testable and so a listing
 * with an unreadable price is dropped, never guessed.
 *
 * Price fields match the backend: `discountedPriceText` is what the buyer pays
 * (-> sale), `oldText` when `old > 0` is the struck-through former price.
 */
object TrendyolParse {

    private const val BASE = "https://www.trendyol.com"

    /** Parse the JSON array string of search products into Products. */
    fun parseSearch(productsJson: String): List<Product> {
        val out = mutableListOf<Product>()
        val arr = try {
            JSONArray(productsJson)
        } catch (e: Exception) {
            return out
        }
        for (i in 0 until arr.length()) {
            parseProduct(arr.optJSONObject(i) ?: continue)?.let { out.add(it) }
        }
        return out
    }

    private fun parseProduct(raw: JSONObject): Product? {
        val id = raw.opt("id")?.toString() ?: return null
        val name = raw.optString("name").ifBlank { return null }
        val url = raw.optString("url").ifBlank { return null }
        val priceObj = raw.optJSONObject("price") ?: return null

        val symbol = priceObj.optString("currencySymbol").ifBlank {
            priceObj.optString("currency", "TL")
        }
        val sale = Money.parseTr(priceObj.optString("discountedPriceText"), codeFor(symbol))
            ?: return null

        val oldRaw = priceObj.opt("old")?.toString()
        val wasMinor = if (oldRaw != null && oldRaw != "0" && oldRaw != "0.0") {
            Money.parseTr(priceObj.optString("oldText"), codeFor(symbol))?.minor
        } else null

        val rating = raw.optJSONObject("ratingScore")
        return Product(
            store = "trendyol",
            storeId = id,
            name = name,
            url = if (url.startsWith("http")) url else BASE + url,
            saleMinor = sale.minor,
            wasMinor = wasMinor,
            currency = sale.currency,
            brand = raw.optString("brand", ""),
            image = raw.optString("image", ""),
            rating = rating?.optDouble("averageRating"),
            ratingCount = rating?.optInt("totalCount", 0) ?: 0,
        )
    }

    private fun codeFor(symbol: String): String = when (symbol.trim()) {
        "TL", "₺", "TRY" -> "TRY"
        "$", "USD" -> "USD"
        "€", "EUR" -> "EUR"
        else -> "TRY"
    }
}
