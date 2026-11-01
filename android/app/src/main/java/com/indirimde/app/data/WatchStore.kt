package com.indirimde.app.data

import android.content.Context
import com.indirimde.app.core.DropRule
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.math.BigDecimal

/**
 * The watchlist, persisted as one JSON file. Room would be overkill for a
 * handful of watches and would drag in annotation processing; a plain file,
 * written atomically (temp then rename), is enough and keeps the build simple.
 * All access is synchronized because the UI thread and the background worker
 * both touch it.
 */
class WatchStore(context: Context) {

    private val file = File(context.filesDir, "watches.json")
    private val lock = Any()

    fun load(): MutableList<Watch> = synchronized(lock) {
        if (!file.exists()) return mutableListOf()
        return try {
            val arr = JSONArray(file.readText(Charsets.UTF_8))
            MutableList(arr.length()) { fromJson(arr.getJSONObject(it)) }
        } catch (e: Exception) {
            // A corrupt file is reported by returning empty rather than
            // crashing; it is not silently overwritten until the next save.
            mutableListOf()
        }
    }

    fun save(watches: List<Watch>) = synchronized(lock) {
        val arr = JSONArray()
        watches.forEach { arr.put(toJson(it)) }
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeText(arr.toString(), Charsets.UTF_8)
        if (file.exists()) file.delete()
        tmp.renameTo(file)
    }

    private fun toJson(w: Watch): JSONObject {
        val p = w.product
        val prod = JSONObject()
            .put("store", p.store).put("storeId", p.storeId).put("name", p.name)
            .put("url", p.url).put("saleMinor", p.saleMinor)
            .put("wasMinor", p.wasMinor ?: JSONObject.NULL)
            .put("currency", p.currency).put("brand", p.brand).put("image", p.image)
            .put("rating", p.rating ?: JSONObject.NULL).put("ratingCount", p.ratingCount)
        val hist = JSONArray()
        w.history.forEach { hist.put(JSONObject().put("at", it.atMillis).put("minor", it.minor)) }
        return JSONObject()
            .put("product", prod)
            .put("addedMinor", w.addedMinor)
            .put("baselineMinor", w.baselineMinor ?: JSONObject.NULL)
            .put("lastCheckMillis", w.lastCheckMillis)
            .put("lastReachable", w.lastReachable)
            .put("ruleMinPct", w.rule.minPct.toString())
            .put("ruleMinMinor", w.rule.minMinor)
            .put("history", hist)
    }

    private fun fromJson(o: JSONObject): Watch {
        val p = o.getJSONObject("product")
        val product = Product(
            store = p.getString("store"),
            storeId = p.getString("storeId"),
            name = p.getString("name"),
            url = p.getString("url"),
            saleMinor = p.getLong("saleMinor"),
            wasMinor = if (p.isNull("wasMinor")) null else p.getLong("wasMinor"),
            currency = p.optString("currency", "TRY"),
            brand = p.optString("brand", ""),
            image = p.optString("image", ""),
            rating = if (p.isNull("rating")) null else p.getDouble("rating"),
            ratingCount = p.optInt("ratingCount", 0),
        )
        val history = mutableListOf<PricePoint>()
        val hist = o.optJSONArray("history")
        if (hist != null) for (i in 0 until hist.length()) {
            val h = hist.getJSONObject(i)
            history.add(PricePoint(h.getLong("at"), h.getLong("minor")))
        }
        return Watch(
            product = product,
            addedMinor = o.getLong("addedMinor"),
            baselineMinor = if (o.isNull("baselineMinor")) null else o.getLong("baselineMinor"),
            lastCheckMillis = o.optLong("lastCheckMillis", 0L),
            lastReachable = o.optBoolean("lastReachable", true),
            history = history,
            rule = DropRule(
                minPct = BigDecimal(o.optString("ruleMinPct", "1")),
                minMinor = o.optLong("ruleMinMinor", 100),
            ),
        )
    }
}
