import sys

# Thiết lập UTF-8 để hiển thị tiếng Việt mượt mà trên console Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Sơ đồ quan hệ dạng ASCII
ASCII_ERD = """
================================================================================
                    SƠ ĐỒ QUAN HỆ CƠ SỞ DỮ LIỆU (ASCII ERD - 3NF) 
================================================================================

    [dim_borough]
         │ 1
         │
         │ N
    [dim_neighborhood]
         │ 1
         │
         │ N
    [dim_location]                       [dim_building_class]
         │ 1                                      │ 1
         │                                        │
         │ N                                      │ N
    [fact_sales] N────────────────────────1 [dim_property]

================================================================================
"""

# Sơ đồ quan hệ dạng Mermaid
MERMAID_ERD = """
================================================================================
                          SƠ ĐỒ DẠNG MERMAID ERD
================================================================================
erDiagram
    dim_borough ||--o{ dim_neighborhood : "chứa (1:N)"
    dim_neighborhood ||--o{ dim_location : "định vị (1:N)"
    dim_building_class ||--o{ dim_property : "phân loại (1:N)"
    dim_property ||--o{ fact_sales : "thuộc tính vật lý (1:N)"
    dim_location ||--o{ fact_sales : "địa điểm giao dịch (1:N)"

* Gợi ý: Bạn có thể copy mã nguồn erDiagram trên và dán trực tiếp vào:
  - Mermaid Live Editor (https://mermaid.live/) hoặc Draw.io để vẽ sơ đồ đẹp mắt.
================================================================================
"""

# Chi tiết liên kết và khóa ngoại
RELATIONSHIP_DETAILS = """
================================================================================
                    CHI TIẾT RÀNG BUỘC KHÓA NGOẠI (FOREIGN KEYS)
================================================================================
1. dim_neighborhood.borough_id  ───> dim_borough.borough_id
   - Ràng buộc: Một Quận (Borough) có thể có nhiều Khu phố (Neighborhood).

2. dim_location.neighborhood_id ───> dim_neighborhood.neighborhood_id
   - Ràng buộc: Một Khu phố (Neighborhood) có thể chứa nhiều Địa chỉ/Thửa đất (Location).

3. dim_property.building_class_id ─> dim_building_class.building_class_id
   - Ràng buộc: Một Lớp phân loại (Building Class) áp dụng cho nhiều Bất động sản (Property).

4. fact_sales.property_id ─────────> dim_property.property_id
   - Ràng buộc: Một Bất động sản vật lý (Property) có thể giao dịch mua bán nhiều lần.

5. fact_sales.location_id ─────────> dim_location.location_id
   - Ràng buộc: Một địa chỉ địa chính (Location) có thể xảy ra nhiều lượt giao dịch.
================================================================================
"""

def main():
    print(ASCII_ERD)
    print(RELATIONSHIP_DETAILS)
    print(MERMAID_ERD)

if __name__ == "__main__":
    main()
