"""
etl_to_sqlite.py
================
ETL Pipeline: Đọc file CSV đã làm sạch → Tách bảng → Ghi vào SQLite (Star-Schema)

Cấu trúc Star-Schema:
    dim_borough         (5 quận)
    dim_neighborhood    (các khu phố)
    dim_location        (địa chỉ, zipcode, block, lot)
    dim_property        (loại nhà, diện tích, năm xây)
    dim_social_metrics  (chỉ số kinh tế-xã hội theo quận)
    fact_sales          (giao dịch bất động sản - trung tâm)

Chạy:
    python src/etl_to_sqlite.py
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
import json
from datetime import datetime

# ── Cấu hình encoding UTF-8 trên Windows ─────────────────────────────────────
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ── Đường dẫn ─────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_CSV      = os.path.join(BASE_DIR, 'data', 'data clean', 'Dulieu_Cleaned.csv')
WAREHOUSE_DIR  = os.path.join(BASE_DIR, 'data', 'warehouse')
DB_PATH        = os.path.join(WAREHOUSE_DIR, 'nyc_warehouse.db')
RAW_DIR        = os.path.join(BASE_DIR, 'data', 'raw')
SOCIAL_JSON    = os.path.join(RAW_DIR, 'social_metrics.json')

# ── Hàm tiện ích ─────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{ts}] {msg}")


def safe_int(val, default=0):
    try:
        v = int(val)
        return v if not np.isnan(v) else default
    except Exception:
        return default


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 1: Load CSV sạch
# ═════════════════════════════════════════════════════════════════════════════
def load_clean_csv() -> pd.DataFrame:
    log(f"Đang đọc file CSV sạch: {os.path.basename(CLEAN_CSV)}")
    df = pd.read_csv(CLEAN_CSV, low_memory=False)
    log(f"  → Tải thành công: {len(df):,} dòng × {len(df.columns)} cột")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 2: Khởi tạo SQLite và tạo Schema
# ═════════════════════════════════════════════════════════════════════════════
CREATE_SQL = """
-- Bảng Quận
CREATE TABLE IF NOT EXISTS dim_borough (
    borough_id    INTEGER PRIMARY KEY,
    borough_name  TEXT NOT NULL UNIQUE
);

-- Bảng Khu phố
CREATE TABLE IF NOT EXISTS dim_neighborhood (
    neighborhood_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood_name TEXT NOT NULL,
    borough_id        INTEGER NOT NULL,
    FOREIGN KEY (borough_id) REFERENCES dim_borough(borough_id),
    UNIQUE (neighborhood_name, borough_id)
);

-- Bảng Địa chỉ
CREATE TABLE IF NOT EXISTS dim_location (
    location_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    address         TEXT,
    zip_code        TEXT,
    block           TEXT,
    lot             TEXT,
    neighborhood_id INTEGER NOT NULL,
    FOREIGN KEY (neighborhood_id) REFERENCES dim_neighborhood(neighborhood_id)
);

-- Bảng Bất động sản (tính chất vật lý)
CREATE TABLE IF NOT EXISTS dim_property (
    property_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    building_class_category  TEXT,
    building_category        TEXT,
    building_type            TEXT,
    building_class_present   TEXT,
    tax_class_present        TEXT,
    gross_sqft               REAL,
    land_sqft                REAL,
    year_built               INTEGER,
    building_age             INTEGER,
    residential_units        INTEGER,
    commercial_units         INTEGER,
    total_units              INTEGER,
    is_residential           INTEGER
);

-- Bảng Chỉ số kinh tế-xã hội (theo Quận)
CREATE TABLE IF NOT EXISTS dim_social_metrics (
    social_id        INTEGER PRIMARY KEY,
    borough_id       INTEGER NOT NULL UNIQUE,
    pop_density      REAL,
    avg_income       REAL,
    gdp_local        REAL,
    dist_center      REAL,
    amenity_score    REAL,
    num_parks        INTEGER,
    num_hospitals    INTEGER,
    num_supermarkets INTEGER,
    source_census    TEXT,
    source_osm       TEXT,
    FOREIGN KEY (borough_id) REFERENCES dim_borough(borough_id)
);

