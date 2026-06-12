import os
import time
from datetime import datetime

import requests
import certifi


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Token belum diisi. Set TELEGRAM_BOT_TOKEN dulu.")


# =========================
# TELEGRAM
# =========================
def telegram_api(method, payload=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(
        url,
        json=payload or {},
        timeout=(10, 60),
        verify=certifi.where()
    )
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text):
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })


# =========================
# HTTP HELPER
# =========================
def get_json(url, params=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Connection": "close"
    }

    last_error = None

    for _ in range(3):
        try:
            r = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=(10, 30),
                verify=certifi.where()
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_error = e
            time.sleep(2)

    raise RuntimeError(last_error)

def get_coinbase_btc_klines(interval="15m", limit=120):
    """
    Ambil candle BTC dari Coinbase Exchange.
    15m = 900 detik
    1h = 3600 detik
    """
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

    if interval == "1h":
        granularity = 3600
    else:
        granularity = 900

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Connection": "close"
    }

    params = {
        "granularity": granularity
    }

    r = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=(10, 30),
        verify=certifi.where()
    )
    r.raise_for_status()

    data = r.json()

    candles = []

    # Format Coinbase:
    # [time, low, high, open, close, volume]
    for row in data:
        candles.append({
            "open_time": int(row[0]) * 1000,
            "open": float(row[3]),
            "high": float(row[2]),
            "low": float(row[1]),
            "close": float(row[4]),
            "volume": float(row[5]),
            "close_time": int(row[0]) * 1000,
            "is_closed": True
        })

    candles = sorted(candles, key=lambda x: x["open_time"])

    return candles[-limit:]


def get_btc_klines(interval="15m", limit=120):
    """
    Ambil candle BTC.
    Sekarang pakai Coinbase dulu karena Binance/Yahoo error di koneksi kamu.
    """
    try:
        candles = get_coinbase_btc_klines(interval, limit)
        return candles, "Coinbase BTC-USD"
    except Exception as e:
        raise RuntimeError(f"Gagal ambil candle BTC dari Coinbase: {e}")


def get_btc_long_short():
    """
    Ambil retail long-short dari Binance Futures.
    Kalau gagal, return None.
    """
    url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"

    params = {
        "symbol": "BTCUSDT",
        "period": "15m",
        "limit": 1
    }

    try:
        data = get_json(url, params)
        if not data:
            return None

        last = data[-1]

        return {
            "long_pct": float(last["longAccount"]) * 100,
            "short_pct": float(last["shortAccount"]) * 100,
            "ratio": float(last["longShortRatio"])
        }

    except Exception:
        return None


# =========================
# ANALISIS
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


def retail_score(sentiment):
    if not sentiment:
        return 0, "Retail long-short tidak terbaca"

    long_pct = sentiment["long_pct"]
    short_pct = sentiment["short_pct"]

    # Kontrarian ringan:
    # retail terlalu long = rawan bearish
    # retail terlalu short = rawan bullish
    if long_pct >= 60:
        return -20, f"Retail dominan long {long_pct:.1f}% vs short {short_pct:.1f}%"

    if short_pct >= 60:
        return 20, f"Retail dominan short {short_pct:.1f}% vs long {long_pct:.1f}%"

    if long_pct >= 55:
        return -10, f"Retail agak long {long_pct:.1f}% vs short {short_pct:.1f}%"

    if short_pct >= 55:
        return 10, f"Retail agak short {short_pct:.1f}% vs long {long_pct:.1f}%"

    return 0, f"Retail seimbang: long {long_pct:.1f}% vs short {short_pct:.1f}%"


def classify(score):
    if score >= 60:
        return "CENDERUNG BULLISH KUAT"
    if score >= 25:
        return "CENDERUNG BULLISH"
    if score <= -60:
        return "CENDERUNG BEARISH KUAT"
    if score <= -25:
        return "CENDERUNG BEARISH"
    return "SIDEWAYS / NETRAL"


def analyze_btc():
    candles_m15, source_m15 = get_btc_klines("15m", 120)
    candles_h1, source_h1 = get_btc_klines("1h", 120)
    sentiment = get_btc_long_short()

    if len(candles_m15) < 30 or len(candles_h1) < 30:
        return "Data BTC belum cukup untuk analisis."

    score = 0
    reasons = []

    s, r = trend_score(candles_m15, 30, "M15")
    score += s
    reasons.append(r)

    s, r = trend_score(candles_h1, 25, "H1")
    score += s
    reasons.append(r)

    s, r = volume_score(candles_m15)
    score += s
    reasons.append(r)

    s, r = retail_score(sentiment)
    score += s
    reasons.append(r)

    last = candles_m15[-1]
    time_text = datetime.fromtimestamp(last["open_time"] / 1000).strftime("%Y-%m-%d %H:%M")

    if sentiment:
        retail_text = f"Long {sentiment['long_pct']:.1f}% | Short {sentiment['short_pct']:.1f}%"
    else:
        retail_text = "Tidak terbaca"

    return f"""
<b>BTC/USDT — {classify(score)}</b>

TF utama: M15
Filter: H1
Skor: {score}
Harga close M15 terakhir: {last['close']}
Candle M15 terakhir: {time_text}

Sumber candle: {source_m15}
Retail: {retail_text}

<b>Alasan:</b>
- {reasons[0]}
- {reasons[1]}
- {reasons[2]}
- {reasons[3]}

<b>Catatan aman:</b>
Ini bukan sinyal entry langsung. Tunggu candle M15 close dan jangan entry kalau harga sudah terlalu jauh.
""".strip()


# =========================
# BOT LOOP
# =========================
print("BTC bot berjalan...")

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

            if text == "/start":
                send_message(
                    chat_id,
                    "BTC bot aktif.\n\nKetik /btc untuk analisis BTC M15."
                )

            elif text in ["/btc", "btc", "bitcoin"]:
                try:
                    result = analyze_btc()
                    send_message(chat_id, result)
                except Exception as e:
                    send_message(chat_id, f"Error saat analisis BTC: {e}")

            else:
                send_message(chat_id, "Ketik /btc untuk analisis BTC.")

    except Exception as e:
        print("Loop error:", e)
        time.sleep(5)