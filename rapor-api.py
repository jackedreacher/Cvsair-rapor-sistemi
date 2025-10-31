#!/usr/bin/env python3
# pip install requests pandas

import os
import requests
import pandas as pd

# Basit .env yükleyici: .env dosyası varsa key=value satırlarını ortam değişkenlerine ekler
def _load_dotenv_if_present(path: str = ".env"):
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Mevcut ortamı ezmemek için sadece yoksa set et
                        if key and (key not in os.environ):
                            os.environ[key] = value
    except Exception:
        pass

_load_dotenv_if_present()

# Ortam değişkenleri (repo genelinde aynı isimler kullanılıyor)
REMOTE_API_BASE = os.getenv("REMOTE_API_BASE", "http://localhost:5047").strip()
REMOTE_ORDERS_PATH = os.getenv("REMOTE_ORDERS_PATH", "/api/Genel/getSIPARISLERCVS").strip()
REMOTE_BEARER_TOKEN = os.getenv("REMOTE_BEARER_TOKEN", "").strip()

# Tarih aralığı (gerekirse env ile yönetilebilir)
BAS_TAR = os.getenv("BAS_TAR", "2025-01-01")
BIT_TAR = os.getenv("BIT_TAR", "2025-12-31")

def get_siparisler():
    url = f"{REMOTE_API_BASE}{REMOTE_ORDERS_PATH}"
    headers = {"Authorization": f"Bearer {REMOTE_BEARER_TOKEN}"} if REMOTE_BEARER_TOKEN else {}
    params = {"basTar": BAS_TAR, "bitTar": BIT_TAR}

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()          # list[dict]

def main():
    raw = get_siparisler()
    df  = pd.DataFrame(raw)

    # 12 sütun seç / yeniden adlandır
    df = df[["sip_tarih","cari_unvan","sip_stok_sormerk","sormerk_adi",
             "sip_miktar","sip_teslim_miktar","sip_tutar","sip_net_tutar",
             "sip_cins","proje_adi"]].copy()

    df.rename(columns={
        "sip_tarih"        : "siparis_tarihi",
        "cari_unvan"       : "cari_isim",
        "sip_stok_sormerk" : "sormerk_kod",
        "sormerk_adi"      : "sormerk_ad",
        "sip_miktar"       : "miktar",
        "sip_teslim_miktar": "tamamlanan_miktar",
        "sip_tutar"        : "tutar_brut",
        "sip_net_tutar"    : "tutar_net",
        "sip_cins"         : "doviz_cinsi",
        "proje_adi"        : "proje_ad"
    }, inplace=True)

    # 11-12. sütunlar
    df["kalan_miktar"]   = df["miktar"] - df["tamamlanan_miktar"]
    df["kalan_net_tutar"] = df.apply(
        lambda r: round(r["tutar_net"] * r["kalan_miktar"] / r["miktar"], 2)
                  if r["miktar"] else 0.0, axis=1)

    print(df.to_string(index=False))
    # df.to_excel("siparis_raporu.xlsx", index=False)  # istersen

if __name__ == "__main__":
    main()