import os
import sys
import sqlite3

# Cấu hình encoding cho terminal tránh lỗi hiển thị Unicode
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nyc_real_estate.db")

print("==================================================")
print("   RUNNING DATABASE RELATIONSHIP INTEGRITY TESTS  ")
print("==================================================")

if not os.path.exists(DB_PATH):
    print(f"[ERROR] Database file not found at: {DB_PATH}")
    print("Please run 'python init_db.py' first to create the database.")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Bật tính năng khóa ngoại bắt buộc
cursor.execute("PRAGMA foreign_keys = ON;")

def run_test(test_name, test_func):
    try:
        test_func()
        print(f"[PASS] {test_name}")
    except Exception as e:
        print(f"[FAIL] {test_name}")
        print(f"       Detail: {e}")

# TEST 1: Kiểm tra kết nối và cấu hình khóa ngoại
def test_foreign_key_enabled():
    cursor.execute("PRAGMA foreign_keys;")
    status = cursor.fetchone()[0]
    assert status == 1, "Foreign key constraints are not enabled!"

# TEST 2: Kiểm tra dữ liệu có tồn tại trong các bảng
def test_tables_populated():
    tables = ['dim_borough', 'dim_neighborhood', 'dim_location', 'dim_building_class', 'dim_property', 'fact_sales']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        assert count > 0, f"Table {table} is empty!"
        print(f"       - Table '{table}': {count} records")

# TEST 3: Kiểm tra ràng buộc khóa ngoại (Constraint Enforcement)
def test_fk_constraint_enforcement():
    # Thử chèn một giao dịch vào fact_sales với property_id không tồn tại (phải báo lỗi)
    try:
        cursor.execute("""
            INSERT INTO fact_sales (property_id, location_id, sale_price, sale_date, sale_year, sale_month)
            VALUES (99999999, 1, 500000.0, '2026-06-29', 2026, 6);
        """)
        # Nếu chạy đến đây mà không lỗi tức là ràng buộc khóa ngoại không hoạt động
        assert False, "Violating FK constraint did not raise an error!"
    except sqlite3.IntegrityError as e:
        # Nhận lỗi IntegrityError là đúng thiết kế
        pass

# TEST 4: Kiểm tra tính toàn vẹn của dữ liệu thông qua truy vấn JOIN
def test_data_join_integrity():
    cursor.execute("""
        SELECT 
            f.sale_id,
            b.borough_name,
            n.neighborhood_name,
            l.address,
            c.building_category,
            f.sale_price
        FROM fact_sales f
        JOIN dim_property p ON f.property_id = p.property_id
        JOIN dim_building_class c ON p.building_class_id = c.building_class_id
        JOIN dim_location l ON f.location_id = l.location_id
        JOIN dim_neighborhood n ON l.neighborhood_id = n.neighborhood_id
        JOIN dim_borough b ON n.borough_id = b.borough_id
        LIMIT 1;
    """)
    row = cursor.fetchone()
    assert row is not None, "JOIN query returned no results!"
    print(f"       - Sample transaction: Sale #{row[0]} in {row[1]} ({row[2]}) at {row[3]} for {row[4]} sold at ${row[5]:,.2f}")

# Chạy các bài test
run_test("1. Verify Foreign Key Configuration", test_foreign_key_enabled)
run_test("2. Verify Row Count in All Tables", test_tables_populated)
run_test("3. Verify Foreign Key Constraint Enforcement", test_fk_constraint_enforcement)
run_test("4. Verify Referential Integrity via Multi-Table JOIN", test_data_join_integrity)

conn.close()
print("==================================================")
print("               TEST RUN COMPLETE                  ")
print("==================================================")
