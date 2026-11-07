# Madina — Telegram AI yordamchi

Madina Telegramda matn va ovozli xabarlarni qabul qiladigan shaxsiy AI yordamchidir. Kod Python’da yozilgan; suhbat tarixi SQLite’da saqlanadi, AI xizmati OpenRouter orqali ulanadi.

## Muhim: maxfiy kalitlar

BotFather tokeni va OpenRouter kalitini chatga yoki GitHub kodiga yubormang. Ularni faqat o'zingizning kompyuteringizdagi `.env` faylida saqlang. Bu repoda `.env` Git’ga kiritilmaydi. Avval chatga yuborilgan token/kalitlarni bekor qilib, yangisini oling.

## Ishga tushirish (Windows)

1. Python 3.11 yoki undan yangi versiyasini o'rnating: https://www.python.org/downloads/ (o'rnatishda **Add Python to PATH** ni belgilang).
2. GitHub repozitoriysini kompyuteringizga yuklab, papkani oching: https://github.com/zohidalijonov0600-e330/madina-ai-agent
3. Papka ichida `setup_windows.bat` faylini ikki marta bosing. U virtual muhit va paketlarni o'rnatadi.
4. `.env.example` faylidan nusxa olib, nusxasini `.env` deb nomlang.
5. `.env`-ийг Notepad’da ochib, Telegram token, OpenRouter kalit va Telegram ID-гаа kiriting. Qiymatlar misol matni emas, haqiqiy yangi credential bo'lishi kerak.
6. `run_windows.bat` файлын ikki marta bosing. Qora oynada `Application started` chiqsa, bot ishga tushgan bo'ladi. Oynani yopmang.
7. Telegramda botingizni ochib, `/start` yuboring.

## macOS / Linux

Python 3.11+, FFmpeg o'rnating (Linux: `sudo apt install ffmpeg`; macOS: `brew install ffmpeg`), terminalda loyiha papkasiga o'tib bajaring:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env ichidagi qiymatlarni tahrirlang, so'ng:
python main.py
```

Voice transkripsiyasiga OpenRouter’dagi audio transcription endpoint va `STT_MODEL` ishlatiladi. Ovozli javob TTS model tanlanıp `.env`-ში `TTS_MODEL` to'ldirilgandan keyin yoqiladi; hozircha matnli javob ishlashi uchun TTS bo'sh qoldirilishi mumkin. Model nomlari va mavjudligi provayderda o'zgarishi mumkin.

## Telegram ID va token olish

- Token: Telegram’da `@BotFather` bilan suhbat ochib, `/newbot` yo'riqnomasini bajaring. Tokenni `.env` ichida saqlang.
- O'zingizning Telegram raqamli ID’ingizni aniqlash uchun `@userinfobot` kabi ishonchli ID botidan so'rang va `OWNER_TELEGRAM_ID` qatoriga yozing. ID maxfiy token emas, lekin ommaga ulashmaslik ma'qul.

## Bot buyruqlari

`/start`, `/help`, `/voice_on`, `/voice_off`, `/text`, `/language uz|ru|en`, `/clear`, `/status`.

Bot faqat `OWNER_TELEGRAM_ID` ko'rsatgan odamning shaxsiy chatida javob beradi. `.env` yoki API kalitlarini GitHub’ga commit qilmang. Botni 24/7 ishlatish uchun doimiy ishlaydigan kompyuter/VPS va maxfiy muhit o'zgaruvchilari kerak; ushbu repo o'zi hostingni ta'minlamaydi.
