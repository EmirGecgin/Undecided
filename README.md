# Kararsızım

Kullanıcıların kararsız kaldıkları konularda diğer kullanıcılara anket açarak danıştığı bir web uygulaması.

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
