/*
================================================================================
BÁO CÁO PHÂN TÍCH DATABASE & SƠ ĐỒ THIẾT KẾ CSDL CHUẨN HÓA 3NF (ERD) DẠNG SQL COMMENTS
================================================================================

1. PHÂN TÍCH TOÀN BỘ BẢNG CHUẨN HÓA (DETAILED 3NF TABLES ANALYSIS)
--------------------------------------------------------------------------------
Bảng 1: dim_borough (Quận)
- Mục đích: Lưu trữ thông tin kinh tế - xã hội của 5 quận lớn tại NYC.
- Các cột:
  * borough_id (INT)            : Khóa chính (PK), NOT NULL.
  * borough_name (VARCHAR(50))  : Tên quận, UNIQUE, NOT NULL.
  * pop_density (INT)           : Mật độ dân số, NULLABLE.
  * avg_income (DECIMAL(12,2))  : Thu nhập bình quân, NULLABLE.
  * gdp_local (DECIMAL(5,2))    : GDP đóng góp, NULLABLE.
  * dist_center (DECIMAL(5,2))  : Khoảng cách tới trung tâm (km), NULLABLE.
  * amenity_score (DECIMAL(4,2)): Điểm tiện ích công cộng, NULLABLE.

Bảng 2: dim_neighborhood (Khu phố)
- Mục đích: Lưu trữ các khu phố trực thuộc các quận (Loại bỏ phụ thuộc bắc cầu giữa Neighborhood và Borough).
- Các cột:
  * neighborhood_id (SERIAL)    : Khóa chính (PK), AUTO_INCREMENT, NOT NULL.
  * neighborhood_name (VARCHAR) : Tên khu phố, UNIQUE, NOT NULL.
  * borough_id (INT)            : Khóa ngoại (FK) tham chiếu tới dim_borough, NOT NULL.

Bảng 3: dim_location (Vị trí & Địa chỉ)
- Mục đích: Định vị địa chỉ địa chính và liên kết với khu phố hành chính.
- Các cột:
  * location_id (SERIAL)        : Khóa chính (PK), AUTO_INCREMENT, NOT NULL.
  * address (VARCHAR(255))      : Địa chỉ chi tiết, NOT NULL.
  * zip_code (VARCHAR(20))      : Mã zip bưu chính, NULLABLE.
  * block (INT)                 : Mã khối đất địa chính, NULLABLE.
  * lot (INT)                   : Mã thửa đất địa chính, NULLABLE.
  * neighborhood_id (INT)       : Khóa ngoại (FK) tham chiếu tới dim_neighborhood, NOT NULL.

Bảng 4: dim_building_class (Phân loại loại hình xây dựng)
- Mục đích: Lưu cấu trúc phân loại tòa nhà và danh mục lớp đóng thuế của NYC.
- Các cột:
  * building_class_id (VARCHAR) : Khóa chính (PK) (Ví dụ: 'A1', 'R4'), NOT NULL.
  * building_class_category (VC): Lớp danh mục tòa nhà, NOT NULL.
  * building_category (VARCHAR) : Danh mục tổng quát, NOT NULL.
  * building_type (VARCHAR)     : Phân khúc chi tiết, NOT NULL.

Bảng 5: dim_property (Thông số vật lý tài sản)
- Mục đích: Lưu các chỉ số vật lý, tuổi thọ, quy mô diện tích của từng tài sản.
- Các cột:
  * property_id (SERIAL)        : Khóa chính (PK), AUTO_INCREMENT, NOT NULL.
  * building_class_id (VARCHAR) : Khóa ngoại (FK) tham chiếu tới dim_building_class, NOT NULL.
  * year_built (INT)            : Năm xây dựng, NULLABLE.
  * building_age (INT)          : Tuổi công trình, NULLABLE.
  * residential_units (INT)     : Số căn hộ để ở, DEFAULT 0, NOT NULL.
  * commercial_units (INT)      : Số căn hộ kinh doanh, DEFAULT 0, NOT NULL.
  * total_units (INT)           : Tổng số căn hộ, DEFAULT 0, NOT NULL.
  * land_sqft (INT)             : Diện tích đất (sqft), NULLABLE.
  * gross_sqft (INT)            : Diện tích sàn xây dựng (sqft), NULLABLE.
  * is_residential (INT)        : Cờ xác định phân khúc (0/1), CHECK, NULLABLE.

Bảng 6: fact_sales (Sự kiện giao dịch mua bán)
- Mục đích: Ghi nhận lịch sử giao dịch mua bán thực tế.
- Các cột:
  * sale_id (SERIAL)            : Khóa chính (PK), AUTO_INCREMENT, NOT NULL.
  * property_id (INT)           : Khóa ngoại (FK) tham chiếu tới dim_property, NOT NULL.
  * location_id (INT)           : Khóa ngoại (FK) tham chiếu tới dim_location, NOT NULL.
  * sale_price (DECIMAL(15,2))  : Giá giao dịch, NOT NULL.
  * price_per_sqft (DECIMAL)    : Đơn giá tạm tính, NULLABLE.
  * price_per_sqft_real (DEC)   : Đơn giá thực tế, NULLABLE.
  * sale_date (DATE)            : Ngày giao dịch, NOT NULL.
  * sale_year (INT)             : Năm giao dịch, NOT NULL.
  * sale_month (INT)            : Tháng giao dịch, NOT NULL.
  * is_internal_transfer (BOOL) : Giao dịch nội bộ, DEFAULT FALSE.
  * is_luxury (BOOL)            : Bất động sản siêu sang, DEFAULT FALSE.


2. PHÂN TÍCH QUAN HỆ (RELATIONSHIPS)
--------------------------------------------------------------------------------
- dim_borough (1)       <-------- (N) dim_neighborhood (Quận có nhiều khu phố)
- dim_neighborhood (1)  <-------- (N) dim_location (Khu phố chứa nhiều địa chỉ thửa đất)
- dim_location (1)      <-------- (N) fact_sales (Địa chỉ đất xảy ra nhiều giao dịch qua năm tháng)
- dim_building_class (1)<-------- (N) dim_property (Một lớp xây dựng áp dụng cho nhiều tài sản)
- dim_property (1)      <-------- (N) fact_sales (Tài sản vật lý trải qua nhiều lần mua đi bán lại)


3. CHỈ RÕ FOREIGN KEYS (KHÓA NGOẠI)
--------------------------------------------------------------------------------
- dim_neighborhood.borough_id     --> dim_borough.borough_id
- dim_location.neighborhood_id    --> dim_neighborhood.neighborhood_id
- dim_property.building_class_id  --> dim_building_class.building_class_id
- fact_sales.property_id          --> dim_property.property_id
- fact_sales.location_id          --> dim_location.location_id


4. SƠ ĐỒ MERMAID ERD (Mermaid Code)
--------------------------------------------------------------------------------
erDiagram
    dim_borough ||--o{ dim_neighborhood : "contains"
    dim_neighborhood ||--o{ dim_location : "contains"
    dim_building_class ||--o{ dim_property : "classifies"
    dim_property ||--o{ fact_sales : "features"
    dim_location ||--o{ fact_sales : "places"
================================================================================
*/

