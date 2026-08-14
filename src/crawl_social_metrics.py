"""
crawl_social_metrics.py
========================
Crawl chỉ số kinh tế-xã hội của 5 quận NYC từ nguồn thực:
  - Census ACS 2023 API (pop_density, avg_income)
  - OpenStreetMap Overpass API (parks, hospitals, supermarkets → amenity_score)
  - Geography constants (dist_center, gdp_local — ổn định theo địa lý)

Output: data/raw/social_metrics.json
Pipeline: crawl_social_metrics.py → etl_to_sqlite.py → dim_social_metrics

Chạy: python src/crawl_social_metrics.py
"""

import os, sys, json, time, urllib.request, urllib.parse
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR    = os.path.join(BASE_DIR, 'data', 'raw')
OUTPUT     = os.path.join(RAW_DIR, 'social_metrics.json')
os.makedirs(RAW_DIR, exist_ok=True)

# ── Hằng số địa lý (ổn định, không cần crawl) ────────────────────────────────
# dist_center: khoảng cách trung bình tới Financial District Manhattan (km)
# gdp_local:   tỷ trọng đóng góp GDP NYC (ước tính từ NYC Comptroller 2023)
GEO_CONSTANTS = {
    '1': {'dist_center': 2.0,  'gdp_local': 6.8},   # Manhattan
    '2': {'dist_center': 4.5,  'gdp_local': 5.9},   # Bronx
    '3': {'dist_center': 8.0,  'gdp_local': 5.3},   # Brooklyn
    '4': {'dist_center': 11.5, 'gdp_local': 5.0},   # Queens
    '5': {'dist_center': 16.0, 'gdp_local': 6.2},   # Staten Island
}

# ── Mapping ──────────────────────────────────────────────────────────────────
BOROUGH_ID = {
    'Manhattan': '1', 'Bronx': '2', 'Brooklyn': '3',
    'Queens': '4', 'Staten Island': '5',
}
# FIPS county code trong New York State (FIPS state = 36)
COUNTY_FIPS = {
    'Manhattan':     '061',   # New York County
    'Bronx':         '005',   # Bronx County
    'Brooklyn':      '047',   # Kings County
    'Queens':        '081',   # Queens County
    'Staten Island': '085',   # Richmond County
}
# Bounding box [s, w, n, e] cho Overpass API
BOROUGH_BBOX = {
    'Manhattan':     (40.6960, -74.0203, 40.8820, -73.9067),
    'Bronx':         (40.7850, -73.9332, 40.9176, -73.7654),
    'Brooklyn':      (40.5707, -74.0421, 40.7395, -73.8334),
    'Queens':        (40.5431, -73.9625, 40.8007, -73.7004),
    'Staten Island': (40.4774, -74.2591, 40.6501, -74.0340),
}

# Fallback nếu API down (giá trị đã dùng trước đó)
FALLBACK = {
    '1': {'pop_density': 72000, 'avg_income': 88000},
    '2': {'pop_density': 36000, 'avg_income': 64000},
    '3': {'pop_density': 38000, 'avg_income': 59000},
    '4': {'pop_density': 19000, 'avg_income': 55000},
    '5': {'pop_density':  9000, 'avg_income': 74000},
}


# ═══════════════════════════════════════════════════════════════════
# BƯỚC 1: Census ACS 2023 — pop_density & avg_income
# ═══════════════════════════════════════════════════════════════════
def fetch_census(borough_name: str, fips: str) -> dict:
    """
    Lấy dân số (B01003_001E) và thu nhập trung vị hộ gia đình (B19013_001E)
    từ Census ACS 5-Year 2023.
    API công khai, không cần key.
    """
    url = (
        f"https://api.census.gov/data/2023/acs/acs5"
        f"?get=B01003_001E,B19013_001E,ALAND"
        f"&for=county:{fips}&in=state:36"
    )
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'research-bot/1.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            # data[0] = header, data[1] = values
            population = int(data[1][0])
            income     = int(data[1][1])
            land_sqm   = int(data[1][2])   # diện tích đất (m²)
            land_sqkm  = land_sqm / 1_000_000
            density    = round(population / land_sqkm) if land_sqkm > 0 else 0
            print(f"  [Census OK] {borough_name}: pop={population:,} | density={density:,}/km² | income=${income:,}")
            return {'pop_density': density, 'avg_income': income, 'source_census': 'ACS 2023'}
    except Exception as e:
        bid = BOROUGH_ID[borough_name]
        fb  = FALLBACK[bid]
        print(f"  [Census FALLBACK] {borough_name}: {e}")
        return {'pop_density': fb['pop_density'], 'avg_income': fb['avg_income'], 'source_census': 'fallback'}


# ═══════════════════════════════════════════════════════════════════
# BƯỚC 2: OpenStreetMap Overpass — amenity counts → amenity_score
# ═══════════════════════════════════════════════════════════════════
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'

