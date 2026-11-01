package com.indirimde.app.scrape

import android.annotation.SuppressLint
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONObject
import org.json.JSONTokener
import kotlin.coroutines.resume

/**
 * Loads a page in an offscreen WebView and runs a probe script against it,
 * returning whatever string the probe produced — or null on timeout or
 * failure. This is the on-device equivalent of the server's Playwright: a
 * plain request to Trendyol is 403-blocked, but a real WebView renders the
 * page and we read the same embedded data the browser sees.
 *
 * The probe is polled after the page finishes because Trendyol hydrates its
 * state after load. Everything runs on the main thread (WebView's requirement)
 * and the WebView is always destroyed, success or not.
 */
object WebExtractor {

    private const val USER_AGENT =
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) " +
            "Chrome/125.0.0.0 Mobile Safari/537.36"

    private const val POLL_MS = 350L
    private const val MAX_POLLS = 45
    private const val TIMEOUT_MS = 30_000L

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun extract(context: Context, url: String, probeJs: String): String? =
        withTimeoutOrNull(TIMEOUT_MS) {
            withContext(Dispatchers.Main) {
                suspendCancellableCoroutine { cont ->
                    val handler = Handler(Looper.getMainLooper())
                    val webView = WebView(context.applicationContext)
                    var finished = false

                    fun finish(result: String?) {
                        if (finished) return
                        finished = true
                        webView.stopLoading()
                        webView.destroy()
                        if (cont.isActive) cont.resume(result)
                    }

                    webView.settings.apply {
                        javaScriptEnabled = true
                        domStorageEnabled = true
                        userAgentString = USER_AGENT
                        blockNetworkImage = true // we only need the data, not the pictures
                        loadsImagesAutomatically = false
                    }

                    webView.webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, pageUrl: String?) {
                            var tries = 0
                            val poll = object : Runnable {
                                override fun run() {
                                    if (finished) return
                                    webView.evaluateJavascript(probeJs) { raw ->
                                        val value = decode(raw)
                                        if (!value.isNullOrEmpty()) {
                                            finish(value)
                                        } else if (tries++ < MAX_POLLS) {
                                            handler.postDelayed(this, POLL_MS)
                                        } else {
                                            finish(null)
                                        }
                                    }
                                }
                            }
                            handler.post(poll)
                        }
                    }

                    cont.invokeOnCancellation {
                        handler.post { finish(null) }
                    }

                    webView.loadUrl(url)
                }
            }
        }

    /**
     * evaluateJavascript hands back the JS value already JSON-encoded. When the
     * probe returns a string, that means a quoted, escaped string; unwrap one
     * level. "null" and literal null both mean "nothing yet".
     */
    private fun decode(raw: String?): String? {
        if (raw == null || raw == "null") return null
        return try {
            when (val v = JSONTokener(raw).nextValue()) {
                is String -> v
                JSONObject.NULL -> null
                else -> v.toString()
            }
        } catch (e: Exception) {
            raw
        }
    }
}
