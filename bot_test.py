from builtins import int
import os
import time
from datetime import datetime

import requests
import certifi
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is United and Running!"

def run_web():
    # Render menyediakan port otomatis di environment variable mereka
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Jalankan server web di background thread agar tidak mengganggu looping bot Telegram kamu
threading.Thread(target=run_web).start()

# --- DI BAWAH INI ADALAH KODE UTAMA LOOPING BOT TELEGRAM KAMU YANG SUDAH ADA ---
# (Contoh: bot.polling() atau while True getUpdates kamu)
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("Token Telegram belum diisi. Cek file .env kamu.")
if not TWELVE_DATA_API_KEY:
    raise RuntimeError("API Key Twelve Data belum diisi. Cek file .env kamu.")


# =========================
# SETTING MARKET
# =========================
CRYPTO_ALIASES = {
    "btc": "BTCUSDT",
    "bitcoin": "BTCUSDT",
    "eth": "ETHUSDT",
    "ethereum": "ETHUSDT",
    "sol": "SOLUSDT",
    "solana": "SOLUSDT",
    "xrp": "XRPUSDT",
    "ripple": "XRPUSDT",
    "bnb": "BNBUSDT",
    "doge": "DOGEUSDT",
    "dogecoin": "DOGEUSDT",
    "ada": "ADAUSDT",
    "cardano": "ADAUSDT",
    "avax": "AVAXUSDT",
    "link": "LINKUSDT",
    "matic": "MATICUSDT",
    "pol": "POLUSDT",
    "trx": "TRXUSDT",
    "ton": "TONUSDT",
    "dot": "DOTUSDT",
    "ltc": "LTCUSDT",
    "shib": "SHIBUSDT",
}

# Mapping instrumen Forex & Komoditas untuk Twelve Data
FX_COMM_ALIASES = {
    "eurusd": "EUR/USD",
    "gbpusd": "GBP/USD",
    "usdjpy": "USD/JPY",
    "audusd": "AUD/USD",
    "usdcad": "USD/CAD",
    "xauusd": "XAU/USD",  # Emas
    "gold": "XAU/USD",
    "xagusd": "XAG/USD",  # Perak
    "silver": "XAG/USD",
    "wti": "CL",          # Crude Oil
    "brent": "BZ",        # Brent Oil
}


# =========================
# TELEGRAM
# =========================
def telegram_api(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        r = requests.post(
            url,
            json=payload or {},
            timeout=(10, 60),
            verify=certifi.where()
        )
        return r.json()
    except Exception as e:
        print("TELEGRAM ERROR:", e)
        return {}


def send_message(chat_id, text):
    max_len = 3900
    parts = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    for part in parts:
        telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": part
        })


def menu_text():
    return (
        "Bot Multi-Market Aktif ✅\n\n"
        "Command Utama Crypto:\n"
        "/btc, /eth, /sol, /xrp, /bnb, /doge\n\n"
        "Command Utama Forex & Komoditas:\n"
        "/gold = Analisis Emas (XAU/USD)\n"
        "/eurusd = Analisis EUR/USD\n"
        "/gbpusd = Analisis GBP/USD\n"
        "/wti = Analisis Minyak Mentah\n\n"
        "Command fleksibel:\n"
        "/coin btc atau /coin gold\n\n"
        "Command lain:\n"
        "/list = daftar market yang tersedia\n\n"
        "Output bot hanya kecenderungan market, bukan sinyal entry langsung."
    )


# =========================
# HELPER SYMBOL
# =========================
def format_display_symbol(market_type, symbol):
    if market_type == "CRYPTO" and symbol.endswith("USDT"):
        return symbol.replace("USDT", "/USDT")
    return symbol


def normalize_symbol(text):
    t = text.lower().strip()

    if t.startswith("/"):
        t = t[1:]

    if t.startswith("coin "):
        t = t.replace("coin ", "", 1).strip()

    if t.endswith("usdt") and len(t) >= 6:
        return "CRYPTO", t.upper()

    if t in CRYPTO_ALIASES:
        return "CRYPTO", CRYPTO_ALIASES[t]
        
    if t in FX_COMM_ALIASES:
        return "FX_COMM", FX_COMM_ALIASES[t]

    return None, None