-- ==========================================
-- BƯỚC 1: XÓA CÁC BẢNG THEO THỨ TỰ PHỤ THUỘC KHÓA NGOẠI
-- ==========================================
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_property;
DROP TABLE IF EXISTS dim_building_class;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_neighborhood;
DROP TABLE IF EXISTS dim_borough;

-- ==========================================
-- BƯỚC 2: TẠO BẢNG QUẬN (dim_borough)
-- ==========================================
CREATE TABLE dim_borough (
    borough_id INT,
    borough_name VARCHAR(50) NOT NULL,
    pop_density INT NULL,
    avg_income DECIMAL(12, 2) NULL,
    gdp_local DECIMAL(5, 2) NULL,
    dist_center DECIMAL(5, 2) NULL,
    amenity_score DECIMAL(4, 2) NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_dim_borough PRIMARY KEY (borough_id),
    CONSTRAINT uq_borough_name UNIQUE (borough_name)
);

-- ==========================================
-- BƯỚC 3: TẠO BẢNG KHU PHỐ (dim_neighborhood)
-- ==========================================
CREATE TABLE dim_neighborhood (
    neighborhood_id SERIAL,
    neighborhood_name VARCHAR(100) NOT NULL,
    borough_id INT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_dim_neighborhood PRIMARY KEY (neighborhood_id),
    CONSTRAINT uq_neighborhood_name UNIQUE (neighborhood_name),
    CONSTRAINT fk_neighborhood_borough FOREIGN KEY (borough_id)
        REFERENCES dim_borough(borough_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ==========================================
-- BƯỚC 4: TẠO BẢNG ĐỊA CHỈ & THỬA ĐẤT (dim_location)
-- ==========================================
CREATE TABLE dim_location (
    location_id SERIAL,
    address VARCHAR(255) NOT NULL,
    zip_code VARCHAR(20) NULL,
    block INT NULL,
    lot INT NULL,
    neighborhood_id INT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_dim_location PRIMARY KEY (location_id),
    CONSTRAINT fk_location_neighborhood FOREIGN KEY (neighborhood_id)
        REFERENCES dim_neighborhood(neighborhood_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ==========================================
-- BƯỚC 5: TẠO BẢNG PHÂN LOẠI XÂY DỰNG (dim_building_class)
-- ==========================================
CREATE TABLE dim_building_class (
    building_class_id VARCHAR(10),
    building_class_category VARCHAR(100) NOT NULL,
    building_category VARCHAR(100) NOT NULL,
    building_type VARCHAR(100) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_dim_building_class PRIMARY KEY (building_class_id)
);

-- ==========================================
-- BƯỚC 6: TẠO BẢNG THÔNG SỐ VẬT LÝ TÀI SẢN (dim_property)
-- ==========================================
CREATE TABLE dim_property (
    property_id SERIAL,
    building_class_id VARCHAR(10) NOT NULL,
    year_built INT NULL,
    building_age INT NULL,
    residential_units INT NOT NULL DEFAULT 0,
    commercial_units INT NOT NULL DEFAULT 0,
    total_units INT NOT NULL DEFAULT 0,
    land_sqft INT NULL,
    gross_sqft INT NULL,
    is_residential INT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_dim_property PRIMARY KEY (property_id),
    CONSTRAINT fk_property_building_class FOREIGN KEY (building_class_id)
        REFERENCES dim_building_class(building_class_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT chk_property_is_residential CHECK (is_residential IN (0, 1))
);

-- ==========================================
-- BƯỚC 7: TẠO BẢNG SỰ KIỆN GIAO DỊCH GIAO DỊCH (fact_sales)
-- ==========================================
CREATE TABLE fact_sales (
    sale_id SERIAL,
    property_id INT NOT NULL,
    location_id INT NOT NULL,
    sale_price DECIMAL(15, 2) NOT NULL,
    price_per_sqft DECIMAL(15, 2) NULL,
    price_per_sqft_real DECIMAL(15, 2) NULL,
    sale_date DATE NOT NULL,
    sale_year INT NOT NULL,
    sale_month INT NOT NULL,
    is_internal_transfer BOOLEAN DEFAULT FALSE,
    is_luxury BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT pk_fact_sales PRIMARY KEY (sale_id),
    
    CONSTRAINT fk_sales_property FOREIGN KEY (property_id)
        REFERENCES dim_property(property_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
        
    CONSTRAINT fk_sales_location FOREIGN KEY (location_id)
        REFERENCES dim_location(location_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

-- ==========================================
-- BƯỚC 8: TẠO CHỈ MỤC (INDEXES) TỐI ƯU TRUY VẤN
-- ==========================================

-- Chỉ mục hỗn hợp hỗ trợ tìm kiếm giao dịch nhanh theo giá bán và ngày bán
CREATE INDEX idx_sales_date_price ON fact_sales (sale_date, sale_price);

-- Chỉ mục khóa ngoại giúp truy vấn kết hợp các bảng chiều nhanh chóng
CREATE INDEX idx_sales_property_fk ON fact_sales (property_id);
CREATE INDEX idx_sales_location_fk ON fact_sales (location_id);
CREATE INDEX idx_location_neighborhood_fk ON dim_location (neighborhood_id);
CREATE INDEX idx_neighborhood_borough_fk ON dim_neighborhood (borough_id);
CREATE INDEX idx_property_building_class_fk ON dim_property (building_class_id);
