# indirimde

Takip ettiğin ürünün fiyatı düştüğünde telefonuna bildirim gönderen uygulama.
Uygulama içinden ürün ara, takibe al, indirime girince haber al.

![indirimde canlı demo](assets/demo.gif)

> Yukarıdaki kayıt **canlı** alınmıştır: tek aramada **Trendyol + n11**'e
> paralel fan-out, gerçek fiyatlar + eski fiyatlar, gerçek düşüş kararı ve
> FCM push (`15.000,00 TL → 6.395,00 TL`, %57.4). Uydurma veri yok.

## Nasıl çalışıyor

Üç parça var ve bilerek ayrık tutuldu:

- **Saf çekirdek** (`backend/indirimde/money.py`, `pricing.py`) — fiyatı tam
  sayı kuruş olarak tutar (float yok, `884,45 TL` = `88445`) ve "bu fiyat
  gerçekten düştü mü?" kararını verir. Ağ yok, aynı girdi hep aynı çıktı,
  tamamı testli.
- **Mağaza adaptörleri** (`backend/indirimde/stores/`) — dış dünyaya dokunan
  tek yer. Her mağazanın bir *parser*'ı (mağazanın verdiği yanıtı `Product`'a
  çevirir, testli) bir de *fetcher*'ı (o yanıtı gidip getiren kırılgan yarı)
  vardır. Fetcher **fail-closed** çalışır: fiyat okunamazsa fiyat uydurmaz,
  boş/`None` döner.
- **İzleyici** (`backend/indirimde/watcher.py`) — bir takibi yoklar: fiyatı
  okur, karar verir, tabanı günceller, düştüyse bildirir. Mağaza çökerse taban
  son gerçek fiyatta kalır; kesinti fiyat değişikliği sanılmaz.

### Mağazalar

Türk alışveriş siteleri. Tek aramada hepsine **paralel fan-out** yapılır
(`stores/multi.py`), sonuçlar harmanlanır; bir ürünün fiyat yeniden-kontrolü
geldiği mağazaya yönlenir. Bir mağaza engellerse diğerlerini batırmaz
(her adaptör fail-closed).

- **Trendyol** — düz istek `403` döndüğü için sayfa tarayıcıda render edilir;
  arama gömülü state'ten (`window["__single-search-result__PROPS"].data`),
  fiyat yeniden-kontrolü ürün sayfasının JSON-LD teklifinden okunur.
- **n11** — arama sayfasının JSON-LD `ItemList`'i (satış + liste/eski fiyat),
  ürün sayfasının JSON-LD `Product` teklifi. `backend/fixtures/n11_*.json`
  canlı siteden yakalanmış örneğe göre testli.
