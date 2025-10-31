#!/usr/bin/env python3
"""
Flask API Server for CVS Air Dashboard
Integrates with rapor-api.py to serve data to the frontend
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import pandas as pd
import csv
import os
import re
from datetime import datetime, timedelta
import unicodedata
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Environment-based security settings
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', '').strip()
API_TOKEN_ENV = os.getenv('API_TOKEN', '').strip()

app = Flask(__name__, static_folder='.')
# CORS based on FRONTEND_ORIGIN env
if FRONTEND_ORIGIN:
    CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})
    logger.info(f"CORS origin set to {FRONTEND_ORIGIN}")
else:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    logger.warning("FRONTEND_ORIGIN not set; allowing all origins for /api/* in development")

# Uzak API yapılandırması (ENV üzerinden; hardcoded secret yok)
REMOTE_API_BASE = os.getenv('REMOTE_API_BASE', 'http://localhost:5047').strip()
REMOTE_ORDERS_PATH = os.getenv('REMOTE_ORDERS_PATH', '/api/Genel/getSIPARISLERCVS').strip()
REMOTE_BEARER_TOKEN = os.getenv('REMOTE_BEARER_TOKEN', '').strip()

def get_siparisler(bas_tar=None, bit_tar=None, base_url=None):
    """
    Uzaktan API'den siparişleri getirir; isteğe bağlı tarih aralığı.
    Tanı amaçlı base_url geçici override'ını destekler (query: baseUrl).
    """
    # Default date range if not provided - yearly data
    if not bas_tar:
        bas_tar = "2025-01-01"
    if not bit_tar:
        bit_tar = "2025-12-31"

    base = (base_url or REMOTE_API_BASE)
    url = f"{base}{REMOTE_ORDERS_PATH}"
    headers = {"Authorization": f"Bearer {REMOTE_BEARER_TOKEN}"} if REMOTE_BEARER_TOKEN else {}
    params = {"basTar": bas_tar, "bitTar": bit_tar}
    if not REMOTE_BEARER_TOKEN:
        logger.warning("REMOTE_BEARER_TOKEN not set; calling remote API without Authorization header")

    try:
        logger.info(f"Attempting external API GET {url} params={params}")
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        logger.info(f"External API response status: {resp.status_code}")
        if resp.status_code == 404:
            # Content could be HTML; avoid log flooding
            logger.error(f"External API 404 Not Found: {resp.url}")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        # Log detailed HTTP error
        logger.error(f"HTTP error from external API: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise

# CSV yardımcıları

def _parse_number(val):
    if val is None:
        return 0.0
    s = str(val).strip().replace('"', '')
    if s == '':
        return 0.0
    # Binlik ayırıcıları kaldır (ör: 46,565.11)
    s = s.replace(',', '')
    try:
        return float(s)
    except Exception:
        return 0.0


def _parse_int(val):
    try:
        return int(round(_parse_number(val)))
    except Exception:
        return 0


def _parse_date_iso(date_str):
    date_str = (date_str or '').strip()
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return dt.date().isoformat()
    except Exception:
        return None


def read_orders_from_csv(csv_path):
    """Read orders from a CSV file and map to dashboard schema.
    Expects headers like: SİPARİŞ TARİHİ, CARİ İSMİ, Sorumluluk Merkezi Adı, MİKTAR, TAMAMLANAN MİKTAR, TUTAR, NET TUTAR, DOVİZ CİNSİ, KALAN MİKTAR, KALAN SİPARİŞ NET TUTAR
    Skips summary rows without a valid date.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV dosyası bulunamadı: {csv_path}")

    results = []
    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sip_tarih = (row.get("SİPARİŞ TARİHİ") or '').strip()
            iso_date = _parse_date_iso(sip_tarih)
            if not iso_date:
                # Tarih yoksa veya toplam satırıysa atla
                continue

            cari = (row.get("CARİ İSMİ") or '').strip()
            sormerk_adi = (row.get("Sorumluluk Merkezi Adı") or '').strip()
            doviz = (row.get("DOVİZ CİNSİ") or '').strip()

            miktar = _parse_int(row.get("MİKTAR"))
            tamamlanan = _parse_int(row.get("TAMAMLANAN MİKTAR"))
            kalan_miktar = _parse_int(row.get("KALAN MİKTAR"))
            if kalan_miktar == 0 and (miktar or tamamlanan):
                kalan_miktar = max(miktar - tamamlanan, 0)

            # Kalan Net Tutar bazı dosyalarda "NET TUTAR" olarak gelebilir
            kalan_net_tutar = _parse_number(
                row.get("KALAN SİPARİŞ NET TUTAR")
                or row.get("NET TUTAR")
                or row.get("TUTAR")
            )

            results.append({
                'SİPARİŞ TARİHİ': sip_tarih,
                'CARİ İSMİ': cari,
                'Sorumluluk Merkezi Adı': sormerk_adi,
                'MİKTAR': miktar,
                'KALAN SİPARİŞ NET TUTAR': kalan_net_tutar,
                'DOVİZ CİNSİ': doviz,
                'KALAN MİKTAR': kalan_miktar,
                'date': iso_date
            })

    return results

