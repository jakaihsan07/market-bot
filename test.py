import requests
import certifi

BASES = [
    "https://data-api.binance.vision",
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://api4.binance.com",
]

for base in BASES:
    url = base + "/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "limit": 5
    }

    try:
        r = requests.get(
            url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=(10, 30),
            verify=certifi.where()
        )

        print(base, "=>", r.status_code)

        if r.status_code == 200:
            print("BERHASIL:", r.text[:100])
            break

    except Exception as e:
        print(base, "=> ERROR:", e)