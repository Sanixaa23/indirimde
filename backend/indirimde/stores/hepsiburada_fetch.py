"""The fragile half of the Hepsiburada adapter: a headful Chrome past the wall.

Hepsiburada only lets a real, visible Google Chrome through its bot wall, and
even then the session is sometimes closed mid-load, so every call retries a few
times with a fresh context and fails closed (None) if none succeed. Data is
read from the rendered DOM — there is no JSON-LD or state blob to lean on.

Requires Google Chrome installed and a desktop session (headful). On a headless
server this needs Xvfb; without a display the fetcher simply returns None and
Hepsiburada is treated as unreachable, which the rest of the app handles.
"""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

from .browser import page

SEARCH_URL = "https://www.hepsiburada.com/ara?q={q}"
_RETRIES = 3

# Normalises each search card into the dict the pure parser expects.
_EXTRACT_JS = r"""() => {
  const anchors=[...document.querySelectorAll('a[href*="-p-HB"]')];
  const seen=new Set(); const cards=[];
  for(const a of anchors){
    const m=a.href.match(/-p-([A-Z0-9]+)/i); if(!m) continue;
    const id=m[1]; if(seen.has(id)) continue; seen.add(id);
    let el=a, card=a;
    for(let i=0;i<7&&el;i++){ el=el.parentElement; if(!el)break;
      if(el.tagName==='LI'||el.tagName==='ARTICLE'){card=el;break;} }
    const q=s=>{const n=card.querySelector(s); return n?n.innerText.trim():null;};
    const final=q('[data-test-id^="final-price"]') || q('[data-test-id*="price-current"]');
    if(!final) continue;
    const old=q('del') || q('[data-test-id*="old"]') || q('[data-test-id*="Old"]');
    const title=a.getAttribute('title') || q('[data-test-id^="title"]') || a.innerText.trim();
    const img=card.querySelector('img');
    cards.push({id, url:a.href.split('?')[0], title,
                finalPriceText:final.split('\n').pop().trim(),
                oldPriceText: old? old.split('\n').pop().trim(): null,
                image: img?img.src:""});
    if(cards.length>=20) break;
  }
  return cards;
}"""

# Reads one product page's current price. Prefers JSON-LD (a dot-decimal
# {price, priceCurrency}) when the PDP carries it, else the rendered DOM price
# text ({priceText}, Turkish-formatted). The store parses whichever comes back.
_PRICE_JS = r"""() => {
  const lds=[...document.querySelectorAll('script[type="application/ld+json"]')]
    .map(s=>{try{return JSON.parse(s.textContent);}catch(e){return null;}}).filter(Boolean);
  for(const l of lds){ const arr=Array.isArray(l)?l:[l];
    for(const n of arr){ if(n&&n['@type']==='Product'&&n.offers){ let o=n.offers; if(Array.isArray(o))o=o[0];
      if(o&&o.price!=null) return {price:String(o.price), priceCurrency:o.priceCurrency||'TRY'}; } } }
  const q=s=>{const n=document.querySelector(s); return n?n.innerText.trim():null;};
  let t = q('[data-test-id="price-current-price"]') || q('[data-test-id*="price-current"]')
        || q('[data-test-id^="final-price"]');
  if(!t){ const m=(document.body.innerText||"").match(/\d{1,3}(\.\d{3})*(,\d{2})?\s*TL/); if(m) t=m[0]; }
  if(!t) return null;
  const m2=t.match(/\d{1,3}(\.\d{3})*(,\d{2})?\s*TL/);
  return m2 ? { priceText: m2[0] } : null;
}"""


def _headful():
    # Explicit channel + visible window: the only combination Hepsiburada lets
    # through. channel defaults to "chrome" but honours INDIRIMDE_BROWSER_CHANNEL.
    return page(headless=False, channel="chrome")


def fetch_search(query: str) -> Optional[List[dict]]:
    url = SEARCH_URL.format(q=quote(query))
    for _ in range(_RETRIES):
        try:
            with _headful() as pg:
                pg.goto(url, wait_until="domcontentloaded")
                pg.wait_for_selector('a[href*="-p-HB"]', timeout=20000)
                cards = pg.evaluate(_EXTRACT_JS)
                if cards:
                    return cards
        except Exception:
            continue
    return None


def fetch_price_by_url(url: str) -> Optional[dict]:
    for _ in range(_RETRIES):
        try:
            with _headful() as pg:
                pg.goto(url, wait_until="domcontentloaded")
                pg.wait_for_function(f"() => !!({_PRICE_JS})()", timeout=20000)
                result = pg.evaluate(_PRICE_JS)
                if result:
                    return result
        except Exception:
            continue
    return None


def make_fetchers():
    return fetch_search, fetch_price_by_url