def process_data(raw_data):
    """
    Normalize remote API data to match dashboard expectations.
    Handles alternate field names, type conversions, and date parsing.
    """
    # Unwrap common response containers
    data = raw_data
    if isinstance(raw_data, dict):
        for key in ['data', 'Data', 'result', 'Result', 'results']:
            if key in raw_data and isinstance(raw_data[key], (list, tuple)):
                data = raw_data[key]
                break

    df = pd.DataFrame(data)
    if df.empty:
        return []

    # Helper: normalize keys for matching
    def norm(s):
        try:
            s = unicodedata.normalize('NFKD', str(s))
            s = s.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            s = str(s)
        return re.sub(r'[^a-z0-9]+', '', s.lower())

    cols_norm = {norm(c): c for c in df.columns}

    # Target fields and candidate names (normalized)
    target_candidates = {
        'SİPARİŞ TARİHİ': ['tarih','sip_tarih','siparistarihi','siparistarih','siparis_tarih','sip_tar'],
        'CARİ İSMİ': ['cari','cari_unvan','cariunvan','cariismi','cari_isim','cariadi','cari_ad'],
        'Sorumluluk Merkezi Adı': ['srmad','sormerk_adi','sorumlulukmerkeziadi','sorumlulukmerkezi','sip_stok_sormerk','sormerk'],
        'Sorumluluk Merkezi Kodu': ['srmkod','sormerk_kod','sorumlulukmerkezikodu','sormerk'],
        'MİKTAR': ['miktar','sip_miktar','adet','quantity'],
        'TAMAMLANAN MİKTAR': ['teslim','sip_teslim_miktar','teslim_miktar','tamamlanan_miktar','teslimmiktar','delivered'],
        'KALAN MİKTAR': ['kalanmik','kalan_miktar','kalansiparis','remaining'],
        'TUTAR': ['tutar','sip_tutar','brut_tutar','bruttutar','gross'],
        'NET TUTAR': ['nettutar','net_tutar','sip_net_tutar'],
        'KALAN SİPARİŞ NET TUTAR': ['kalannet','kalan_net','kalansiparisnettutar','sip_net_tutar','net_tutar','nettutar','kalantutar'],
        'DOVİZ CİNSİ': ['doviz','sip_cins','doviz_cinsi','currency'],
        'PROJE': ['proje','project','proje_adi','projeadi'],
        'DURUM': ['durum','status','siparis_durum','siparisdurum']
    }

    # Build canonical dataframe
    out = pd.DataFrame()
    for target, cands in target_candidates.items():
        found = None
        for cand in cands:
            if cand in cols_norm:
                found = cols_norm[cand]
                break
        if found is None:
            # If original (already canonical) exists, use it
            if target in df.columns:
                found = target
        if found is not None:
            out[target] = df[found]
        else:
            out[target] = ''

    # Numeric conversions using existing helpers
    for num_col in ['MİKTAR', 'TAMAMLANAN MİKTAR', 'KALAN MİKTAR', 'TUTAR', 'NET TUTAR', 'KALAN SİPARİŞ NET TUTAR']:
        if num_col in out.columns:
            out[num_col] = out[num_col].apply(_parse_number)

    # Derived column - only calculate if not already provided
    if 'KALAN MİKTAR' not in out.columns or out['KALAN MİKTAR'].isna().all():
        out['KALAN MİKTAR'] = out['MİKTAR'] - out['TAMAMLANAN MİKTAR']

    # Date normalization to ISO (server-side convenience)
    def parse_any_date(s):
        iso = _parse_date_iso(s)
        if iso:
            return iso
        try:
            dt = pd.to_datetime(s, errors='coerce')
            if pd.notna(dt):
                return dt.date().isoformat()
        except Exception:
            pass
        return None

    out['date'] = out['SİPARİŞ TARİHİ'].apply(parse_any_date)

    # Drop rows without valid date if data clearly represents orders
    # Keep if there is currency summary without date (optional)
    filtered = out[(out['date'].notnull()) | ((out['DOVİZ CİNSİ'] != '') & (out['KALAN SİPARİŞ NET TUTAR'] > 0))]

    records = filtered.to_dict('records')
    if not records:
        logger.warning('Processed data is empty after normalization; returning original rows as fallback.')
        records = out.to_dict('records')
    return records

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH_ENV = os.getenv('CSV_PATH', '').strip()

