package com.indirimde.app.scrape

import android.content.Context
import com.indirimde.app.core.Money
import com.indirimde.app.data.Product

/**
 * The Trendyol store, on-device. Search reads the embedded result JSON; a
 * price recheck reads the selling price straight off the product page's DOM,
 * which is the most durable signal there is — it is exactly what a shopper
 * sees. Both go through the WebView extractor and both fail closed: an empty
 * list or a null price, never a guess.
 */
object Trendyol {

    private fun searchUrl(query: String): String {
        val q = java.net.URLEncoder.encode(query, "UTF-8")
        return "https://www.trendyol.com/sr?q=$q"
    }

    // Pull the embedded search products as a JSON array string, or null.
    private const val SEARCH_PROBE = """
        (function(){
          try {
            var s = window['__single-search-result__PROPS'];
            if (s && s.data && s.data.products && s.data.products.length)
              return JSON.stringify(s.data.products);
          } catch(e){}
          return null;
        })()
    """

    // Read the selling price text ("987 TL") from the product page, skipping
    // add-on service (vas), installment and basket figures.
    private const val PRICE_PROBE = """
        (function(){
          try {
            var els = document.querySelectorAll('[class*="price"],[class*="Price"]');
            for (var i=0;i<els.length;i++){
              var e = els[i];
              var c = (e.className || '') + '';
              if (/vas|installment|taksit|campaign|coupon|cart|basket|strike|old/i.test(c)) continue;
              var t = (e.textContent || '').trim();
              if (/^\d{1,3}(\.\d{3})*(,\d{2})?\s*TL${'$'}/.test(t)) return t;
            }
          } catch(e){}
          return null;
        })()
    """

    suspend fun search(context: Context, query: String, limit: Int = 24): List<Product> {
        val json = WebExtractor.extract(context, searchUrl(query), SEARCH_PROBE) ?: return emptyList()
        return TrendyolParse.parseSearch(json).take(limit)
    }

    /** The product's current selling price, or null if it could not be read. */
    suspend fun fetchPrice(context: Context, url: String): Money? {
        val text = WebExtractor.extract(context, url, PRICE_PROBE) ?: return null
        return Money.parseTr(text)
    }
}
