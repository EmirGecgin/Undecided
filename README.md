# Kararsızım

Kararsız kaldığın konularda başkalarına danışabildiğin, basit bir anket uygulaması.
*"Bugün sinemaya mı gitsem, restorana mı?"* gibi sorular için hızlıca anket aç; misafir ya da üye olarak oy ver, sonucu gör.

**🔗 Canlı demo:** **https://kararsizim-pink.vercel.app**

![Kararsızım ana sayfa ekran görüntüsü](docs/screenshot.jpg)

## Ne yapabilirsin?

- **Üye olmadan** anketleri görüntüle ve oy ver (çerez tabanlı misafir oyu, hesap gerekmez)
- Üye olup **kendi anketini aç** — 2 ile 5 arasında seçenek, isteğe bağlı kategori ve bitiş süresi
- Oy verdikten sonra (ya da anket sahibiysen her zaman) sonuçları **yüzde + oy sayısı + renkli çubuk** olarak gör
- Ana sayfada **"En yeni" / "Popüler" / "Kapananlar"** sekmeleri, kategori filtresi ve arama
- Kendi açtığın anketi istediğin zaman **silebilirsin**
- Tamamen **Türkçe arayüz**, mobil öncelikli tasarım

## Kullanılan teknolojiler

| Katman | Seçim |
|---|---|
| Backend | Django 5.2 (sunucu taraflı render, ekstra bir frontend framework yok) |
| Veritabanı | [Supabase](https://supabase.com) (yalnızca PostgreSQL olarak), yerelde SQLite |
| Frontend | Saf HTML + CSS + JavaScript (`templates/`, `static/`) |
| Yayın | [Vercel](https://vercel.com) |

Bilinçli olarak sade tutuldu: React/Vue, Tailwind, DRF, Celery, Redis, Docker gibi araçlar **kullanılmıyor**.

## Yerelde çalıştırma

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

`DATABASE_URL` tanımlı değilse proje otomatik olarak SQLite'a düşer, yani yukarıdaki adımlar dışında ekstra bir veritabanı kurulumu gerekmez.

Testleri çalıştırmak için:

```bash
python manage.py test
```

<details>
<summary><strong>Kendi Supabase + Vercel kopyana yayınlamak istersen</strong></summary>

### 1. Supabase'de proje aç
1. [supabase.com/dashboard](https://supabase.com/dashboard) üzerinden yeni bir proje oluştur.
2. Proje açıldıktan sonra üstteki **Connect** butonuna tıkla, **Transaction pooler** sekmesini seç ve bağlantı dizesini kopyala.
   - ⚠️ Host'taki küme numarasını (`aws-0`, `aws-1` vb.) tahmin etme — Connect penceresinden birebir kopyala, aksi halde "tenant or user not found" hatası alırsın.
3. Database şifresini aynı pencereden gör/sıfırla ve bağlantı dizesindeki `[YOUR-PASSWORD]` yerine yaz.

### 2. Yerelden migrate et
```bash
# .env dosyanda DATABASE_URL'i geçici olarak Supabase'e işaret ettir
# (session pooler veya direkt bağlantı, port 5432 tercih edilir)
python manage.py migrate
python manage.py createsuperuser
# işin bitince DATABASE_URL satırını tekrar yorum satırı yap (yerelde SQLite kullanmaya devam etmek için)
```

### 3. Vercel'de projeyi GitHub'dan içe aktar
1. Kod GitHub reposuna push edilmiş olmalı.
2. Vercel'de **Add New → Project** ile GitHub reposunu içe aktar. `manage.py` ve `config/wsgi.py` standart yapısı sayesinde ekstra yapılandırma (`vercel.json`, `/api` klasörü) gerekmez.
3. Proje ayarlarından **Settings → Deployment Protection**'ı kapat (aksi halde site herkese açık olmaz).
4. **Settings → Environment Variables** altına şunları ekle (Production + Preview):
   - `SECRET_KEY` — güçlü, rastgele bir değer (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
   - `DEBUG=False`
   - `ALLOWED_HOSTS=localhost,127.0.0.1,.vercel.app`
   - `CSRF_TRUSTED_ORIGINS=https://*.vercel.app`
   - `DATABASE_URL` — Supabase **Transaction pooler** bağlantı dizesi (port 6543)
5. Deploy et. Vercel `collectstatic`'i otomatik çalıştırıp statik dosyaları kendi CDN'inden sunar — `WhiteNoise` veya `vercel.json` gerekmez.

### 4. Güvenlik: Supabase Data API'yi kapat
Bu projede Supabase yalnızca ham Postgres veritabanı olarak kullanılıyor; Supabase'in kendi Data API'si (PostgREST/`anon` anahtarı) hiç kullanılmıyor. Tabloların `anon` anahtarla dışarıdan okunabilir/yazılabilir kalmaması için Supabase panelinden **Project Settings → Data API**'yi kapat (ya da `public` şemasını "Exposed schemas" listesinden çıkar).

</details>

---

Projenin tüm ürün kuralları, veri modeli, tasarım rehberi ve geliştirme fazları için [CLAUDE.md](CLAUDE.md) dosyasına bakabilirsin.
