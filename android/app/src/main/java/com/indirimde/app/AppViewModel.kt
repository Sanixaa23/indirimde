package com.indirimde.app

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.toMutableStateList
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.indirimde.app.data.Product
import com.indirimde.app.data.Watch
import com.indirimde.app.data.WatchStore
import com.indirimde.app.scrape.Trendyol
import com.indirimde.app.work.PriceChecker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AppViewModel(app: Application) : AndroidViewModel(app) {

    private val store = WatchStore(app)

    val watches = store.load().toMutableStateList()
    val results = mutableListOf<Product>().toMutableStateList()

    var query by mutableStateOf("")
        private set
    var searching by mutableStateOf(false)
        private set
    var searchError by mutableStateOf<String?>(null)
        private set
    var checking by mutableStateOf(false)
        private set

    private val watchedKeys: Set<String> get() = watches.map { it.product.key }.toSet()

    fun isWatched(product: Product): Boolean = product.key in watchedKeys

    fun onQueryChange(value: String) { query = value }

    fun search() {
        val q = query.trim()
        if (q.isEmpty() || searching) return
        searching = true
        searchError = null
        viewModelScope.launch {
            val found = Trendyol.search(getApplication(), q)
            results.clear()
            results.addAll(found)
            searchError = if (found.isEmpty()) "Sonuç yok ya da Trendyol'a ulaşılamadı." else null
            searching = false
        }
    }

    fun addWatch(product: Product) {
        if (isWatched(product)) return
        watches.add(Watch(product = product, addedMinor = product.saleMinor))
        persist()
    }

    fun removeWatch(key: String) {
        watches.removeAll { it.product.key == key }
        persist()
    }

    /** Re-check every watch now, in the foreground, so the user sees it work. */
    fun checkNow() {
        if (checking || watches.isEmpty()) return
        checking = true
        viewModelScope.launch {
            for (i in watches.indices) {
                val watch = watches[i]
                PriceChecker.checkOne(getApplication(), watch)
                // Re-assign to trigger recomposition of this row.
                watches[i] = watch.copy()
            }
            persist()
            checking = false
        }
    }

    private fun persist() {
        viewModelScope.launch(Dispatchers.IO) { store.save(watches.toList()) }
    }
}

private fun Watch.copy(): Watch = Watch(
    product = product,
    addedMinor = addedMinor,
    baselineMinor = baselineMinor,
    lastCheckMillis = lastCheckMillis,
    lastReachable = lastReachable,
    history = history,
    rule = rule,
)
