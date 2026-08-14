"""
verify_sqlite.py
================
Kiểm tra tính nhất quán giữa SQLite Data Warehouse và CSV gốc.

Chạy:
    python src/verify_sqlite.py
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_CSV  = os.path.join(BASE_DIR, 'data', 'data clean', 'Dulieu_Cleaned.csv')
DB_PATH    = os.path.join(BASE_DIR, 'data', 'warehouse', 'nyc_warehouse.db')

PASS = "✅ PASS"
FAIL = "❌ FAIL"

def check(label: str, expected, actual, tolerance=0):
    if isinstance(expected, float) and tolerance > 0:
        ok = abs(expected - actual) <= tolerance
    else:
        ok = expected == actual
    status = PASS if ok else FAIL
    print(f"  {status}  {label}")
    if not ok:
        print(f"         CSV   : {expected}")
        print(f"         SQLite: {actual}")
    return ok


def run_verify():
    print()
    print("=" * 65)
    print("  VERIFY: So sánh SQLite ↔ CSV gốc")
    print("=" * 65)

    # ── Đọc CSV ──────────────────────────────────────────────────
    print("\n[1] Đọc CSV sạch...")
    df = pd.read_csv(CLEAN_CSV, low_memory=False)
    print(f"    CSV: {len(df):,} dòng × {len(df.columns)} cột")

    # ── Kết nối SQLite ────────────────────────────────────────────
    print("\n[2] Kết nối SQLite...")
    conn = sqlite3.connect(DB_PATH)

    def q(sql):
        return conn.execute(sql).fetchone()[0]

    def qdf(sql):
        return pd.read_sql_query(sql, conn)

    results = []

    # ── Kiểm tra số dòng ──────────────────────────────────────────
    print("\n[3] Kiểm tra số dòng:")
    results.append(check(
        "Tổng fact_sales = CSV rows (47,039)",
        len(df),
        q("SELECT COUNT(*) FROM fact_sales")
    ))
    results.append(check(
        "dim_borough = 5 quận",
        5,
        q("SELECT COUNT(*) FROM dim_borough")
    ))
    # Tính số khu phố theo cặp (neighborhood + borough) — đúng hơn vì có khu phố trùng tên khác quận
    csv_neighborhood_count = df[['neighborhood', 'borough_name']].drop_duplicates().shape[0]
    results.append(check(
        f"dim_neighborhood = số khu phố trong CSV (theo cặp neighborhood+borough)",
        csv_neighborhood_count,
        q("SELECT COUNT(*) FROM dim_neighborhood")
    ))
    results.append(check(
        "dim_social_metrics = 5 bộ chỉ số",
        5,
        q("SELECT COUNT(*) FROM dim_social_metrics")
    ))

    # ── Kiểm tra tổng giá trị ────────────────────────────────────
    print("\n[4] Kiểm tra tổng giá trị (sale_price):")
    csv_total  = float(df['sale_price'].sum())
    sql_total  = float(q("SELECT SUM(sale_price) FROM fact_sales"))
    results.append(check(
        "Tổng sale_price CSV ≈ SQLite (sai số < 1%)",
        csv_total,
        sql_total,
        tolerance=csv_total * 0.01
    ))
    print(f"    CSV total   : {csv_total:>20,.0f}")
    print(f"    SQLite total: {sql_total:>20,.0f}")

    # ── Kiểm tra giá trung bình theo quận ───────────────────────
    print("\n[5] Kiểm tra giá TB từng quận (CSV vs SQLite JOIN):")
    csv_avg = (
        df.groupby('borough_name')['sale_price']
        .mean()
        .round(0)
        .sort_index()
    )

    sql_avg_df = qdf("""
        SELECT b.borough_name, ROUND(AVG(f.sale_price), 0) AS avg_price
        FROM fact_sales f
        JOIN dim_location  l ON f.location_id = l.location_id
        JOIN dim_neighborhood n ON l.neighborhood_id = n.neighborhood_id
        JOIN dim_borough   b ON n.borough_id = b.borough_id
        GROUP BY b.borough_name
        ORDER BY b.borough_name
    """)
    sql_avg = sql_avg_df.set_index('borough_name')['avg_price']

    print(f"\n  {'Quận':<15} {'CSV (avg $)':>15} {'SQLite (avg $)':>15} {'Khớp?':>8}")
    print(f"  {'-'*15} {'-'*15} {'-'*15} {'-'*8}")
    all_match = True
    for bname in sorted(csv_avg.index):
        cv = csv_avg.get(bname, np.nan)
        sv = sql_avg.get(bname, np.nan)
        match = abs(cv - sv) < 1.0 if (not np.isnan(cv) and not np.isnan(sv)) else False
        icon  = "✅" if match else "❌"
        print(f"  {bname:<15} {cv:>15,.0f} {sv:>15,.0f} {icon:>8}")
        if not match:
            all_match = False
    results.append(all_match)

    # ── Kiểm tra Foreign Keys nhất quán ─────────────────────────
    print("\n[6] Kiểm tra tính toàn vẹn Foreign Key:")
    orphan_loc = q("""
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_location l ON f.location_id = l.location_id
        WHERE l.location_id IS NULL
    """)
    results.append(check("Không có fact_sales orphan (location_id)", 0, orphan_loc))

    orphan_prop = q("""
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_property p ON f.property_id = p.property_id
        WHERE p.property_id IS NULL
    """)
    results.append(check("Không có fact_sales orphan (property_id)", 0, orphan_prop))

    orphan_social = q("""
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_social_metrics s ON f.social_id = s.social_id
        WHERE s.social_id IS NULL
    """)
    results.append(check("Không có fact_sales orphan (social_id)", 0, orphan_social))

    # ── Kiểm tra cấu trúc bảng ───────────────────────────────────
    print("\n[7] Danh sách bảng trong DB:")
    tables = qdf("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for t in tables['name']:
        cnt = q(f"SELECT COUNT(*) FROM {t}")
        print(f"    📋 {t:<25} → {cnt:,} dòng")

    # ── Kết quả tổng ─────────────────────────────────────────────
    conn.close()
    passed = sum(1 for r in results if r)
    total  = len(results)
    print()
    print("=" * 65)
    print(f"  KẾT QUẢ: {passed}/{total} kiểm tra PASSED")
    if passed == total:
        print("  🎉 SQLite Data Warehouse NHẤT QUÁN hoàn toàn với CSV gốc!")
    else:
        print(f"  ⚠️  Có {total - passed} kiểm tra FAILED — cần xem lại ETL.")
    print("=" * 65)
    print()


if __name__ == '__main__':
    run_verify()
