"""
etl_to_postgres.py
================
ETL Pipeline: Đọc file CSV đã làm sạch → Tách bảng → Ghi vào PostgreSQL (Star-Schema)

Chạy:
    python src/etl_to_postgres.py
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from dotenv import load_dotenv

# ── Cấu hình encoding UTF-8 trên Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ── Load biến môi trường từ .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("LỖI: Không tìm thấy DATABASE_URL trong file .env!")

# ── Đường dẫn
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_CSV      = os.path.join(BASE_DIR, 'data', 'data clean', 'Dulieu_Cleaned.csv')
RAW_DIR        = os.path.join(BASE_DIR, 'data', 'raw')
SOCIAL_JSON    = os.path.join(RAW_DIR, 'social_metrics.json')

# ── Hàm tiện ích
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
# BƯỚC 2: Khởi tạo PostgreSQL Schema
# ═════════════════════════════════════════════════════════════════════════════
CREATE_SQL = """
-- Xóa bảng cũ nếu tồn tại (CASCADE để xóa khóa ngoại)
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_social_metrics CASCADE;
DROP TABLE IF EXISTS dim_property CASCADE;
DROP TABLE IF EXISTS dim_location CASCADE;
DROP TABLE IF EXISTS dim_neighborhood CASCADE;
DROP TABLE IF EXISTS dim_borough CASCADE;

-- Bảng Quận
CREATE TABLE dim_borough (
    borough_id    INTEGER PRIMARY KEY,
    borough_name  VARCHAR(255) NOT NULL UNIQUE
);

-- Bảng Khu phố
CREATE TABLE dim_neighborhood (
    neighborhood_id   SERIAL PRIMARY KEY,
    neighborhood_name VARCHAR(255) NOT NULL,
    borough_id        INTEGER NOT NULL,
    FOREIGN KEY (borough_id) REFERENCES dim_borough(borough_id),
    UNIQUE (neighborhood_name, borough_id)
);

-- Bảng Địa chỉ
CREATE TABLE dim_location (
    location_id     INTEGER PRIMARY KEY,
    address         VARCHAR(500),
    zip_code        VARCHAR(20),
    block           VARCHAR(50),
    lot             VARCHAR(50),
    neighborhood_id INTEGER NOT NULL,
    FOREIGN KEY (neighborhood_id) REFERENCES dim_neighborhood(neighborhood_id)
);

-- Bảng Bất động sản (tính chất vật lý)
CREATE TABLE dim_property (
    property_id              INTEGER PRIMARY KEY,
    building_class_category  VARCHAR(255),
    building_category        VARCHAR(255),
    building_type            VARCHAR(255),
    building_class_present   VARCHAR(50),
    tax_class_present        VARCHAR(50),
    gross_sqft               DOUBLE PRECISION,
    land_sqft                DOUBLE PRECISION,
    year_built               INTEGER,
    building_age             INTEGER,
    residential_units        INTEGER,
    commercial_units         INTEGER,
    total_units              INTEGER,
    is_residential           INTEGER
);

-- Bảng Chỉ số kinh tế-xã hội (theo Khu vực)
CREATE TABLE dim_social_metrics (
    social_id        SERIAL PRIMARY KEY,
    neighborhood_id  INTEGER NOT NULL UNIQUE,
    pop_density      DOUBLE PRECISION,
    avg_income       DOUBLE PRECISION,
    gdp_local        DOUBLE PRECISION,
    dist_center      DOUBLE PRECISION,
    amenity_score    DOUBLE PRECISION,
    num_parks        INTEGER,
    num_hospitals    INTEGER,
    num_supermarkets INTEGER,
    source_census    VARCHAR(255),
    source_osm       VARCHAR(255),
    FOREIGN KEY (neighborhood_id) REFERENCES dim_neighborhood(neighborhood_id)
);

