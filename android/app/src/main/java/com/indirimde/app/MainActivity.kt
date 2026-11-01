package com.indirimde.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.indirimde.app.notify.Notifications
import com.indirimde.app.ui.AppScreen
import com.indirimde.app.ui.IndirimdeTheme
import com.indirimde.app.work.PriceCheckWorker

class MainActivity : ComponentActivity() {

    private val askNotify =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        Notifications.ensureChannel(this)
        requestNotificationPermission()
        PriceCheckWorker.schedule(this)

        setContent {
            IndirimdeTheme {
                val vm: AppViewModel = viewModel()
                AppScreen(vm)
            }
        }
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val granted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED
            if (!granted) askNotify.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