def supported_list_text():
    crypto_coins = sorted(set(CRYPTO_ALIASES.values()))
    crypto_text = ", ".join(c.replace("USDT", "/USDT") for c in crypto_coins)
    
    fx_comm_pairs = sorted(set(FX_COMM_ALIASES.values()))
    fx_text = ", ".join(fx_comm_pairs)

    return (
        "📋 DAFTAR MARKET YANG TERSEDIA\n\n"
        "🔹 CRYPTO (Binance):\n"
        f"{crypto_text}\n\n"
        "🔹 FOREX & KOMODITAS (Twelve Data):\n"
        f"{fx_text}\n\n"
        "💡 Contoh Penggunaan:\n"
        "/btc atau /coin btc\n"
        "/gold atau /coin eurusd"
    )


# =========================
# CANDLE DATA - BINANCE (CRYPTO)
# =========================
def get_binance_candles(symbol, interval="15m", limit=120):
    bases = [
        "https://data-api.binance.vision",
        "https://api.binance.com",
        "https://api-gcp.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api4.binance.com",
    ]
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    last_error = None

    for base in bases:
        url = base + "/api/v3/klines"
        try:
            r = requests.get(
                url, params=params, headers={"User-Agent": "Mozilla/5.0"}, 
                timeout=(10, 30), verify=certifi.where()
            )
            r.raise_for_status()
            data = r.json()

            candles = []
            now_ms = int(time.time() * 1000)
            for row in data:
                candles.append({
                    "open_time": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "close_time": int(row[6]),
                    "is_closed": now_ms > int(row[6])
                })
            closed_candles = [c for c in candles if c["is_closed"]]
            print(f"{symbol} candle berhasil dari:", base)
            return closed_candles[-limit:], base
        except Exception as e:
            last_error = e
            print("Gagal candle endpoint Binance:", base, "|", symbol, "|", e)
            time.sleep(1)

    raise RuntimeError(f"Semua endpoint Binance Spot gagal untuk {symbol}. Error terakhir: {last_error}")


# =========================
# CANDLE DATA - TWELVE DATA (FX & COMM)
# =========================
def get_twelve_data_candles(symbol, interval="15min", limit=120):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": limit,
        "apikey": TWELVE_DATA_API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=(10, 30), verify=certifi.where())
        data = r.json()
        
        if "values" not in data:
            raise RuntimeError(data.get("message", "Gagal mengambil data dari Twelve Data"))
            
        candles = []
        # Balik urutan karena Twelve Data mengembalikan data dari yang paling baru ke terlama
        for row in reversed(data["values"]):
            dt = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S" if len(row["datetime"]) > 10 else "%Y-%m-%d")
            ts = int(dt.timestamp() * 1000)
            vol = float(row.get("volume", 0)) if row.get("volume") else 0.0
            
            candles.append({
                "open_time": ts,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": vol
            })
        print(f"{symbol} candle berhasil dari Twelve Data")
        return candles, "Twelve Data API"
    except Exception as e:
        print(f"Twelve Data gagal untuk {symbol}: {e}")
        raise e


# =========================
# RETAIL SENTIMENT (CRYPTO ONLY)
# =========================
def get_bybit_retail_sentiment(symbol):
    url = "https://api.bybit.com/v5/market/account-ratio"
    params = {"category": "linear", "symbol": symbol, "period": "15min", "limit": 1}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 30), verify=certifi.where())
        r.raise_for_status()
        data = r.json()
        if data.get("retCode") != 0:
            raise RuntimeError(data.get("retMsg", "Bybit error"))
        items = data.get("result", {}).get("list", [])
        if not items:
            return None
        last = items[0]
        long_pct = float(last["buyRatio"]) * 100
        short_pct = float(last["sellRatio"]) * 100
        return {"long_pct": long_pct, "short_pct": short_pct, "ratio": long_pct / short_pct if short_pct else 0, "source": "Bybit Long/Short"}
    except Exception as e:
        print(f"Retail Bybit gagal untuk {symbol}:", e)
        return None