-- Bảng Giao dịch (Fact Table - trung tâm Star-Schema)
CREATE TABLE fact_sales (
    sale_id              SERIAL PRIMARY KEY,
    location_id          INTEGER NOT NULL,
    property_id          INTEGER NOT NULL,
    social_id            INTEGER NOT NULL,
    sale_price           DOUBLE PRECISION,
    price_per_sqft       DOUBLE PRECISION,
    price_per_sqft_real  DOUBLE PRECISION,
    sale_date            VARCHAR(50),
    sale_year            INTEGER,
    sale_month           INTEGER,
    tax_class_sale       VARCHAR(50),
    building_class_sale  VARCHAR(50),
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

def init_db(conn):
    log("Khởi tạo schema PostgreSQL (Star-Schema 5+1 bảng)...")
    with conn.cursor() as cur:
        cur.execute(CREATE_SQL)
    conn.commit()
    log("  → Schema tạo thành công.")


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 3: Điền từng bảng Dimension
# ═════════════════════════════════════════════════════════════════════════════
def load_dim_borough(conn, df: pd.DataFrame) -> dict:
    log("Nạp dim_borough...")
    rows = [(bid, bname) for bid, bname in BOROUGH_MAP.items()]
    with conn.cursor() as cur:
        execute_batch(cur, 
            "INSERT INTO dim_borough (borough_id, borough_name) VALUES (%s, %s) ON CONFLICT (borough_name) DO NOTHING", 
            rows
        )
        conn.commit()
        cur.execute("SELECT borough_id, borough_name FROM dim_borough")
        result = {row[1]: row[0] for row in cur.fetchall()}
    log(f"  → {len(result)} quận đã nạp.")
    return result


def load_dim_neighborhood(conn, df: pd.DataFrame, borough_map: dict) -> dict:
    log("Nạp dim_neighborhood...")
    unique_neighborhoods = df[['neighborhood', 'borough_name']].drop_duplicates()
    rows = []
    for _, row in unique_neighborhoods.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        rows.append((nname, bid))

    with conn.cursor() as cur:
        execute_batch(cur,
            "INSERT INTO dim_neighborhood (neighborhood_name, borough_id) VALUES (%s, %s) ON CONFLICT (neighborhood_name, borough_id) DO NOTHING",
            rows
        )
        conn.commit()
        cur.execute("SELECT neighborhood_id, neighborhood_name, borough_id FROM dim_neighborhood")
        result = {(row[1], row[2]): row[0] for row in cur.fetchall()}
    log(f"  → {len(result)} khu phố đã nạp.")
    return result


def load_dim_location(conn, df: pd.DataFrame, neighborhood_map: dict, borough_map: dict) -> pd.Series:
    log("Nạp dim_location...")
    loc_cols = ['address', 'zip_code', 'block', 'lot', 'neighborhood', 'borough_name']
    sub = df[loc_cols].copy().reset_index(drop=False)

    rows = []
    for idx, row in sub.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        nid   = neighborhood_map.get((nname, bid), 1)
        rows.append((
            idx + 1,
            str(row['address']).strip()[:200],
            str(row['zip_code']).strip(),
            str(row['block']).strip(),
            str(row['lot']).strip(),
            nid
        ))

    with conn.cursor() as cur:
        execute_batch(cur,
            """INSERT INTO dim_location
               (location_id, address, zip_code, block, lot, neighborhood_id)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        
    location_ids = pd.Series([i + 1 for i in range(len(rows))], index=df.index)
    log(f"  → {len(rows):,} địa chỉ đã nạp.")
    return location_ids


def load_dim_property(conn, df: pd.DataFrame) -> pd.Series:
    log("Nạp dim_property...")
    prop_cols = [
        'building_class_category', 'building_category', 'building_type',
        'building_class_present', 'tax_class_present',
        'gross_sqft', 'land_sqft', 'year_built', 'building_age',
        'residential_units', 'commercial_units', 'total_units', 'is_residential'
    ]
    sub = df[[c for c in prop_cols if c in df.columns]].copy()
    for col in prop_cols:
        if col not in sub.columns:
            sub[col] = None

    rows = []
    for idx, row in sub.iterrows():
        rows.append((
            idx + 1,
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

    with conn.cursor() as cur:
        execute_batch(cur,
            """INSERT INTO dim_property
               (property_id, building_class_category, building_category, building_type,
                building_class_present, tax_class_present,
                gross_sqft, land_sqft, year_built, building_age,
                residential_units, commercial_units, total_units, is_residential)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            rows
        )
        conn.commit()
        
    property_ids = pd.Series([i + 1 for i in range(len(rows))], index=df.index)
    log(f"  → {len(rows):,} bản ghi property đã nạp.")
    return property_ids


def load_dim_social_metrics(conn, df: pd.DataFrame, borough_map: dict, neighborhood_map: dict) -> dict:
    log("Nạp dim_social_metrics (từ CSV gốc thay vì JSON)...")
    
    unique_social = df[['neighborhood', 'borough_name', 'pop_density', 'avg_income', 'dist_center', 'amenity_score']].drop_duplicates()
    
    rows = []
    for _, row in unique_social.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        nid   = neighborhood_map.get((nname, bid), 1)
        
        rows.append((
            nid,
            float(row.get('pop_density', 0)) if pd.notna(row.get('pop_density')) else 0.0,
            float(row.get('avg_income', 0)) if pd.notna(row.get('avg_income')) else 0.0,
            0.0,
            float(row.get('dist_center', 0)) if pd.notna(row.get('dist_center')) else 0.0,
            float(row.get('amenity_score', 0)) if pd.notna(row.get('amenity_score')) else 0.0,
            0, 0, 0,
            'CSV Data', 'CSV Data'
        ))

    with conn.cursor() as cur:
        execute_batch(cur,
            """INSERT INTO dim_social_metrics
               (neighborhood_id, pop_density, avg_income, gdp_local, dist_center, amenity_score,
                num_parks, num_hospitals, num_supermarkets, source_census, source_osm)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (neighborhood_id) DO NOTHING""",
            rows
        )
        conn.commit()
        cur.execute("SELECT neighborhood_id, social_id FROM dim_social_metrics")
        result = {row[0]: row[1] for row in cur.fetchall()}
    log(f"  → {len(result)} bộ chỉ số xã hội đã nạp.")
    return result


# ═════════════════════════════════════════════════════════════════════════════
# BƯỚC 4: Điền bảng Fact
# ═════════════════════════════════════════════════════════════════════════════
def load_fact_sales(conn, df: pd.DataFrame,
                    location_ids: pd.Series, property_ids: pd.Series,
                    social_map: dict, borough_map: dict, neighborhood_map: dict):
    log("Nạp fact_sales...")
    rows = []
    for idx, row in df.iterrows():
        bname = str(row['borough_name']).strip()
        bid   = borough_map.get(bname, 1)
        nname = str(row['neighborhood']).strip()
        nid   = neighborhood_map.get((nname, bid), 1)
        sid   = social_map.get(nid, 1)

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

    BATCH = 5000
    total = len(rows)
    with conn.cursor() as cur:
        for i in range(0, total, BATCH):
            execute_batch(cur,
                """INSERT INTO fact_sales
                   (location_id, property_id, social_id,
                    sale_price, price_per_sqft, price_per_sqft_real,
                    sale_date, sale_year, sale_month,
                    tax_class_sale, building_class_sale)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
    print("  ETL PIPELINE: CSV → PostgreSQL Star-Schema")
    print(f"  Target : Cloud PostgreSQL (Supabase/Neon)")
    print("=" * 60)
    start = datetime.now()

    try:
        conn = psycopg2.connect(DB_URL)
        log("Đã kết nối thành công tới PostgreSQL Cloud!")
        
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
        social_map       = load_dim_social_metrics(conn, df, borough_map, neighborhood_map)

        # 4. Fact
        load_fact_sales(conn, df, location_ids, property_ids, social_map, borough_map, neighborhood_map)

    except Exception as e:
        print(f"\n[LỖI ETL] {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    print()
    print("=" * 60)
    print(f"  ✅ ETL LÊN CLOUD POSTGRES HOÀN TẤT!")
    print(f"  Thời gian  : {elapsed:.1f} giây")
    print("=" * 60)
    print()

if __name__ == '__main__':
    run_etl()
