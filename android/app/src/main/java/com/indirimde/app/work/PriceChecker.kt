package com.indirimde.app.work

import android.content.Context
import com.indirimde.app.core.Money
import com.indirimde.app.core.evaluateDrop
import com.indirimde.app.data.PricePoint
import com.indirimde.app.data.Watch
import com.indirimde.app.notify.Notifications
import com.indirimde.app.scrape.Trendyol

/**
 * The one place the check logic lives, shared by the background worker and the
 * in-app "check now" button so they can never drift apart. Updates the watch in
 * place and shows a notification on a qualifying drop.
 */
object PriceChecker {

    /** Check one watch. Returns true if a drop notification was shown. */
    suspend fun checkOne(context: Context, watch: Watch): Boolean {
        val price = Trendyol.fetchPrice(context, watch.product.url)
        watch.lastCheckMillis = System.currentTimeMillis()
        if (price == null) {
            watch.lastReachable = false
            return false
        }
        watch.lastReachable = true
        watch.history.add(PricePoint(watch.lastCheckMillis, price.minor))
        if (watch.history.size > 60) watch.history.removeAt(0)

        val baseline = watch.baselineMinor
        if (baseline == null) {
            watch.baselineMinor = price.minor
            return false
        }
        val drop = evaluateDrop(Money(baseline, watch.currency), price, watch.rule)
        watch.baselineMinor = price.minor
        if (drop != null) {
            Notifications.showDrop(context, watch, drop)
            return true
        }
        return false
    }
}