-- Bảng Giao dịch (Fact Table - trung tâm Star-Schema)
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id          INTEGER NOT NULL,
    property_id          INTEGER NOT NULL,
    social_id            INTEGER NOT NULL,
    sale_price           REAL,
    price_per_sqft       REAL,
    price_per_sqft_real  REAL,
    sale_date            TEXT,
    sale_year            INTEGER,
    sale_month           INTEGER,
    tax_class_sale       TEXT,
    building_class_sale  TEXT,
    FOREIGN KEY (location_id) REFERENCES dim_location(location_id),
    FOREIGN KEY (property_id) REFERENCES dim_property(property_id),
    FOREIGN KEY (social_id)   REFERENCES dim_social_metrics(social_id)
);
"""

BOROUGH_MAP = {
    1: 'Manhattan',
    2: 'Bronx',
    3: 'Brooklyn',
    4: 'Queens',
    5: 'Staten Island',
}

def init_db(conn: sqlite3.Connection):
    log("Khởi tạo schema SQLite (Star-Schema 5+1 bảng)...")
    conn.executescript(CREATE_SQL)
    conn.commit()
    log("  → Schema tạo thành công.")


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 3: Điền từng bảng Dimension
# ═════════════════════════════════════════════════════════════════════════════
def load_dim_borough(conn: sqlite3.Connection, df: pd.DataFrame) -> dict:
    """Trả về dict: borough_name → borough_id"""
    log("Nạp dim_borough...")
    rows = []
    for bid, bname in BOROUGH_MAP.items():
        rows.append((bid, bname))
    conn.executemany(
        "INSERT OR IGNORE INTO dim_borough (borough_id, borough_name) VALUES (?, ?)",
        rows
    )
    conn.commit()
    cur = conn.execute("SELECT borough_id, borough_name FROM dim_borough")
    result = {row[1]: row[0] for row in cur.fetchall()}
    log(f"  → {len(result)} quận đã nạp.")
    return result


def load_dim_neighborhood(conn: sqlite3.Connection, df: pd.DataFrame, borough_map: dict) -> dict:
    """Trả về dict: (neighborhood_name, borough_id) → neighborhood_id"""
    log("Nạp dim_neighborhood...")
    unique_neighborhoods = df[['neighborhood', 'borough_name']].drop_duplicates()
    rows = []
    for _, row in unique_neighborhoods.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        rows.append((nname, bid))

    conn.executemany(
        "INSERT OR IGNORE INTO dim_neighborhood (neighborhood_name, borough_id) VALUES (?, ?)",
        rows
    )
    conn.commit()

    cur = conn.execute("SELECT neighborhood_id, neighborhood_name, borough_id FROM dim_neighborhood")
    result = {(row[1], row[2]): row[0] for row in cur.fetchall()}
    log(f"  → {len(result)} khu phố đã nạp.")
    return result


def load_dim_location(conn: sqlite3.Connection, df: pd.DataFrame,
                      neighborhood_map: dict, borough_map: dict) -> pd.Series:
    """Nạp dim_location, trả về Series location_id theo index gốc của df"""
    log("Nạp dim_location...")
    loc_cols = ['address', 'zip_code', 'block', 'lot', 'neighborhood', 'borough_name']
    sub = df[loc_cols].copy().reset_index(drop=False)  # giữ index gốc

    rows = []
    for _, row in sub.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        nid   = neighborhood_map.get((nname, bid), 1)
        rows.append((
            str(row['address']).strip()[:200],
            str(row['zip_code']).strip(),
            str(row['block']).strip(),
            str(row['lot']).strip(),
            nid
        ))

    conn.executemany(
        """INSERT INTO dim_location
           (address, zip_code, block, lot, neighborhood_id)
           VALUES (?, ?, ?, ?, ?)""",
        rows
    )
    conn.commit()

    # Lấy lại location_id theo thứ tự insert (ROWID)
    first_id = conn.execute(
        "SELECT MIN(location_id) FROM dim_location"
    ).fetchone()[0]
    total = len(rows)
    location_ids = list(range(first_id, first_id + total))
    log(f"  → {total:,} địa chỉ đã nạp.")
    return pd.Series(location_ids, index=df.index)


def load_dim_property(conn: sqlite3.Connection, df: pd.DataFrame) -> pd.Series:
    """Nạp dim_property, trả về Series property_id theo index gốc của df"""
    log("Nạp dim_property...")
    prop_cols = [
        'building_class_category', 'building_category', 'building_type',
        'building_class_present', 'tax_class_present',
        'gross_sqft', 'land_sqft', 'year_built', 'building_age',
        'residential_units', 'commercial_units', 'total_units', 'is_residential'
    ]
    sub = df[[c for c in prop_cols if c in df.columns]].copy()

    # Điền cột còn thiếu nếu không tồn tại
    for col in prop_cols:
        if col not in sub.columns:
            sub[col] = None

    rows = []
    for _, row in sub.iterrows():
        rows.append((
            str(row['building_class_category'])[:100],
            str(row.get('building_category', ''))[:100],
            str(row.get('building_type', ''))[:100],
            str(row['building_class_present'])[:20],
            str(row['tax_class_present'])[:20],
            float(row['gross_sqft']) if pd.notna(row['gross_sqft']) else None,
            float(row['land_sqft'])  if pd.notna(row['land_sqft'])  else None,
            safe_int(row['year_built']),
            safe_int(row['building_age']),
            safe_int(row['residential_units']),
            safe_int(row['commercial_units']),
            safe_int(row['total_units']),
            safe_int(row.get('is_residential', 0)),
        ))

    conn.executemany(
        """INSERT INTO dim_property
           (building_class_category, building_category, building_type,
            building_class_present, tax_class_present,
            gross_sqft, land_sqft, year_built, building_age,
            residential_units, commercial_units, total_units, is_residential)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    conn.commit()

    first_id = conn.execute("SELECT MIN(property_id) FROM dim_property").fetchone()[0]
    property_ids = list(range(first_id, first_id + len(rows)))
    log(f"  → {len(rows):,} bản ghi property đã nạp.")
    return pd.Series(property_ids, index=df.index)


