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
REMOTE_API_BASE = os.getenv("REMOTE_API_BASE", "http://85.153.155.153:5047").strip()
REMOTE_ORDERS_PATH = os.getenv("REMOTE_ORDERS_PATH", "/api/Listeler/listeSIPARISLERCVS").strip()
REMOTE_BEARER_TOKEN = os.getenv("REMOTE_BEARER_TOKEN", "").strip()

# Paginasyon parametreleri (env ile yönetilebilir)
PAGE_INDEX = int(os.getenv("PAGE_INDEX", "0") or 0)
PAGE_SIZE  = int(os.getenv("PAGE_SIZE", "500") or 500)

def get_siparisler():
    url = f"{REMOTE_API_BASE}{REMOTE_ORDERS_PATH}"
    headers = {"Authorization": f"Bearer {REMOTE_BEARER_TOKEN}"} if REMOTE_BEARER_TOKEN else {}
    params = {"pageIndex": PAGE_INDEX, "pageSize": PAGE_SIZE}

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()          # list[dict]

def main():
    raw = get_siparisler()
    df  = pd.DataFrame(raw)

    # Beklenen kolonlar varsa yeniden adlandır; yoksa olduğu gibi yazdır
    expected_cols = {"sip_tarih": "siparis_tarihi",
                     "cari_unvan": "cari_isim",
                     "sip_stok_sormerk": "sormerk_kod",
                     "sormerk_adi": "sormerk_ad",
                     "sip_miktar": "miktar",
                     "sip_teslim_miktar": "tamamlanan_miktar",
                     "sip_tutar": "tutar_brut",
                     "sip_net_tutar": "tutar_net",
                     "sip_cins": "doviz_cinsi",
                     "proje_adi": "proje_ad"}
    present = [c for c in expected_cols.keys() if c in df.columns]
    if present:
        df = df[present].copy()
        df.rename(columns=expected_cols, inplace=True)
    else:
        # Kolonlar beklenenden farklıysa ham çıktıyı yazdır
        print(df.to_string(index=False))
        return

    # 11-12. sütunlar
    if "miktar" in df.columns and "tamamlanan_miktar" in df.columns:
        df["kalan_miktar"] = df["miktar"].fillna(0) - df["tamamlanan_miktar"].fillna(0)
    else:
        df["kalan_miktar"] = 0
    if all(col in df.columns for col in ["tutar_net","kalan_miktar","miktar"]):
        def _calc(r):
            try:
                return round(float(r["tutar_net"]) * float(r["kalan_miktar"]) / float(r["miktar"]) , 2) if float(r["miktar"]) else 0.0
            except Exception:
                return 0.0
        df["kalan_net_tutar"] = df.apply(_calc, axis=1)
    else:
        df["kalan_net_tutar"] = 0.0

    print(df.to_string(index=False))
    # df.to_excel("siparis_raporu.xlsx", index=False)  # istersen

if __name__ == "__main__":
    main()