def get_binance_futures_retail_sentiment(symbol):
    bases = ["https://fapi.binance.com", "https://fapi1.binance.com", "https://fapi2.binance.com", "https://fapi3.binance.com", "https://fapi4.binance.com"]
    params = {"symbol": symbol, "period": "15m", "limit": 1}
    last_error = None
    for base in bases:
        url = base + "/futures/data/globalLongShortAccountRatio"
        try:
            r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 30), verify=certifi.where())
            r.raise_for_status()
            data = r.json()
            if not data: continue
            last = data[-1]
            long_pct = float(last["longAccount"]) * 100
            short_pct = float(last["shortAccount"]) * 100
            return {"long_pct": long_pct, "short_pct": short_pct, "ratio": float(last["longShortRatio"]), "source": "Binance Futures"}
        except Exception as e:
            last_error = e
            print("Gagal retail Binance:", base, "|", symbol, "|", e)
            time.sleep(1)
    print(f"Retail Binance gagal untuk {symbol}:", last_error)
    return None


def get_retail_sentiment(symbol):
    retail = get_bybit_retail_sentiment(symbol)
    if retail: return retail
    return get_binance_futures_retail_sentiment(symbol)


# =========================
# ANALISIS LOGIC
# =========================
def ema(values, period):
    if len(values) < period:
        return sum(values) / len(values)
    k = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = price * k + value * (1 - k)
    return value


def trend_score(candles, weight, label):
    closes = [c["close"] for c in candles]
    last_close = candles[-1]["close"]
    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)

    if last_close > ema_fast > ema_slow:
        return weight, f"{label}: trend naik"
    if last_close < ema_fast < ema_slow:
        return -weight, f"{label}: trend turun"
    return 0, f"{label}: belum searah / mixed"


def volume_score(candles):
    last = candles[-1]
    prev = candles[-21:-1]

    avg_volume = sum(c["volume"] for c in prev) / len(prev)
    vol_ratio = last["volume"] / avg_volume if avg_volume else 1

    candle_range = max(last["high"] - last["low"], 0.000001)
    body = abs(last["close"] - last["open"])
    body_ratio = body / candle_range

    bullish = last["close"] > last["open"]
    bearish = last["close"] < last["open"]

    if vol_ratio >= 1.25 and body_ratio >= 0.45 and bullish:
        return 20, f"Volume tinggi {vol_ratio:.2f}x rata-rata, candle bullish dominan"
    if vol_ratio >= 1.25 and body_ratio >= 0.45 and bearish:
        return -20, f"Volume tinggi {vol_ratio:.2f}x rata-rata, candle bearish dominan"
    if vol_ratio >= 1.25 and body_ratio < 0.35:
        return 0, f"Volume tinggi {vol_ratio:.2f}x rata-rata, tapi body kecil / belum jelas"
    if vol_ratio < 0.75:
        return 0, f"Volume rendah {vol_ratio:.2f}x rata-rata, arah belum kuat"
    return 0, f"Volume normal {vol_ratio:.2f}x rata-rata"


def retail_score_info(retail):
    if not retail:
        return 0, "Retail belum terbaca. Data tidak tersedia / koneksi gagal."

    long_pct = retail["long_pct"]
    short_pct = retail["short_pct"]
    source = retail.get("source", "Retail source")

    if long_pct > short_pct:
        text = f"Retail cenderung LONG: {long_pct:.1f}% long vs {short_pct:.1f}% short"
    elif short_pct > long_pct:
        text = f"Retail cenderung SHORT: {short_pct:.1f}% short vs {long_pct:.1f}% long"
    else:
        text = f"Retail seimbang: {long_pct:.1f}% long vs {short_pct:.1f}% short"

    text += f" | Sumber: {source}"

    if long_pct >= 60: return -20, text + " | Bias kontrarian: rawan bearish"
    if short_pct >= 60: return 20, text + " | Bias kontrarian: rawan bullish"
    if long_pct >= 55: return -10, text + " | Bias kontrarian ringan: rawan bearish"
    if short_pct >= 55: return 10, text + " | Bias kontrarian ringan: rawan bullish"
    return 0, text + " | Belum ekstrem"