def load_dim_social_metrics(conn: sqlite3.Connection, df: pd.DataFrame, borough_map: dict) -> dict:
    """Nạp dim_social_metrics, trả về dict: borough_id → social_id"""
    log("Nạp dim_social_metrics (từ social_metrics.json)...")
    
    if not os.path.exists(SOCIAL_JSON):
        raise FileNotFoundError(f"Không tìm thấy file {SOCIAL_JSON}. Hãy chạy crawl_social_metrics.py trước.")
        
    with open(SOCIAL_JSON, 'r', encoding='utf-8') as f:
        social_data = json.load(f)

    rows = []
    for bid_str, data in social_data.items():
        bid = int(bid_str)
        rows.append((
            bid,  # social_id = borough_id (1-5)
            bid,
            float(data.get('pop_density',  0)),
            float(data.get('avg_income',   0)),
            float(data.get('gdp_local',    0)),
            float(data.get('dist_center',  0)),
            float(data.get('amenity_score', 0)),
            int(data.get('num_parks', 0)),
            int(data.get('num_hospitals', 0)),
            int(data.get('num_supermarkets', 0)),
            str(data.get('source_census', '')),
            str(data.get('source_osm', ''))
        ))

    conn.executemany(
        """INSERT OR IGNORE INTO dim_social_metrics
           (social_id, borough_id, pop_density, avg_income, gdp_local, dist_center, amenity_score,
            num_parks, num_hospitals, num_supermarkets, source_census, source_osm)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows
    )
    conn.commit()
    log(f"  → {len(rows)} bộ chỉ số xã hội (real crawled data) đã nạp.")
    return {row[1]: row[0] for row in rows}  # borough_id → social_id


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 4: Điền bảng Fact
# ═════════════════════════════════════════════════════════════════════════════
def load_fact_sales(conn: sqlite3.Connection, df: pd.DataFrame,
                    location_ids: pd.Series, property_ids: pd.Series,
                    social_map: dict, borough_map: dict):
    log("Nạp fact_sales...")
    rows = []
    for idx, row in df.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        sid   = social_map.get(bid, bid)

        rows.append((
            int(location_ids[idx]),
            int(property_ids[idx]),
            int(sid),
            float(row['sale_price'])           if pd.notna(row['sale_price'])           else None,
            float(row.get('price_per_sqft', 0))      if pd.notna(row.get('price_per_sqft', None)) else None,
            float(row.get('price_per_sqft_real', 0)) if pd.notna(row.get('price_per_sqft_real', None)) else None,
            str(row.get('sale_date', ''))[:20],
            safe_int(row.get('sale_year', 0)),
            safe_int(row.get('sale_month', 0)),
            str(row.get('tax_class_sale', ''))[:20],
            str(row.get('building_class_sale', ''))[:20],
        ))

    # Insert theo batch để nhanh hơn
    BATCH = 5000
    total = len(rows)
    for i in range(0, total, BATCH):
        conn.executemany(
            """INSERT INTO fact_sales
               (location_id, property_id, social_id,
                sale_price, price_per_sqft, price_per_sqft_real,
                sale_date, sale_year, sale_month,
                tax_class_sale, building_class_sale)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows[i:i+BATCH]
        )
        conn.commit()
        log(f"  → Đã insert: {min(i+BATCH, total):,}/{total:,}")

    log(f"  ✅ fact_sales hoàn tất: {total:,} giao dịch.")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def run_etl():
    print()
    print("=" * 60)
    print("  ETL PIPELINE: CSV → SQLite Star-Schema")
    print(f"  Source : {os.path.basename(CLEAN_CSV)}")
    print(f"  Target : {DB_PATH}")
    print("=" * 60)
    start = datetime.now()

    # Tạo thư mục warehouse nếu chưa có
    os.makedirs(WAREHOUSE_DIR, exist_ok=True)

    # Xóa DB cũ để build lại từ đầu (idempotent)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        log("Đã xóa file DB cũ, build lại từ đầu.")

    # Kết nối SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        # 1. Đọc CSV
        df = load_clean_csv()
        df = df.reset_index(drop=True)

        # 2. Schema
        init_db(conn)

        # 3. Dimensions
        borough_map      = load_dim_borough(conn, df)
        neighborhood_map = load_dim_neighborhood(conn, df, borough_map)
        location_ids     = load_dim_location(conn, df, neighborhood_map, borough_map)
        property_ids     = load_dim_property(conn, df)
        social_map       = load_dim_social_metrics(conn, df, borough_map)

        # 4. Fact
        load_fact_sales(conn, df, location_ids, property_ids, social_map, borough_map)

    finally:
        conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    db_size = os.path.getsize(DB_PATH) / 1024 / 1024
    print()
    print("=" * 60)
    print(f"  ✅ ETL HOÀN TẤT!")
    print(f"  Thời gian  : {elapsed:.1f} giây")
    print(f"  File DB    : {DB_PATH}")
    print(f"  Kích thước : {db_size:.1f} MB")
    print("=" * 60)
    print()


if __name__ == '__main__':
    run_etl()
