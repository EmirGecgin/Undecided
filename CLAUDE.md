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
- **Fazlı geliştirme kuralı:** Bu dosyanın asıl amacı bölüm 12'deki fazları sırayla uygulamaktır — bir faz bitmeden sonrakine geçilmez, her fazın sonunda ilgili "Kabul kriterleri" tek tek doğrulanır. Şu an **Faz 5 tamamlandı** (Supabase + Vercel'e yayın); prototip canlıda. Faz 6'dan "anket bitiş süresi" ve "arama/kategoriler" eklendi (bkz. bölüm 12); listedeki diğer maddeler ihtiyaca göre seçilecek. **Prod dağıtım durumu ve kritik tuzaklar için bölüm 10.1'i mutlaka oku.**
- **Oy verme görünümü context'e göre dallanır:** `templates/partials/poll_options.html`, hepsi tek bir `.poll-vote-area` sarmalayıcısı içinde olmak üzere üç moddan birini render eder — `poll.show_results` doluysa sonuç satırları (`interactive` ve `poll.can_vote` ikisi de doğruysa — yani detay sayfasında ve anket kapalı değilse — her satır tıklanabilir bir oy formudur: ilk oy da, oy **değiştirme** de aynı uca gider; aksi halde salt okunur `role=progressbar` satırı), değilse (`show_results` boş) `interactive` context değişkenine bakılır: `True` ise aktif oy formu (sadece `polls/detail.html` bunu `{% include ... with interactive=True %}` ile geçiyor), yoksa (ana sayfa/profil) nötr/yüzdesiz önizleme barı. **`static/js/main.js`'teki `renderPollResults` bu yapıyı DOM'da yeniden üretir** (her AJAX oy/değişiklik sonrası `.poll-vote-area`'nın içeriği komple değiştirilir) — şablondaki ARIA attribute'ları ve tıklanabilirlik mantığı (`data.is_closed`, `container.dataset.voteUrl`) burada da birebir olmalı; biri değişince diğerini güncellemeyi unutma (bir kez unutulup sonradan fark edilip düzeltildi).
- **Static dosya önbellek kırma (prod):** `STORAGES["staticfiles"]`, `DEBUG=False` iken `ManifestStaticFilesStorage` kullanır — `collectstatic` her dosyayı içerik hash'iyle yeniden adlandırır (`main.a1b2c3.js`), `{% static %}` etiketi otomatik doğru adı çözer. Bu sayede bir deploy'da JS/CSS değişince tarayıcılar eski sürümü önbellekten kullanmaya devam etmez. Yerelde (`DEBUG=True`) düz `StaticFilesStorage` kullanılır, `collectstatic` çalıştırmaya gerek yok.

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
| Dil | Python 3.12 | Bu makinede 3.12 kurulu değildi (pyenv/homebrew yok); kullanıcı onayıyla **3.14** ile devam edildi, Django 5.2 sorunsuz çalışıyor. Yeni bir makinede 3.12 varsa tercih et, yoksa 3.14'ü sorgulamadan kullan. |
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
- **Misafir oyu → hesap bağlama:** `polls/signals.py`, Django'nun `user_logged_in` sinyaline bağlı (`polls/apps.py: ready()`); hem `LoginView` hem `register()`'daki otomatik login bu sinyali tetikler. Giriş anında, o tarayıcının `voter_id` çerezine ait tüm misafir oyları (`voter_token` dolu, `user` boş) giriş yapan kullanıcıya taşınır. Kullanıcının o ankete zaten üye olarak oyu varsa (başka bir cihazdan), misafir oyu çakışma yaratmadan silinir.

---

## 5. Ürün Kuralları

