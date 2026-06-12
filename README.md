# 📈 Multi-Market Crypto & Forex Telegram Bot

Bot Telegram otomatis berbasis Python yang berfungsi untuk melakukan *scanning* dan analisis teknikal kilat pada pasar **Crypto (Binance Spot)** serta **Forex & Komoditas (Twelve Data)**. Bot ini menggunakan indikator *Exponential Moving Average* (EMA), analisis volume, serta bias kontrarian sentimen ritel pada *Timeframe* M15 dengan filter H1.

---

## 🚀 Fitur Utama

* **Multi-Market Support:** Mendukung aset Crypto populer (BTC, ETH, SOL, XRP, dll) melalui Binance API, serta Forex & Komoditas (XAU/USD, EUR/USD, GBP/USD, WTI Crude Oil) melalui Twelve Data API.
* **Dual Timeframe Analysis:** Mengombinasikan tren indikator EMA Fast (9) dan EMA Slow (21) pada *Timeframe* M15 dan H1 untuk menentukan kekuatan arah pasar.
* **Volume Spike Detector:** Mendeteksi lonjakan volume transaksi di atas rata-rata 20 candle terakhir untuk menyaring konfirmasi *breakout* (Khusus market Crypto).
* **Contrarian Retail Sentiment:** Membaca data rasio *Long/Short* trader ritel dari pasar berjangka Bybit & Binance Futures secara *real-time* sebagai filter bias pembalikan arah pasar (Khusus market Crypto).
* **Auto Chunk Message:** Mengamankan pengiriman pesan dengan memecah output secara otomatis jika teks melebihi batas maksimal karakter dari Telegram API (4096 karakter).

---


