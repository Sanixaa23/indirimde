# indirimde

Takip ettiğin ürünün fiyatı düştüğünde telefonuna bildirim gönderen uygulama.
Uygulama içinden ürün ara, takibe al, indirime girince haber al.

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

Henüz yok (sıradaki):
- Trendyol canlı fetcher (tarayıcı render) — parser hazır, bağlanacak.
- FastAPI uç noktaları (ara, takibe al, takip listesi, cihaz token kaydı).
- Zamanlayıcı (periyodik yoklama).
- Android uygulaması (Kotlin/Compose: arama, takip listesi, FCM istemci).
- FCM gönderimi — Firebase projesi + `google-services.json` + sunucu kimliği
  gerekir; bunları yalnızca sen oluşturabilirsin, o adım sende.

## Çalıştırma (testler)

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

31 test, hepsi geçer.