1. Bir anket için kişi başı **tek oy**, ama **oy değiştirilebilir**: aynı kullanıcı/misafir tekrar oy verirse (poll kapalı değilse) mevcut `Vote` satırının `option`'ı güncellenir, yeni satır açılmaz — `polls/views.py: vote()`. Detay sayfasında sonuç satırlarının tamamı, poll açık olduğu sürece tıklanabilir oy formuna dönüşür (`poll.can_vote` = `not poll.is_closed`); seçili olan "✓" ile işaretlenir.
2. **Sonuçlar oy verdikten sonra** görünür (yüzde + oy sayısı + çubuk grafik). Anket sahibi sonuçları her zaman görür.
3. **Ana sayfa/profilde anketler oy verilebilir şekilde görünmez** — seçenekler nötr (yüzdesiz) renkli barlar olarak önizlenir, oy vermek için anket başlığına tıklanıp detay sayfasına gidilir. Oy verme butonları (aktif) sadece **detay sayfasında**, oy vermemiş/sahip olmayan kullanıcıya gösterilir.
4. Toplam oy sayısı her durumda kartta görünür ("23 oy"). Ana sayfada kartlar 640px üzeri genişliklerde 2 sütun, mobilde tek sütun.
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
| `/parola-sifirla/` | Parola sıfırlama isteği (e-posta gir) | Herkes |
| `/parola-sifirla/<uidb64>/<token>/` | Sıfırlama bağlantısı → yeni parola formu | Herkes (geçerli token ile) |
| `/admin/` | Django admin | Süper kullanıcı |

**Navbar:** Logo "Kararsızım" · "Anket Aç" butonu (misafirse giriş sayfasına götürür) · Giriş/Kayıt veya kullanıcı adı + Çıkış. Üye girişliyse `@kullaniciadi` artık kendi profil sayfasına (`/u/<username>/`) bağlantı — tıklayınca kullanıcı kendi açtığı anketleri görür (`templates/partials/navbar.html`).

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

**Hedef kitle:** Gençler. **His:** Modern, "yeni nesil ürün" hissi — cam efektli (glassmorphism) kartlar, yumuşak aurora arka plan, mikro-animasyonlar. Ağır/karmaşık değil; tek bir framework/build adımı eklemeden saf CSS+JS ile elde edildi.
**Ana fikir:** Açık lavanta arka plan üzerinde yavaşça kayan bulanık renkli "aurora" lekeleri (`body::before`), kartlar yarı saydam + `backdrop-filter: blur()` (glassmorphism); canlı ama dengeli bir aksan paleti; büyük/kalın başlıklar, sayısal/meta bilgiler monospace fontla ayrışır. Bu yön, `https://kararsizim.vercel.app` referans alınarak ama daha rafine bir palet ve tipografiyle (Faz 6 sonrası bir oturumda) uygulandı — eski sıcak krem/mor palet (Plus Jakarta Sans) tamamen bunun yerini aldı; sonraki bir oturumda kullanıcı "çok sade, daha modern/şık olsun" isteyince glassmorphism + aurora arka plan + mikro-animasyonlar (bkz. aşağıdaki "Mikro-animasyonlar" bölümü) eklendi.

### Renk paleti (CSS değişkenleri, `:root` içinde)
```css
:root {
  --bg: #F5F4FB;           /* soft lavanta-beyaz arka plan */
  --surface: #FFFFFF;      /* kartlar */
  --text: #15132A;         /* koyu lacivert-siyah */
  --text-muted: #6B6880;
  --border: #E6E3F2;

  --primary: #5B4FE8;      /* canlı indigo-mor — ana butonlar, logo */
  --primary-hover: #4C3FE0;
  --primary-tint: #ECE9FF;

  /* 5 seçenek rengi (max 5 seçenek = her birine bir renk) */
  --opt-1: #5B4FE8;  --opt-1-tint: #ECE9FF;  /* indigo-mor */
  --opt-2: #F0397A;  --opt-2-tint: #FFE3EE;  /* pembe */
  --opt-3: #FFB224;  --opt-3-tint: #FFF2D9;  /* amber */
  --opt-4: #11C98E;  --opt-4-tint: #D8F7EC;  /* yeşil */
  --opt-5: #FF6B4A;  --opt-5-tint: #FFE3DA;  /* mercan */

  --radius: 16px;
  --radius-sm: 10px;
  --shadow: 0 1px 2px rgba(21, 19, 42, 0.04), 0 10px 24px rgba(21, 19, 42, 0.05);
}
```
- Her seçenek `order` değerine göre kendi rengini alır (`[data-order="N"]` → `--opt-color`/`--opt-tint`): oy verme butonu ve sonuç satırı sol kenarlıkla (`border-left: 4px solid var(--opt-color)`) renklenir; dolgu değil, vurgu çizgisi kullanılır.
- **Birleşik sonuç çubuğu (`poll-chart`):** her anketin üstünde, tüm seçeneklerin tek bir ince (10px) çubukta segment segment yan yana dizildiği özet görünüm var (`static/partials/poll_options.html`). Sonuç görünürken segment genişlikleri gerçek yüzdeye göre (AJAX oy sonrası animasyonla genişler); ana sayfa/profil önizlemesinde (`poll-chart-neutral`) segmentler eşit genişlikte ve soluk — oy oranını ele vermez (bkz. bölüm 5 kural 3).
- **Durum etiketi (`poll.status_label`):** sonuçlar görünür olduğunda oy dağılımına göre "Karar net" / "Az farkla önde" / "Kalabalık da kararsız" metni gösterilir (`views.py` içindeki `_status_label` fonksiyonu; AJAX oy yanıtında da `status_label` alanıyla döner). Oy yoksa gösterilmez.