OSM_QUERIES = {
    'parks':        'node["leisure"="park"]({s},{w},{n},{e}); way["leisure"="park"]({s},{w},{n},{e});',
    'hospitals':    'node["amenity"="hospital"]({s},{w},{n},{e}); node["amenity"="clinic"]({s},{w},{n},{e});',
    'supermarkets': 'node["shop"="supermarket"]({s},{w},{n},{e}); way["shop"="supermarket"]({s},{w},{n},{e});',
}

def fetch_osm_counts(borough_name: str) -> dict:
    """Lấy số lượng tiện ích từ OSM Overpass → tính amenity_score (1-10)."""
    s, w, n, e = BOROUGH_BBOX[borough_name]
    counts = {}
    for key, q_body in OSM_QUERIES.items():
        q = f"[out:json][timeout:30];\n({q_body.format(s=s,w=w,n=n,e=e)});\nout count;"
        data = urllib.parse.urlencode({'data': q}).encode('utf-8')
        req  = urllib.request.Request(OVERPASS_URL, data=data,
                                      headers={'User-Agent': 'research-bot/1.0'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                resp  = json.loads(r.read().decode())
                count = int(resp['elements'][0]['tags']['total'])
                counts[key] = count
                print(f"    [OSM OK] {borough_name} {key}: {count}")
        except Exception as ex:
            counts[key] = 0
            print(f"    [OSM WARN] {borough_name} {key}: {ex}")
        time.sleep(2)   # lịch sự với Overpass API

    # Công thức amenity_score: kết hợp 3 loại tiện ích, chuẩn hoá về thang 1-10
    raw = (counts.get('parks', 0) * 0.04
         + counts.get('hospitals', 0) * 0.3
         + counts.get('supermarkets', 0) * 0.15)
    score = round(min(max(raw, 1.0), 10.0), 4)
    print(f"  [OSM Score] {borough_name}: parks={counts.get('parks')} "
          f"hosp={counts.get('hospitals')} super={counts.get('supermarkets')} → score={score}")
    return {**counts, 'amenity_score': score, 'source_osm': 'OpenStreetMap Overpass'}


# ═══════════════════════════════════════════════════════════════════
# MAIN: Ghép tất cả → lưu JSON
# ═══════════════════════════════════════════════════════════════════
def run():
    print()
    print("=" * 60)
    print("  CRAWL SOCIAL METRICS — 5 Quận NYC")
    print(f"  Output: {OUTPUT}")
    print("=" * 60)

    result = {}
    for borough, bid in BOROUGH_ID.items():
        print(f"\n[{bid}] {borough}")

        # Census
        census = fetch_census(borough, COUNTY_FIPS[borough])

        # OSM
        print(f"  Fetching OSM data for {borough}...")
        osm = fetch_osm_counts(borough)

        # Ghép
        geo = GEO_CONSTANTS[bid]
        result[bid] = {
            'borough_id':     int(bid),
            'borough_name':   borough,
            'pop_density':    census['pop_density'],
            'avg_income':     census['avg_income'],
            'gdp_local':      geo['gdp_local'],
            'dist_center':    geo['dist_center'],
            'amenity_score':  osm['amenity_score'],
            'num_parks':      osm.get('parks', 0),
            'num_hospitals':  osm.get('hospitals', 0),
            'num_supermarkets': osm.get('supermarkets', 0),
            'source_census':  census.get('source_census'),
            'source_osm':     osm.get('source_osm'),
            'last_updated':   datetime.now().strftime('%Y-%m-%d %H:%M'),
        }

    # Lưu file
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("  BÁO CÁO TỔNG HỢP CRAWL DỮ LIỆU XÃ HỘI (SOCIAL METRICS)")
    print("=" * 80)
    print(f"  {'Quận':<15} | {'Dân số':>10} | {'Thu nhập':>10} | {'Công viên':>10} | {'Siêu thị':>9} | {'Bệnh viện':>10} | {'Điểm Tiện ích':>13}")
    print("-" * 80)
    
    for bid, data in result.items():
        boro  = data['borough_name']
        pop   = f"{data['pop_density']:,.0f}" if data['source_census'] != 'fallback' else "LỖI (Dùng cũ)"
        inc   = f"${data['avg_income']:,.0f}" if data['source_census'] != 'fallback' else "LỖI"
        park  = str(data['num_parks']) if data['num_parks'] > 0 else "LỖI (0)"
        sup   = str(data['num_supermarkets']) if data['num_supermarkets'] > 0 else "LỖI (0)"
        hosp  = str(data['num_hospitals']) if data['num_hospitals'] > 0 else "LỖI (0)"
        score = f"{data['amenity_score']:.1f}/10"
        print(f"  {boro:<15} | {pop:>10} | {inc:>10} | {park:>10} | {sup:>9} | {hosp:>10} | {score:>13}")
        
    print("=" * 80)
    print(f"  ✅ Đã lưu đè file JSON thành công tại: {OUTPUT}")
    print(f"  👉 (Nếu có bất kỳ cột nào hiện 'LỖI' hoặc '0', hãy bật VPN/Cloudflare và chạy lại)")
    print("=" * 80)
    print()

if __name__ == '__main__':
    run()
