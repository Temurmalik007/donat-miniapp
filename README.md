# Donat Mini App (Telegram)

O'yinlar uchun donat (UC, Olmos, Stars, Premium va h.k.) sotadigan **Telegram Mini App** + bot.

## Qanday ishlaydi

- Mijoz botni ochadi → **"Do'konni ochish"** tugmasini bosadi → Mini App (web-ilova) ochiladi.
- Mini App'da: balans, kategoriyalar (o'yinlar), mahsulotlar, tarix, sozlamalar.
- **Hisobni to'ldirish** — bot chatida (`/topup`), chunki chek-rasm yuborish kerak. Admin tasdiqlagach, balans **avtomatik** to'ldiriladi.
- Balans yetarli bo'lsa, mijoz mini app'da mahsulot tanlab, **bir tugma bosib darhol xarid qiladi** — pul avtomatik yechiladi, admin'ga xabar boradi.
- Admin buyurtmani "Bajarildi" deb belgilaydi (UC/olmos hali qo'lda yuboriladi, chunki ta'minotchi API'si yo'q — keyinchalik ulab beriladi).

## 1-qadam: Botni yaratish

1. Telegram'da **@BotFather** ga yozing → `/newbot` → nom bering.
2. Sizga `BOT_TOKEN` beriladi — saqlab qo'ying.
3. O'z Telegram ID'ingizni bilish uchun **@userinfobot** ga yozing.

## 2-qadam: Kodni GitHub'ga yuklash

1. [github.com](https://github.com) da yangi repository yarating (masalan `donat-miniapp`).
2. Shu papkadagi barcha fayllarni o'sha repo'ga yuklang (GitHub Desktop yoki `git` orqali).

## 3-qadam: Render'da bepul joylashtirish

1. [render.com](https://render.com) da ro'yxatdan o'ting (GitHub bilan kirish qulay).
2. **New → Web Service** tanlang, GitHub repo'ingizni ulang.
3. Sozlamalar:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
4. **Environment Variables** bo'limiga quyidagilarni qo'shing (`.env.example` dagi kabi):
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `CLICK_CARD`, `PAYME_CARD`, `CARD_OWNER`
   - `WEBAPP_URL` — bu qadamda hali bilmaysiz, keyin to'ldirasiz
5. **Create Web Service** bosing. Bir necha daqiqada sizga manzil beriladi, masalan:
   `https://donat-miniapp.onrender.com`
6. Endi `WEBAPP_URL` environment variable'ni shu manzilga o'zgartiring (Render panelida) va **Manual Deploy → Redeploy** qiling.

> ⚠️ Bepul Render xizmati 15 daqiqa harakatsizlikdan keyin "uxlab qoladi" va birinchi so'rovda 30-60 soniya sekin ochiladi. Doimiy tez ishlashi uchun kelajakda pullik reja ($7/oy) yoki boshqa hosting (VPS) kerak bo'ladi.

## 4-qadam: Botga Mini App tugmasini ulash

Bot kodi (`bot_handlers.py`) `WEBAPP_URL`ni avtomatik ishlatadi — Render'da shu o'zgaruvchini to'g'ri qo'ygan bo'lsangiz, bot `/start` bosilganda "🛍 Do'konni ochish" tugmasi chiqadi va shu manzilni ochadi. Qo'shimcha sozlash shart emas.

## 5-qadam: Katalog to'ldirish

Botda (admin sifatida) yozing:

- `/admin` — admin panel
- `/add_category` — kategoriya qo'shish (nomi, emoji, badge, Player ID kerakmi)
- `/add_product` — kategoriyaga mahsulot qo'shish (nomi, narxi)

Qo'shgan kategoriya/mahsulotlar darhol Mini App'da ko'rinadi.

## Lokal test qilish (kompyuteringizda)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # so'ng .env faylni to'ldiring
python app.py
```

> Diqqat: Mini App faqat **https** manzilda ishlaydi, shuning uchun uni to'liq sinash uchun baribir Render'ga (yoki boshqa https hosting'ga) joylashtirish kerak bo'ladi. Lokal rejimda faqat bot va API xatolarini tekshirishingiz mumkin.

## Fayl tuzilishi

```
donat_miniapp/
├── app.py              # FastAPI server: Mini App + REST API + botni ishga tushiradi
├── bot_handlers.py      # bot: /start, /topup, admin buyruqlari, tasdiqlash tugmalari
├── database.py          # SQLite: users (balans), categories, products, orders, topups
├── webapp_auth.py        # Telegram Mini App initData'ni xavfsiz tekshirish
├── config.py            # .env dan sozlamalarni o'qiydi
├── states.py            # bot suhbat holatlari (FSM)
└── static/
    ├── index.html        # Mini App interfeysi
    ├── style.css          # dizayn
    └── app.js             # frontend mantiq (API bilan ishlash)
```

## Keyingi qadamlar (tavsiya)

1. **Click/Payme merchant** olsangiz — chek-screenshot o'rniga to'g'ridan-to'g'ri API orqali to'lovni avtomatlashtirib beraman.
2. **UC/Olmos ta'minotchisi (reseller API)** topsangiz — "Bajarildi" bosqichini ham botning o'zi avtomatik bajaradigan qilib beraman.
3. **Telegram Stars** — bot o'zining rasmiy Stars to'lov tizimidan foydalanishi mumkin (alohida so'rasangiz ulab beraman) — bu to'liq avtomatik ishlaydi.