def classify(score):
    if score >= 50: return "CENDERUNG BULLISH KUAT"
    if score >= 20: return "CENDERUNG BULLISH"
    if score <= -50: return "CENDERUNG BEARISH KUAT"
    if score <= -20: return "CENDERUNG BEARISH"
    return "SIDEWAYS / NETRAL"


# =========================
# CORE ENGINE MULTI-MARKET
# =========================
def analyze_market(market_type, symbol):
    # Mengambil data lilin berdasarkan tipe pasarnya
    if market_type == "CRYPTO":
        candles_m15, source_m15 = get_binance_candles(symbol, "15m", 120)
        candles_h1, source_h1 = get_binance_candles(symbol, "1h", 120)
        source_display = "Binance Spot"
    else:
        # Twelve data memakai parameter '15min' dan '1h'
        candles_m15, source_m15 = get_twelve_data_candles(symbol, "15min", 120)
        candles_h1, source_h1 = get_twelve_data_candles(symbol, "1h", 120)
        source_display = "Twelve Data"

    if len(candles_m15) < 30 or len(candles_h1) < 30:
        return f"Data {format_display_symbol(market_type, symbol)} belum cukup untuk analisis."

    score = 0
    reasons = []

    # 1. Skor Tren Berbasis EMA (M15 & H1)
    s, r = trend_score(candles_m15, 30, "M15")
    score += s
    reasons.append(r)

    s, r = trend_score(candles_h1, 25, "H1")
    score += s
    reasons.append(r)

    # 2. Skor Volume & Skor Sentimen Ritel (Hanya untuk Crypto)
    if market_type == "CRYPTO":
        s_vol, r_vol = volume_score(candles_m15)
        score += s_vol
        reasons.append(r_vol)

        retail = get_retail_sentiment(symbol)
        s_ret, retail_text = retail_score_info(retail)
        score += s_ret
        reasons.append(retail_text)
    else:
        # Definisikan info pelengkap kosong agar format cetakan teks tidak error
        r_vol = "Volume filter dilewati (Forex/Komoditas OTC)"
        retail_text = "Data Sentimen Ritel tidak tersedia untuk pasar Forex/Komoditas gratis"
        reasons.append(r_vol)
        reasons.append(retail_text)

    last = candles_m15[-1]
    time_text = datetime.fromtimestamp(last["open_time"] / 1000).strftime("%Y-%m-%d %H:%M")
    display_name = format_display_symbol(market_type, symbol)

    return f"""
{display_name} — {classify(score)}

Tipe Pasar: {market_type}
TF utama: M15 | Filter: H1
Skor Total: {score}
Harga close M15 terakhir: {last['close']}
Candle M15 terakhir: {time_text}
Sumber Data: {source_display}

Alasan:
- {reasons[0]}
- {reasons[1]}
- {reasons[2]}

Sentimen Pasar:
{retail_text}

Catatan aman:
Ini bukan sinyal entry langsung. Tunggu candle M15 close dan perhatikan spread saat rilis berita besar.
""".strip()


# =========================
# BOT LOOP
# =========================
print("Bot Multi-Market (Crypto, Forex, Commodities) berjalan...")

offset = None

while True:
    try:
        payload = {"timeout": 30}
        if offset is not None:
            payload["offset"] = offset

        updates = telegram_api("getUpdates", payload)

        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            message = update.get("message", {})
            chat = message.get("chat", {})
            chat_id = chat.get("id")
            text = message.get("text", "").lower().strip()

            if not chat_id:
                continue

            print("CHAT ID:", chat_id)
            print("TEXT:", text)

            if text == "/start":
                send_message(chat_id, menu_text())

            elif text == "/list":
                send_message(chat_id, supported_list_text())

            else:
                market_type, symbol = normalize_symbol(text)

                if symbol:
                    try:
                        result = analyze_market(market_type, symbol)
                        send_message(chat_id, result)
                    except Exception as e:
                        display_name = format_display_symbol(market_type, symbol)
                        send_message(chat_id, f"Error saat analisis {display_name}: {e}")
                else:
                    # Filter agar bot tidak merespons teks sembarang jika dalam grup besar
                    if text.startswith("/"):
                        send_message(chat_id, "Command belum dikenali. Ketik /list untuk lihat daftar market.")

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)