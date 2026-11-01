# indirimde

Takip ettiğin ürünün fiyatı düştüğünde telefonuna bildirim gönderen uygulama.
Uygulama içinden ürün ara, takibe al, indirime girince haber al.

![indirimde canlı demo](assets/demo.gif)

> Yukarıdaki kayıt **canlı Trendyol'dan** alınmıştır: gerçek arama, gerçek
> fiyatlar, gerçek düşüş kararı (`719,00 TL → 699,00 TL`, %2.8). Uydurma veri yok.

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

Mağaza olarak Türkiye seçildi; ilk adaptör **Trendyol**. Trendyol düz sunucu
isteğini `403` ile reddediyor (bot koruması), bu yüzden arama sonucu gerçek bir
tarayıcıda render edilip sayfadaki gömülü JSON
(`window["__single-search-result__PROPS"].data`) alınır. Parser bu yapıyı
canlı siteden yakalanmış bir örneğe (`backend/fixtures/`) göre test edilir.

Fiyat anlamı: alıcının ödediği = `discountedPriceText` → takip edilen fiyat.
`old > 0` olduğunda çizili eski fiyat gösterim içindir.

## Durum

Bitti ve testli:
- Para tipi (TR fiyat parse, kuruş, Decimal yuvarlama).
- İndirim kararı (yüzde + mutlak eşik, kullanıcı başına kural).
- Trendyol arama parser'ı (gerçek yakalanmış veriye karşı).
- İzle → oku → karar → bildir akışı, mağaza kesintisine dayanıklı.
- Bildirim metni (Türkçe) ve taşıma arayüzü (FCM enjekte edilir).

- Trendyol canlı fetcher (Playwright ile tarayıcı render) — 403 engelini aşıp
  gömülü arama JSON'unu çeker.

Henüz yok (sunucu yolu için sıradaki):
- FastAPI uç noktaları (ara, takibe al, takip listesi, cihaz token kaydı).
- Zamanlayıcı (periyodik yoklama).
- FCM gönderimi — Firebase projesi + `google-services.json` + sunucu kimliği
  gerekir; bunları yalnızca sen oluşturabilirsin, o adım sende.

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

31 test, hepsi geçer.
