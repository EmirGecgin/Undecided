# Kararsızım

Kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara anket açarak danıştığı bir web uygulaması.

**Canlı:** https://kararsizim-pink.vercel.app
**Admin:** https://kararsizim-pink.vercel.app/admin/

Detaylı proje rehberi için [CLAUDE.md](CLAUDE.md) dosyasına bakın.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

`DATABASE_URL` tanımlı değilse proje otomatik olarak SQLite kullanır.

## Supabase + Vercel'e Yayın

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
