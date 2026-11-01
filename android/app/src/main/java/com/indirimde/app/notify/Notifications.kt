package com.indirimde.app.notify

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.content.getSystemService
import com.indirimde.app.R
import com.indirimde.app.core.Drop
import com.indirimde.app.data.Watch

/** Renders and shows the drop notification. Wording matches the backend. */
object Notifications {

    private const val CHANNEL_ID = "drops"

    fun ensureChannel(context: Context) {
        val mgr = context.getSystemService<NotificationManager>() ?: return
        if (mgr.getNotificationChannel(CHANNEL_ID) == null) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Fiyat düşüşleri",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply { description = "Takip ettiğin ürün indirime girince bildirir." }
            mgr.createNotificationChannel(channel)
        }
    }

    private fun shorten(name: String, limit: Int = 48): String {
        val n = name.trim()
        return if (n.length <= limit) n else n.take(limit - 1).trimEnd() + "…"
    }

    fun showDrop(context: Context, watch: Watch, drop: Drop) {
        ensureChannel(context)
        val mgr = context.getSystemService<NotificationManager>() ?: return

        val title = "${shorten(watch.product.name)} indirimde"
        val body = "${drop.was.format()} → ${drop.now.format()}  (%${drop.pct} indirim)"

        val open = Intent(Intent.ACTION_VIEW, Uri.parse(watch.product.url))
        val pending = PendingIntent.getActivity(
            context, watch.product.key.hashCode(), open,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_drop)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(pending)
            .setAutoCancel(true)
            .build()

        mgr.notify(watch.product.key.hashCode(), notification)
    }
}