- **Hepsiburada** (opsiyonel, `INDIRIMDE_HEPSIBURADA=1`) — JSON-LD/state
  vermiyor ve headless'a "Güvenlik" bot duvarı çıkarıyor; yalnız **gerçek,
  görünür Google Chrome** (`channel=chrome`, headful) geçiyor, veri DOM'dan
  okunuyor (retry'lı, fail-closed). Arama canlı doğrulandı; PDP fiyat
  yeniden-kontrolü masaüstü oturumu gerektirir (sunucuda Xvfb) ve
  `fixtures/hepsiburada_*.json`'a göre parser testli.

Yeni mağaza eklemek = bir *parser* (fixture'a karşı testli) + bir *fetcher*.
Çoğu sitede fiyat kaynağı ortak: `schema.org/Product → offers.price`
(`stores/ld.py`). **Amazon.com.tr** JSON-LD vermiyor (sadece DOM) — aynı
desenle eklenebilir, henüz yok.

Fiyat anlamı: alıcının ödediği (Trendyol `discountedPriceText`, n11
`offers.price`) → takip edilen fiyat. Çizili/liste fiyat yalnız gösterim için.

## Durum

Bitti ve testli:
- Para tipi (TR fiyat parse, kuruş, Decimal yuvarlama).
- İndirim kararı (yüzde + mutlak eşik, kullanıcı başına kural).
- Trendyol + n11 + Hepsiburada arama parser'ları (gerçek yakalanmış veriye karşı).
- Çoklu-mağaza fan-out arama (paralel, harmanlanmış sonuç, fiyat yönlendirme).
- İzle → oku → karar → bildir akışı, mağaza kesintisine dayanıklı.
- Bildirim metni (Türkçe) ve taşıma arayüzü (FCM enjekte edilir).

- Canlı fetcher'lar (Playwright ile tarayıcı render) — Trendyol 403'ünü ve
  n11 bot duvarını aşar; fiyat için ortak `schema.org/Product → offers.price`
  (JSON-LD) kaynağı. JSON-LD kararlı sözleşmedir; sayfanın değişen özel
  state'ine bağlı değildir.
- **FastAPI sunucusu** (`backend/indirimde/server/`) — ara, cihaz token kaydı,
  takibe al/çıkar, takip listesi uç noktaları; arka planda periyodik yoklama
  (asyncio zamanlayıcı); düşüşte **FCM** push.

Firebase gerektiren tek adım sende: `google-services.json` (istemci) +
servis hesabı JSON'u (sunucu). Yoksa sunucu yine uçtan uca çalışır — FCM
taşıması her push'u göndermek yerine loglar, böylece tüm akış (ara → takip →
yokla → düşüş kararı → render) Firebase'siz denenebilir.

## Sunucu (server + FCM)

```bash
cd backend
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m indirimde.server.run        # http://0.0.0.0:8000
```

Uç noktalar: `POST /search` (tüm mağazalara fan-out), `GET /stores` (aktif
mağazalar), `POST /devices`, `POST/DELETE /watches`, `GET /watches?userId=`,
`POST /poll` (elle tetik), `GET /health`.

Ayarlar (ortam değişkeni): `INDIRIMDE_PORT`, `INDIRIMDE_POLL_SECONDS`
(varsayılan 10800 = 3 saat), `INDIRIMDE_DATA` (JSON durum dosyası),
`INDIRIMDE_FCM_CREDENTIALS` / `GOOGLE_APPLICATION_CREDENTIALS` (servis hesabı).

FCM'i gerçekten göndermek için: Firebase projesi aç, bir servis hesabı anahtarı
indir, yolunu `INDIRIMDE_FCM_CREDENTIALS` ile ver. Anahtar depoya girmez
(`.gitignore`).

## Android uygulaması (v1, bağımsız)

`android/` altında Kotlin + Jetpack Compose uygulaması. Bu ilk sürüm **tek
başına** çalışır: sunucu ya da Firebase gerektirmez.

<img src="assets/android.png" alt="indirimde Android arayüzü" width="300">


- Fiyatı telefonun kendisi kontrol eder. Trendyol'a düz istek 403 döndüğü için
  sayfayı gizli bir **WebView**'de render edip veriyi oradan okur (sunucudaki
  Playwright'ın mobil karşılığı): arama gömülü JSON'dan, fiyat yeniden-kontrolü
  ürün sayfasının DOM'undaki satış fiyatından.
- **WorkManager** 3 saatte bir arka planda kontrol eder; indirim eşiği (yüzde +
  mutlak) aşılınca **yerel bildirim** atar. Backend watcher'ın aynı mantığı:
  ilk okuma tabanı kurar, mağaza kesintisi fiyat değişikliği sanılmaz.
- Para/indirim çekirdeği backend'in Kotlin portu (kuruş, float yok).
- Apple tarzı cam arayüz; "Ara" ve "Takip" sekmeleri.

Kurulabilir APK: bu deponun **Releases** bölümünde.

Kaynaktan derleme (JDK 17 + Android SDK gerekir):

```bash
cd android
./gradlew assembleDebug
```

Not: Gradle/AGP proje yolunda ASCII olmayan karakteri reddeder; depoyu ASCII bir
yola koyup derle.

## Çalıştırma (backend testleri)

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

69 test, hepsi geçer (çekirdek + Trendyol/n11/Hepsiburada parser + watcher +
çoklu-mağaza fan-out + sunucu/HTTP akışı).