def resolve_csv_path():
    p = CSV_PATH_ENV if CSV_PATH_ENV else 'orders.csv'
    if not os.path.isabs(p):
        p = os.path.join(BASE_DIR, p)
    return p

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """
    API endpoint to get orders data
    Supports optional date range parameters
    Falls back to CSV data if API is unavailable
    """
    # Optional API token guard
    if API_TOKEN_ENV:
        provided = request.headers.get('X-API-Token') or request.args.get('api_token')
        if provided != API_TOKEN_ENV:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    try:
        # Get date parameters from query string
        bas_tar = request.args.get('startDate')
        bit_tar = request.args.get('endDate')
        base_url_override = request.args.get('baseUrl')

        try:
            # Try to fetch raw data from the API
            raw_data = get_siparisler(bas_tar, bit_tar, base_url_override)

            # Process and transform the data
            processed_data = process_data(raw_data)

            logger.info(f"Successfully processed {len(processed_data)} orders from API")

            return jsonify({
                'success': True,
                'data': processed_data,
                'count': len(processed_data),
                'date_range': {
                    'start': bas_tar,
                    'end': bit_tar
                }
            })

        except Exception as api_error:
            logger.warning(f"API request failed: {str(api_error)}")
            logger.info("Falling back to CSV data...")

            try:
                csv_path = resolve_csv_path()
                logger.info(f"CSV fallback using path: {csv_path}")
                csv_data = read_orders_from_csv(csv_path)
                logger.info(f"Returning {len(csv_data)} orders from CSV fallback")
                return jsonify({
                    'success': True,
                    'data': csv_data,
                    'count': len(csv_data),
                    'note': 'CSV fallback - Original API unavailable',
                    'date_range': {
                        'start': bas_tar,
                        'end': bit_tar
                    }
                })
            except Exception as csv_error:
                logger.error(f"CSV fallback failed: {csv_error}")
                return jsonify({
                    'success': True,
                    'data': [],
                    'count': 0,
                    'note': 'No data: API and CSV unavailable',
                    'date_range': {
                        'start': bas_tar,
                        'end': bit_tar
                    }
                })

    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'remote_base': REMOTE_API_BASE,
        'remote_orders_path': REMOTE_ORDERS_PATH,
        'remote_url': f"{REMOTE_API_BASE}{REMOTE_ORDERS_PATH}",
        'csv_path': resolve_csv_path(),
        'frontend_origin': FRONTEND_ORIGIN,
        'auth_required': bool(API_TOKEN_ENV)
    })

@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """Get sample data for testing"""
    try:
        sample_data = [
            {
                'SİPARİŞ TARİHİ': '18.08.2025',
                'CARİ İSMİ': 'DFN MALATYA 1262',
                'Sorumluluk Merkezi Adı': 'DFN MALATYA 1262',
                'MİKTAR': 45000,
                'KALAN SİPARİŞ NET TUTAR': 45000,
                'DOVİZ CİNSİ': 'TL',
                'KALAN MİKTAR': 45000,
                'date': '2025-08-18'
            },
            {
                'SİPARİŞ TARİHİ': '19.08.2025',
                'CARİ İSMİ': 'DFN MALATYA 700',
                'Sorumluluk Merkezi Adı': 'DFN MALATYA 700',
                'MİKTAR': 23000,
                'KALAN SİPARİŞ NET TUTAR': 23000,
                'DOVİZ CİNSİ': 'TL',
                'KALAN MİKTAR': 23000,
                'date': '2025-08-19'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': sample_data,
            'count': len(sample_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting sample data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/<path:filename>')
def serve_static_files(filename):
    """Serve static files (HTML, CSS, JS, etc.)"""
    try:
        return send_from_directory('.', filename)
    except Exception as e:
        logger.error(f"Error serving file {filename}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'File not found: {filename}'
        }), 404

@app.route('/')
def serve_index():
    """Serve the main dashboard"""
    try:
        return send_from_directory('.', 'deneme.html')
    except Exception as e:
        logger.error(f"Error serving index: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Index file not found'
        }), 404

if __name__ == '__main__':
    print("Starting CVS Air API Server...")
    print(f"Remote API: {REMOTE_API_BASE}{REMOTE_ORDERS_PATH}")
    print("Available endpoints:")
    print("  GET /api/orders - Get orders data")
    print("  GET /api/health - Health check")
    print("  GET /api/sample-data - Sample data for testing")
    
    app.run(host='0.0.0.0', port=8000, debug=True)