### Tipografi
- Google Fonts: **"Space Grotesk"** (400, 500, 700) — başlıklar ve gövde metni.
- **"JetBrains Mono"** (400, 500, 600) — zaman damgaları, oy sayıları, karakter sayaçları, rozetler gibi tüm sayısal/meta metinler (`--font-mono`).
- Soru başlıkları kalın (700), büyük; gövde 16px.

### Bileşen tarzı
- Yuvarlak köşeler (`--radius` kartlarda, `--radius-sm` input/satırlarda), hafif gölge (`--shadow`), ince `--border` kenarlık, bol boşluk.
- Ana butonlar hap şeklinde (`border-radius: 999px`); oy verme/sonuç satırları ise daha az yuvarlak (`--radius-sm`) ve sol renkli kenarlıklı.
- Sekmeler (`.tabs`) ve aktif kategori pilleri artı koyu lacivert dolgu (`var(--text)`) ile vurgulanır (mora kıyasla daha nötr/modern).
- Anket kartı: üstte yazar (`@kullaniciadi` + köşeleri yuvarlatılmış kare baş harf avatarı) ve zaman, kategori/kapanış rozetleri, ortada soru, altta birleşik sonuç çubuğu + seçenekler, en altta oy sayısı.
- Ana sayfada üç sekme: **"En yeni" / "Popüler" / "Kapananlar"** (süresi dolmuş anketler, `?sekme=kapandi`).
- Boş durumlar dostça: "Henüz anket yok. İlk kararsızlığı sen paylaş! 🤔" (Kapananlar sekmesinde: "Henüz kapanan anket yok.").
- **Mobil öncelikli** tasarım; mobilde tek sütun, ana sayfada 640px üzerinde kartlar 2 sütun.
- **Erişilebilirlik**: yeterli kontrast, odak (focus) halkaları görünür (`select` dahil), butonlar gerçek `<button>`. Skip link (`.skip-link`, `#main-content`, `top: -80px` ile tamamen ekran dışı). Sonuç satırları `role="progressbar"` + `aria-valuenow/min/max` ile duyuruluyor (birleşik `poll-chart` segmentleri salt dekoratif, `aria-hidden="true"`); seçili seçenek rengin yanında metinle de ("✓") belirtiliyor — bilgi asla sadece renge dayanmamalı (renk körlüğü). Toast mesajları `role="status" aria-live="polite"`. Dekoratif emojiler `aria-hidden="true"`. Aktif sekme/kategori `aria-current`.
- **ARIA/yapı senkronizasyonu:** `templates/partials/poll_options.html` ile `static/js/main.js`teki `renderPollResults` birebir aynı DOM yapısını (poll-chart + durum etiketi + poll-results) üretir; birini değiştirince diğerini güncellemeyi unutma (bkz. dosyanın başındaki mimari özet notu).

