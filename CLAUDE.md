# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Kararsızım — Proje Rehberi (CLAUDE.md)

Bu dosya, Claude Code'un projeyi anlaması ve fazlar halinde geliştirmesi için hazırlanmıştır.
Projenin kök dizinine `CLAUDE.md` adıyla koy; Claude Code her oturumda bu dosyayı otomatik okur.

> **Claude Code için genel kural:** Her seferinde yalnızca istenen fazı uygula. Bir faz bitmeden sonrakine geçme.
> Faz sonunda "Kabul kriterleri" listesini tek tek kontrol et, ne yaptığını kısaca özetle ve bir sonraki fazı bekle.

---

## 0. Geliştirme Komutları

```bash
# Ortamı kur (bir defalık)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # yerelde DATABASE_URL satırını yorumda bırak, otomatik SQLite kullanılır

# Geliştirme sunucusu
python manage.py runserver

# Migration
python manage.py makemigrations
python manage.py migrate

# Testler
python manage.py test                                                      # tüm testler
python manage.py test polls                                                # tek app
python manage.py test polls.tests.PollModelTests.test_requires_two_options  # tek test

# Sistem kontrolü
python manage.py check
python manage.py check --deploy   # prod'a almadan önce (Faz 5)
```

Bu projede henüz bir linter/formatter yapılandırılmamış (`requirements.txt`'te yok). Bölüm 13'teki kurala göre, prototip sade kalmalı — yeni bir araç eklemeden önce gerçekten gerekli olduğundan emin ol.

### Mimari Özeti (çok dosyaya bakmadan anlaşılmayan noktalar)

- **İki app, tek sorumluluk ayrımı:** `accounts` kimlik/kullanıcı, `polls` anket/seçenek/oy. `config/` sadece proje ayarları ve kök URL yönlendirmesidir (`config/urls.py` → `polls.urls`); iş mantığı app'lerin içinde kalmalı.
- **Özel kullanıcı modeli (Faz 1'de eklenecek):** `accounts.User`, `AbstractUser`'dan türer ve email ile giriş yapar (`USERNAME_FIELD = "email"`), kullanıcı adı ayrı bir zorunlu/benzersiz alandır. Bu model **ilk migration'dan önce** `AUTH_USER_MODEL` olarak ayarlanmalı — sonradan değiştirmek çok zahmetli (bkz. bölüm 4.1).
- **Çift modlu oy verme:** `polls.Vote` hem `user` (üye) hem `voter_token` (misafir çerezi) alanlarını barındırır; tam olarak biri dolu olmalı (`CheckConstraint` + koşullu `UniqueConstraint`'ler). Misafir kimliği bir middleware'in verdiği `voter_id` çerezinden gelir (bölüm 4.5); oy mantığına dokunurken middleware + model kısıtlarını birlikte okumak gerekir.
- **Oy verme JSON sözleşmesi** (bölüm 7), frontend (`static/js/main.js`) ile `polls` view'ları arasındaki tek temas noktasıdır. Sunucu tarafı doğrulama JS'den tamamen bağımsız olmalı: JS kapalıyken aynı endpoint normal form POST'u ile de çalışmalı (progressive enhancement, bölüm 7–8).
- **Ortam bazlı veritabanı seçimi:** `config/settings.py`, `DATABASE_URL` tanımlıysa Supabase/Postgres'e (transaction pooler, port 6543, `DISABLE_SERVER_SIDE_CURSORS=True`) bağlanır; tanımlı değilse SQLite'a düşer. Migration'lar prod'da Vercel build'inde değil, yerelden (session pooler/direkt bağlantı, port 5432) çalıştırılır (bölüm 10).
- **Fazlı geliştirme kuralı:** Bu dosyanın asıl amacı bölüm 12'deki fazları sırayla uygulamaktır — bir faz bitmeden sonrakine geçilmez, her fazın sonunda ilgili "Kabul kriterleri" tek tek doğrulanır. Şu an **Faz 0 tamamlandı** (proje iskeleti); sıradaki adım Faz 1 (kullanıcı sistemi).

---

## 1. Proje Özeti

**Kararsızım**, kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara anket açarak danıştığı bir web uygulamasıdır.

- Örnek soru: *"Bugün sinemaya mı gitsem, restorana mı?"*
- Her ankette **en az 2, en fazla 5 seçenek** bulunur.
- **Takip / arkadaşlık sistemi yoktur.** Platformdaki her anket herkese açıktır.
- **Üye olmayanlar** anketleri görüntüleyebilir ve oy verebilir.
- **Anket oluşturmak için üyelik zorunludur.**
- Üyelikte **e-posta, parola ve kullanıcı adı** alınır. Anketlerde **yalnızca kullanıcı adı** görünür, e-posta hiçbir yerde gösterilmez.

**Hedef:** Önce çalışan, sade bir **prototip**. Karmaşık teknolojilerden kaçın; özellikler sonradan adım adım eklenecek.

---

## 2. Teknoloji Yığını

| Katman | Seçim | Not |
|---|---|---|
| Dil | Python 3.12 | |
| Backend | Django 5.2 (LTS) | Django şablonları (server-side rendering) |
| Veritabanı | Supabase (PostgreSQL) | Supabase **yalnızca Postgres veritabanı** olarak kullanılır |
| Kimlik doğrulama | Django'nun kendi auth sistemi | Supabase Auth **kullanılmaz** |
| Frontend | Saf HTML + CSS + JavaScript | Framework yok, aynı repo içinde (`templates/` ve `static/`) |
| Statik dosyalar | Yerelde Django, prod'da Vercel CDN | WhiteNoise yalnızca gerekirse eklenir |
| Deployment | Vercel (Django zero-config desteği) | `vercel.json` gerekmez |

**Bağımlılıklar (`requirements.txt`):**
```
Django>=5.2,<6.0
psycopg[binary]
dj-database-url
python-dotenv
```

**Kullanılmayacaklar (prototip aşamasında):** React/Vue gibi frontend framework'leri, Tailwind/build adımı, Django REST Framework, Celery, Redis, Docker, Supabase JS istemcisi.

---

## 3. Klasör Yapısı

```
kararsizim/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── manage.py
├── config/                 # Django proje ayarları
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py             # Standart Django WSGI dosyası (Vercel bunu otomatik tanır)
├── accounts/               # Kullanıcı modeli, kayıt, giriş, çıkış, profil
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── polls/                  # Anket, seçenek, oy
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
├── templates/
│   ├── base.html
│   ├── partials/           # navbar, poll_card, mesajlar vb.
│   ├── accounts/
│   └── polls/
└── static/
    ├── css/style.css
    ├── js/main.js
    └── img/
```

---

## 4. Veri Modeli

### 4.1 `accounts.User` (özel kullanıcı modeli)
> ⚠️ Özel kullanıcı modeli **ilk migration'dan önce** oluşturulmalı. Sonradan değiştirmek çok zahmetlidir.

`AbstractUser`'dan türetilir.

| Alan | Tip | Kural |
|---|---|---|
| `email` | EmailField | Zorunlu, benzersiz (büyük/küçük harf duyarsız), **asla herkese gösterilmez** |
| `username` | CharField | Zorunlu, benzersiz (büyük/küçük harf duyarsız), 3–20 karakter, yalnızca `a-z`, `0-9`, `_` |
| `date_joined` | (AbstractUser'dan) | |

- `USERNAME_FIELD = "email"` → giriş **e-posta + parola** ile yapılır.
- `REQUIRED_FIELDS = ["username"]`
- Kullanıcı adı kayıtta küçük harfe çevrilerek saklanır.
- `settings.py` içinde: `AUTH_USER_MODEL = "accounts.User"`

### 4.2 `polls.Poll`
| Alan | Tip | Kural |
|---|---|---|
| `author` | FK → User | `on_delete=CASCADE`, `related_name="polls"` |
| `question` | CharField(200) | Zorunlu, en az 5 karakter |
| `description` | TextField | Opsiyonel, en fazla 500 karakter |
| `created_at` | DateTimeField | `auto_now_add=True`, varsayılan sıralama: yeniden eskiye |

### 4.3 `polls.Option`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | `on_delete=CASCADE`, `related_name="options"` |
| `text` | CharField(80) | Zorunlu |
| `order` | PositiveSmallIntegerField | 0–4, seçeneklerin sırası ve renk eşlemesi için |

- Bir ankette **2–5 seçenek** olmalı (form seviyesinde doğrulanır).
- Aynı ankette tekrar eden seçenek metni olamaz (büyük/küçük harf duyarsız).

### 4.4 `polls.Vote`
| Alan | Tip | Kural |
|---|---|---|
| `poll` | FK → Poll | `on_delete=CASCADE` |
| `option` | FK → Option | `on_delete=CASCADE` |
| `user` | FK → User | `null=True`, üye oyu |
| `voter_token` | UUIDField | `null=True`, üye olmayan oyu |
| `created_at` | DateTimeField | `auto_now_add=True` |

**Kısıtlar:**
- `UniqueConstraint(fields=["poll", "user"], condition=Q(user__isnull=False))`
- `UniqueConstraint(fields=["poll", "voter_token"], condition=Q(voter_token__isnull=False))`
- `CheckConstraint`: `user` veya `voter_token`'dan en az biri dolu olmalı.
- `option.poll == poll` olduğu view içinde kontrol edilmeli.

### 4.5 Üye olmayanların oy kullanması
- Ziyaretçiye ilk girişte `voter_id` adlı bir çerez verilir (UUID4).
  - `httponly=True`, `samesite="Lax"`, `secure=True` (prod'da), ömür: 1 yıl.
- Giriş yapmış kullanıcı oy verirse `user` alanı dolar; yapmamışsa `voter_token` = çerezdeki UUID.
- Bu bir prototip korumasıdır; çerezi silen biri tekrar oy verebilir. Bu bilinçli bir tercih — daha sıkı koruma Faz 6'da.

---

## 5. Ürün Kuralları

1. Bir anket için kişi başı **tek oy**. Prototipte **oy değiştirilemez**.
2. **Sonuçlar oy verdikten sonra** görünür (yüzde + oy sayısı + çubuk grafik). Anket sahibi sonuçları her zaman görür.
3. Oy vermeden önce seçenekler sade butonlar olarak gösterilir.
4. Toplam oy sayısı her durumda kartta görünür ("23 oy").
5. Anket sahibi **kendi anketini silebilir** (onay penceresiyle). Düzenleme prototipte yok.
6. Anket sahibi kendi anketine oy verebilir.
7. E-posta adresi hiçbir şablonda, API yanıtında veya HTML kaynağında görünmemeli.
8. Tüm arayüz metinleri **Türkçe**. `LANGUAGE_CODE = "tr"`, `TIME_ZONE = "Europe/Istanbul"`, `USE_TZ = True`.
9. Tarihler göreli gösterilir: "5 dakika önce", "2 gün önce" (Django `timesince`).

---

## 6. Sayfalar ve URL'ler

| URL | Sayfa | Erişim |
|---|---|---|
| `/` | Ana akış: anket kartları, sekmeler **"En yeni"** / **"Popüler"** (en çok oy alan), sayfalama (20'şer) | Herkes |
| `/anket/<id>/` | Anket detay: soru, açıklama, yazar, seçenekler / sonuçlar | Herkes |
| `/anket/olustur/` | Anket oluşturma formu | Yalnızca üyeler (değilse girişe yönlendir, `?next=` ile) |
| `/anket/<id>/oy/` | Oy verme (POST, JSON döner) | Herkes |
| `/anket/<id>/sil/` | Anket silme (POST) | Yalnızca anket sahibi |
| `/u/<username>/` | Kullanıcının açtığı anketler | Herkes |
| `/kayit/` | Kayıt: kullanıcı adı, e-posta, parola, parola tekrar | Misafirler |
| `/giris/` | Giriş: e-posta + parola | Misafirler |
| `/cikis/` | Çıkış (POST) | Üyeler |
| `/admin/` | Django admin | Süper kullanıcı |

**Navbar:** Logo "Kararsızım" · "Anket Aç" butonu (misafirse giriş sayfasına götürür) · Giriş/Kayıt veya kullanıcı adı + Çıkış.

---

## 7. Oy Verme Akışı (JavaScript)

- Detay sayfasında ve ana akıştaki kartlarda oy verilebilir.
- Seçenek butonuna tıklanınca `fetch` ile `POST /anket/<id>/oy/` (body: `option_id`), CSRF token header'da (`X-CSRFToken`).
- Yanıt:
  ```json
  {
    "ok": true,
    "total_votes": 24,
    "results": [
      {"option_id": 1, "text": "Sinema", "votes": 15, "percent": 62},
      {"option_id": 2, "text": "Restoran", "votes": 9, "percent": 38}
    ],
    "voted_option_id": 1
  }
  ```
- Hata durumları: zaten oy verilmiş → `409`, geçersiz seçenek → `400`. Kullanıcıya kısa bir Türkçe mesaj gösterilir.
- Başarılı yanıtta butonlar sonuç çubuklarına **animasyonla** dönüşür (genişlik 0'dan yüzdeye), seçilen seçenek vurgulanır.
- JavaScript kapalıysa form normal POST ile çalışmalı ve sayfaya yönlendirmeli (progressive enhancement).

## 8. Anket Oluşturma Formu (JavaScript)

- Başlangıçta 2 seçenek alanı gelir.
- "+ Seçenek ekle" butonu 5'e kadar alan ekler, 5'te gizlenir.
- 2'den fazla alan varken her alanın yanında "×" ile silme.
- Karakter sayaçları: soru (200), açıklama (500), seçenek (80).
- Tüm kurallar **sunucu tarafında da** doğrulanır (JS'ye güvenilmez).

---

## 9. Tasarım Rehberi

**Hedef kitle:** Gençler. **His:** Eğlenceli, enerjik ama temiz ve okunaklı.
**Ana fikir:** Açık arka plan + canlı renkler, renklerin açık tonları (tint) yüzeylerde kullanılır.

### Renk paleti (CSS değişkenleri, `:root` içinde)
```css
:root {
  --bg: #FFF9F2;          /* sıcak, açık krem arka plan */
  --surface: #FFFFFF;     /* kartlar */
  --text: #1E1B2E;        /* koyu mürdüm, saf siyah değil */
  --text-muted: #6B6680;
  --border: #EFE8F5;

  --primary: #7C3AED;     /* canlı mor — ana butonlar, logo */
  --primary-tint: #EFE7FF;

  /* 5 seçenek rengi (max 5 seçenek = her birine bir renk) */
  --opt-1: #FF4D8D;  --opt-1-tint: #FFE3EE;  /* pembe */
  --opt-2: #3B82F6;  --opt-2-tint: #E1EDFF;  /* mavi */
  --opt-3: #FFB020;  --opt-3-tint: #FFF1D6;  /* sarı-turuncu */
  --opt-4: #14C38E;  --opt-4-tint: #D9F7EC;  /* nane yeşili */
  --opt-5: #FF6B3D;  --opt-5-tint: #FFE6DC;  /* mercan */

  --radius: 18px;
  --shadow: 0 6px 24px rgba(124, 58, 237, 0.08);
}
```
- Her seçenek `order` değerine göre kendi rengini alır: buton arka planı `tint`, kenarlık/çubuk ana renk.
- Sonuç çubukları seçeneğin ana rengiyle dolar.

### Tipografi
- Google Fonts: **"Plus Jakarta Sans"** (400, 600, 800).
- Soru başlıkları kalın (800), büyük; gövde 16px.

### Bileşen tarzı
- Yuvarlak köşeler (`--radius`), yumuşak gölgeler, bol boşluk.
- Butonlar hap şeklinde (`border-radius: 999px`), hover'da hafif büyüme (`transform: scale(1.03)`).
- Anket kartı: üstte yazar (`@kullaniciadi` + renkli baş harf avatarı) ve zaman, ortada soru, altta seçenekler, en altta oy sayısı.
- Boş durumlar dostça: "Henüz anket yok. İlk kararsızlığı sen paylaş! 🤔"
- **Mobil öncelikli** tasarım; tek sütun, 640px üzerinde ortalanmış maksimum 680px genişlik.
- Erişilebilirlik: yeterli kontrast, odak (focus) halkaları görünür, butonlar gerçek `<button>`.

---

## 10. Ortam Değişkenleri

`.env.example`:
```
SECRET_KEY=degistir-beni
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.vercel.app
CSRF_TRUSTED_ORIGINS=https://*.vercel.app
DATABASE_URL=postgresql://postgres.[proje-ref]:[parola]@aws-0-[bolge].pooler.supabase.com:6543/postgres
```
- `.env` asla commit edilmez (`.gitignore`'a ekle).
- Yerelde `DATABASE_URL` yoksa SQLite'a düş (geliştirme kolaylığı).

### Supabase bağlantı notları
- Vercel serverless olduğu için Supabase'in **pooler (transaction mode, port 6543)** bağlantı adresi kullanılır.
- Transaction pooler ile uyum için `settings.py`:
  ```python
  DATABASES = {"default": dj_database_url.config(conn_max_age=0, ssl_require=True)}
  DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
  ```
- **Migration'lar Vercel build'inde değil, yerelden çalıştırılır** (`python manage.py migrate`), tercihen session pooler / direkt bağlantı (port 5432) ile.
- Supabase Data API (PostgREST) bu projede kullanılmıyor. Tabloların anon anahtarla dışarı açılmaması için Supabase panelinden Data API'yi kapat veya `public` şemasını açık şemalardan çıkar.

---

## 11. Güvenlik Kontrol Listesi
- Prod'da `DEBUG=False`, `SECRET_KEY` ortam değişkeninden.
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` prod'da açık.
- Tüm POST formlarında CSRF koruması; fetch isteklerinde `X-CSRFToken`.
- Kullanıcı girdisi şablonlarda otomatik escape edilir; `|safe` kullanılmaz.
- Silme işlemi yalnızca sahibine; başkası denerse `403`.
- Django'nun parola doğrulayıcıları açık (en az 8 karakter).

---

## 12. Fazlar

Her faz için aşağıdaki promptu Claude Code'a yapıştırabilirsin.

### Faz 0 — Proje iskeleti
**Prompt:**
> CLAUDE.md'yi oku ve sadece Faz 0'ı uygula: Django projesini `config` adıyla, `accounts` ve `polls` uygulamalarını oluştur. Klasör yapısını bölüm 3'e göre kur. `settings.py`'yi ortam değişkenleriyle (python-dotenv, dj-database-url, DATABASE_URL yoksa SQLite) yapılandır, `STATIC_URL`, `STATICFILES_DIRS` ve `STATIC_ROOT`'u tanımla, dil/saat dilimini Türkçe/İstanbul yap. `requirements.txt`, `.env.example`, `.gitignore`, kısa bir `README.md` oluştur. `base.html` iskeletini ve boş `style.css`/`main.js` dosyalarını hazırla. Henüz migration çalıştırma.

**Kabul kriterleri:**
- [ ] `python manage.py check` hatasız.
- [ ] `python manage.py runserver` ile boş ana sayfa açılıyor.
- [ ] `.env` git'e girmiyor.

### Faz 1 — Kullanıcı sistemi
**Prompt:**
> CLAUDE.md'yi oku ve Faz 1'i uygula: Bölüm 4.1'deki özel User modelini oluştur, `AUTH_USER_MODEL`'i ayarla, ilk migration'ları oluşturup çalıştır. Kayıt (kullanıcı adı, e-posta, parola, parola tekrar), e-posta ile giriş ve POST ile çıkış sayfalarını yap. Kullanıcı adı kurallarını (3–20, a-z 0-9 _, büyük/küçük harf duyarsız benzersiz) ve e-posta benzersizliğini doğrula. Navbar'ı giriş durumuna göre göster. Admin'e User'ı kaydet. Formlar için temel testler yaz.

**Kabul kriterleri:**
- [ ] Kayıt → otomatik giriş → ana sayfaya yönlendirme çalışıyor.
- [ ] Aynı kullanıcı adı / e-posta (farklı harf büyüklüğüyle bile) ikinci kez alınamıyor.
- [ ] E-posta hiçbir sayfada görünmüyor.
- [ ] `python manage.py test` geçiyor.

### Faz 2 — Anket oluşturma ve listeleme
**Prompt:**
> CLAUDE.md'yi oku ve Faz 2'yi uygula: Poll, Option ve Vote modellerini (bölüm 4.2–4.4, kısıtlarıyla) oluştur ve migration yap. Anket oluşturma sayfasını (yalnızca üyeler) bölüm 8'deki dinamik seçenek ekleme/silme JS'iyle yap; 2–5 seçenek ve tekrar eden seçenek kurallarını sunucuda doğrula (formset veya özel form). Ana sayfada anket kartlarını "En yeni" ve "Popüler" sekmeleriyle, 20'şerli sayfalamayla listele. Anket detay sayfasını, `/u/<username>/` profil sayfasını ve sahibine özel silme işlemini ekle. Henüz oy verme yok; seçenekler pasif görünsün. Testleri yaz.

**Kabul kriterleri:**
- [ ] Misafir "Anket Aç"a basınca girişe, girişten sonra forma geri dönüyor.
- [ ] 1 veya 6 seçenekli anket oluşturulamıyor (JS kapalıyken de).
- [ ] Kartlarda kullanıcı adı ve göreli zaman görünüyor.
- [ ] Başkasının anketini silme denemesi 403 dönüyor.

### Faz 3 — Oylama ve sonuçlar
**Prompt:**
> CLAUDE.md'yi oku ve Faz 3'ü uygula: Bölüm 4.5'teki `voter_id` çerezini bir middleware ile ver. `POST /anket/<id>/oy/` endpoint'ini bölüm 7'deki JSON sözleşmesiyle yaz (üye → user, misafir → voter_token; tekrar oyda 409). `main.js`'te fetch + CSRF ile oy ver, sonuçları animasyonlu çubuklara dönüştür. Daha önce oy verilmiş anketlerde sayfa açılışında sonuçları doğrudan göster; anket sahibine her zaman göster. JS kapalıyken normal form POST'u çalışsın. Yarış durumlarına karşı veritabanı kısıtına güven ve IntegrityError'ı 409'a çevir. Testleri yaz.

**Kabul kriterleri:**
- [ ] Misafir ve üye birer kez oy verebiliyor, ikinci deneme engelleniyor.
- [ ] Yüzdeler doğru (toplam ≈ 100), oy sayısı güncelleniyor.
- [ ] Başka ankete ait `option_id` ile istek 400 dönüyor.
- [ ] Popüler sekmesi oy sayısına göre sıralıyor.

### Faz 4 — Arayüz cilası
**Prompt:**
> CLAUDE.md'yi oku ve Faz 4'ü uygula: Bölüm 9'daki tasarım rehberini tüm sayfalara uygula — renk değişkenleri, Plus Jakarta Sans, seçenek başına renk, hap butonlar, kart gölgeleri, baş harf avatarları, boş durum mesajları, form hata stilleri, Django mesajları için toast bildirimleri. Mobil öncelikli olsun; 375px ve 1280px genişlikte kontrol et. Yeni bir kütüphane ekleme.

**Kabul kriterleri:**
- [ ] Tüm sayfalar aynı görsel dili kullanıyor.
- [ ] Mobilde yatay kaydırma yok.
- [ ] Klavye ile tüm butonlara ulaşılabiliyor, odak halkası görünüyor.

### Faz 5 — Supabase + Vercel'e yayın
**Prompt:**
> CLAUDE.md'yi oku ve Faz 5'i uygula: Projeyi bölüm 10'daki Supabase pooler ayarlarıyla prod'a hazırla. Vercel Django'yu sıfır yapılandırmayla destekliyor (Nisan 2026'dan beri): `vercel.json` yazma, `/api` klasörü kullanma; standart `manage.py` + `config/wsgi.py` yapısı yeterli. Önce Vercel'in güncel Django dokümanını (https://vercel.com/docs/frameworks/backend/django) oku ve statik dosyaların Vercel CDN'den nasıl sunulduğunu, `STATIC_ROOT`/`collectstatic` gerekip gerekmediğini oradan doğrula; WhiteNoise'ı yalnızca doküman gerektiriyorsa ekle. Bölüm 11'deki prod güvenlik ayarlarını `DEBUG=False` iken etkinleştir. README'ye adım adım yayın talimatı ekle: Supabase'de proje açma, bağlantı adresini alma, yerelden migrate, süper kullanıcı oluşturma, Vercel'de projeyi GitHub reposundan içe aktarma ve ortam değişkenlerini girme.

**Kabul kriterleri:**
- [ ] Vercel adresinde kayıt, anket açma, oy verme çalışıyor.
- [ ] CSS/JS dosyaları prod'da yükleniyor.
- [ ] `DEBUG=False` ve hata sayfaları ham traceback göstermiyor.
- [ ] Veriler Supabase tablolarında görünüyor.

### Faz 6 — Sonraki adımlar (prototipten sonra, ihtiyaca göre seç)
- Oy değiştirme / geri alma
- Anket bitiş süresi ("24 saat sonra kapanır") ve kapanmış anket rozeti
- Arama ve kategoriler/etiketler (yemek, eğlence, alışveriş…)
- Anket paylaşım linki ve Open Graph önizlemesi
- Kötüye kullanım önlemleri: oy ve anket açma için hız sınırı, IP hash, raporlama butonu
- Misafir oyunu giriş sonrası hesaba bağlama
- Parola sıfırlama (e-posta gönderimi)
- Karanlık mod
- Yorumlar ("Ben olsam sinemaya giderdim çünkü…")

---

## 13. Kodlama Kuralları
- Kod ve değişken adları **İngilizce**, kullanıcıya görünen metinler **Türkçe**.
- Function-based veya class-based view serbest, ama proje içinde tutarlı ol.
- N+1 sorgularından kaçın: listelerde `select_related("author")`, `prefetch_related("options")`, oy sayıları için `annotate(Count(...))`.
- Her fazın sonunda `python manage.py test` ve `python manage.py check --deploy` (Faz 5'te) çalıştır.
- Yeni bir bağımlılık eklemeden önce gerçekten gerekli olduğundan emin ol; prototip sade kalmalı.
