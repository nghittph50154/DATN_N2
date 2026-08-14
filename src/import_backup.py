import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_JSON = os.path.join(BASE_DIR, 'data', 'raw', 'dl_bo_sung', 'nyc_project', 'nyc_combined_data.json')
OUTPUT_JSON = os.path.join(BASE_DIR, 'data', 'raw', 'social_metrics.json')

BOROUGH_MAP = {
    'Manhattan': '1', 
    'The Bronx': '2', 'Bronx': '2',
    'Brooklyn': '3',
    'Queens': '4', 
    'Staten Island': '5'
}

# Diện tích đất xấp xỉ (km2) để tính mật độ
AREA_SQKM = {
    '1': 59.1,
    '2': 109.0,
    '3': 183.4,
    '4': 281.5,
    '5': 151.5
}

GEO_CONSTANTS = {
    '1': {'dist_center': 2.0,  'gdp_local': 6.8},
    '2': {'dist_center': 4.5,  'gdp_local': 5.9},
    '3': {'dist_center': 8.0,  'gdp_local': 5.3},
    '4': {'dist_center': 11.5, 'gdp_local': 5.0},
    '5': {'dist_center': 16.0, 'gdp_local': 6.2},
}

def clean_number(text):
    if isinstance(text, (int, float)): return text
    text = str(text).replace(',', '').replace('USD', '').replace('$', '').strip()
    match = re.search(r'[\d\.]+', text)
    if match:
        return float(match.group())
    return 0

with open(BACKUP_JSON, 'r', encoding='utf-8') as f:
    backup_data = json.load(f)

result = {}
for row in backup_data:
    boro_name = row.get('Quận')
    if boro_name == 'The Bronx': boro_name = 'Bronx'
    
    bid = BOROUGH_MAP.get(boro_name)
    if not bid: continue
    
    pop = clean_number(row.get('Dân_số', 0))
    area = AREA_SQKM[bid]
    density = round(pop / area) if area > 0 else 0
    
    income = clean_number(row.get('Thu_nhập_trung_vị', 0))
    
    parks = int(clean_number(row.get('Số_công_viên', 0)))
    hospitals = int(clean_number(row.get('Số_bệnh_viện_phòng_khám', 0)))
    supers = int(clean_number(row.get('Số_siêu_thị', 0)))
    
    # Tính amenity_score
    raw_score = (parks * 0.04 + hospitals * 0.3 + supers * 0.15)
    # Vì dữ liệu thật khá lớn, ta scale lại cho hợp lý (vd Manhattan raw = ~174)
    # Điểm cao nhất cho Manhattan là 10
    score = round(min(max(raw_score / 17.5, 1.0), 10.0), 4)
    if boro_name == 'Manhattan': score = 10.0

    geo = GEO_CONSTANTS[bid]
    
    result[bid] = {
        'borough_id': int(bid),
        'borough_name': boro_name,
        'pop_density': density,
        'avg_income': income,
        'gdp_local': geo['gdp_local'],
        'dist_center': geo['dist_center'],
        'amenity_score': score,
        'num_parks': parks,
        'num_hospitals': hospitals,
        'num_supermarkets': supers,
        'source_census': 'Backup Data (Census 2023)',
        'source_osm': 'Backup Data (OSM 2025)',
        'last_updated': '2026-07-29 (From Backup)'
    }

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=4, ensure_ascii=False)

print(f"Đã chuyển đổi thành công từ file backup sang {OUTPUT_JSON}")