### Mikro-animasyonlar ve glassmorphism (son oturumda eklendi)
- **Aurora arka plan:** `body::before`, sabit konumlu (`position: fixed`), 4 bulanık `radial-gradient` lekesinden oluşan, 28 saniyede bir yönünü değiştiren çok yavaş bir `translate/scale` animasyonuyla (`aurora-drift`) kayan dekoratif katman. `z-index: -1`, tıklamaları engellemez.
- **Glassmorphism:** `.poll-card`, `.card` ve `.navbar` artık `var(--glass-bg)` (yarı saydam beyaz) + `backdrop-filter: blur(16px) saturate(160%)` kullanıyor; navbar ayrıca `position: sticky`. `--shadow`/`--shadow-lg` indigo tonlu (nötr siyah değil).
- **Kart giriş animasyonu:** `.poll-grid .poll-card` sayfa yüklenince `card-in` keyframe'iyle (opacity+translateY) içeri süzülüyor, ilk 6 kart için `nth-child` ile kademeli gecikme var. Hover'da kart hafifçe yukarı kalkıyor (`translateY(-4px)` + `--shadow-lg`).
- **Durum etiketi** (`poll.status_label`) göründüğünde `label-pop` ile hafif büyüyerek beliriyor.
- **Konfeti:** Oy verme/değiştirme başarılı olunca (`static/js/main.js: burstConfetti`), tıklanan butonun üzerinden `--opt-N` renklerinde küçük parçacıklar saçılıyor (saf DOM+CSS keyframe, kütüphane yok). `setupVoteForms`'ta `renderPollResults` çağrılmadan **önce** tetiklenir, çünkü `renderPollResults` orijinal butonu DOM'dan kaldırıyor (`getBoundingClientRect()` o an, buton hâlâ DOM'dayken alınmalı).
- **Avatar** artık düz tint değil, `--primary`→`--opt-2` gradient + beyaz yazı.
- **`prefers-reduced-motion: reduce`** saygı görüyor: aurora, kart giriş animasyonu ve durum etiketi animasyonu kapanıyor; konfeti JS tarafında `window.matchMedia` ile tamamen atlanıyor (DOM'a hiç eklenmiyor).

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

### E-posta (parola sıfırlama)
- `EMAIL_BACKEND` tanımlı değilse Django'nun konsol backend'i kullanılır — yerelde e-posta gerçekten gönderilmez, `runserver` çıktısına yazdırılır.
- Prod'da **Resend**'in SMTP relay'i kullanılıyor: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=smtp.resend.com` (varsayılan), `EMAIL_HOST_USER=resend` (varsayılan), `EMAIL_HOST_PASSWORD=<Resend API anahtarı>`. Bu üçü + `DEFAULT_FROM_EMAIL` Vercel ortam değişkenlerine eklendi (Faz 6 sonrası bir oturumda).
- ⚠️ **Şu an sandbox modundayız** (Resend'de alan adı doğrulanmadı): `DEFAULT_FROM_EMAIL=Kararsızım <onboarding@resend.dev>` sadece Resend hesap sahibinin kendi (hesabı açarken kullandığı) adresine gönderebilir — **gerçek kullanıcılara parola sıfırlama e-postası gitmiyor**. `templates/accounts/password_reset_form.html`'de bunu açıklayan bir uyarı kutusu var. Gerçek kullanıcılara göndermek için: bir domain sahiplenip Resend panelinden doğrulamak (DNS'e SPF/DKIM kaydı eklemek) ve `DEFAULT_FROM_EMAIL`'i o domain'den bir adrese çevirmek gerekiyor — kullanıcı bunu bilerek erteledi.

### Supabase bağlantı notları
- Vercel serverless olduğu için Supabase'in **pooler (transaction mode, port 6543)** bağlantı adresi kullanılır.
- Transaction pooler ile uyum için `settings.py`:
  ```python
  DATABASES = {"default": dj_database_url.config(conn_max_age=0, ssl_require=True)}
  DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
  ```
- **Migration'lar Vercel build'inde değil, yerelden çalıştırılır** (`python manage.py migrate`), tercihen session pooler / direkt bağlantı (port 5432) ile.
- Supabase Data API (PostgREST) bu projede kullanılmıyor. Tabloların anon anahtarla dışarı açılmaması için Supabase panelinden Data API'yi kapat veya `public` şemasını açık şemalardan çıkar.

### 10.1 Prod Dağıtım Durumu (Faz 5 sonrası — yeni oturum için önemli)

- **Canlı URL:** https://kararsizim-pink.vercel.app
- **Supabase projesi:** `kararsizim` (ref `ldlvktmqdrkvygplbdmb`, Frankfurt/eu-central-1, ücretsiz katman). Data API kapatıldı (RLS uyarısı bu yüzden yok, tekrar kontrol etmeye gerek yok).
- **Vercel projesi:** `kararsizim`, GitHub reposu `EmirGecgin/Undecided` (private) içe aktarıldı ve bağlandı.
- **Prod admin hesabı:** `admin@example.com`. Şifre önceki oturumda kullanıcıyla paylaşıldı; unutulduysa yerelden prod'a bağlanıp (`DATABASE_URL`'i geçici olarak prod'a çevirip) `python manage.py changepassword admin` ile sıfırlanabilir.
- ⚠️ **Supabase pooler host'unun küme numarasını (`aws-0`, `aws-1`, ...) ASLA tahmin etme.** Bölgeden türetilemez; yanlış tahmin "tenant or user not found" hatası verir (bir kez yaşandı, saatler kaybedildi). Dashboard → proje → **Connect** butonu → "Transaction pooler" sekmesinden bağlantı dizesini birebir kopyala. Bu proje için doğru değer: `aws-1-eu-central-1.pooler.supabase.com` (yani `.env.example`'daki `aws-0` örneği sadece şablon, gerçek değer değil).
- ⚠️ **Vercel'in otomatik deploy'u tutarsız çalışıyor.** Proje Vercel MCP ile (CLI/UI akışı değil) kurulduğu için GitHub push'ları bazen otomatik deploy tetikliyor, bazen tetiklemiyor (sebep netleşmedi). Push sonrası birkaç saniye bekleyip `list_deployments` (projectId: `prj_3AzPjZC3RHl7KVFWUOmpBQUDvgSk`) ile son commit'in deploy edilip edilmediğini kontrol et; edilmediyse `create_deployment` ile elle tetikle: `gitSource: {"type": "github", "org": "EmirGecgin", "repo": "Undecided", "ref": "main"}`, `project: "kararsizim"`, `target: "production"`.
- Yeni bir Poll alanı/migration eklediğinde: hem yerelden `DATABASE_URL`'i geçici olarak prod'a çevirip `migrate` çalıştırmayı hem de sonra tekrar yorum satırı yapıp SQLite'a dönmeyi unutma (bir kez Faz 6'da migration prod'a uygulanmadan deploy edilip fark edilmişti).
- İlk kurulumda Vercel proje ayarlarındaki varsayılan **Deployment Protection (SSO)** kapatıldı — açıksa site misafirlere kapalı kalır.

---

## 11. Güvenlik Kontrol Listesi
- Prod'da `DEBUG=False`, `SECRET_KEY` ortam değişkeninden.
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` prod'da açık.
- Tüm POST formlarında CSRF koruması; fetch isteklerinde `X-CSRFToken`.
- Kullanıcı girdisi şablonlarda otomatik escape edilir; `|safe` kullanılmaz.
- Silme işlemi yalnızca sahibine; başkası denerse `403`.
- Django'nun parola doğrulayıcıları açık (en az 8 karakter).
- Özel hata sayfaları: `templates/404.html`, `templates/403.html` (sitenin tasarımıyla, `base.html` üzerinden) ve `templates/500.html` (**bağımsız**, context'e/`base.html`'e güvenmeden, inline CSS — 500 anında context processor'ların kendisi patlamış olabilir). `DEBUG=False` iken Django bunları otomatik kullanır, ekstra view/URL tanımı gerekmez.

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
- [x] Oy değiştirme / geri alma
- [x] Anket bitiş süresi ("24 saat sonra kapanır") ve kapanmış anket rozeti
- [x] Arama ve kategoriler/etiketler (yemek, eğlence, alışveriş…)
- Anket paylaşım linki ve Open Graph önizlemesi
- [x] Kötüye kullanım önlemleri: oy ve anket açma için hız sınırı (`config/ratelimit.py`). IP hash ve raporlama butonu hâlâ yok.
- [x] Misafir oyunu giriş sonrası hesaba bağlama
- [x] Parola sıfırlama (Resend SMTP ile e-posta gönderimi, bkz. bölüm 10)
- Karanlık mod
- Yorumlar ("Ben olsam sinemaya giderdim çünkü…")

---

## 13. Kodlama Kuralları
- Kod ve değişken adları **İngilizce**, kullanıcıya görünen metinler **Türkçe**.
- Function-based veya class-based view serbest, ama proje içinde tutarlı ol.
- N+1 sorgularından kaçın: listelerde `select_related("author")`, `prefetch_related("options")`, oy sayıları için `annotate(Count(...))`.
- Her fazın sonunda `python manage.py test` ve `python manage.py check --deploy` (Faz 5'te) çalıştır.
- Yeni bir bağımlılık eklemeden önce gerçekten gerekli olduğundan emin ol; prototip sade kalmalı.
