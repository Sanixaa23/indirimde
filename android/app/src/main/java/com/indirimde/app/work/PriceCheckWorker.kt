package com.indirimde.app.work

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.indirimde.app.data.WatchStore
import java.util.concurrent.TimeUnit

/**
 * The background check. For each watch it reads the current price, and:
 *   - if the store was unreachable, it changes nothing (an outage is never
 *     mistaken for a price change);
 *   - on the first successful reading it sets the baseline and does not notify;
 *   - otherwise it compares against the baseline, notifies on a qualifying
 *     drop, and moves the baseline to the new price.
 * This mirrors the backend watcher exactly, just on the phone.
 */
class PriceCheckWorker(appContext: Context, params: WorkerParameters) :
    CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val store = WatchStore(applicationContext)
        val watches = store.load()
        if (watches.isEmpty()) return Result.success()

        for (watch in watches) {
            PriceChecker.checkOne(applicationContext, watch)
        }

        store.save(watches)
        return Result.success()
    }

    companion object {
        private const val NAME = "price-check"

        /** Schedule the periodic check (every 3 hours; WorkManager's floor is
         * 15 minutes, but prices don't move that fast and this spares battery). */
        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<PriceCheckWorker>(3, TimeUnit.HOURS)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                NAME, ExistingPeriodicWorkPolicy.KEEP, request,
            )
        }
    }
}
