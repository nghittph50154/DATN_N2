import sys
import os
import warnings
import pandas as pd
import numpy as np
from datetime import datetime

# --- SYSTEM CONFIG ---
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

warnings.filterwarnings('ignore')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'nyc_sales.csv')
CLEAN_DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'nyc_sales_clean.csv')

BOROUGH_MAP = {
    '1': 'Manhattan',
    '2': 'Bronx',
    '3': 'Brooklyn',
    '4': 'Queens',
    '5': 'Staten Island',
}


def collect_external_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ghép thêm các chỉ số kinh tế – xã hội theo borough.
    Trong dự án thực có thể thay bằng API GSO / Census.
    """
    print("[LOG] Step 1: Thu thập & ghép dữ liệu ngoại vi (Census, GDP, Amenities)...")

    economic_indicators = {
        '1': {'pop_density': 72000, 'avg_income': 88000, 'gdp_local': 6.8, 'dist_center': 2.0},
        '2': {'pop_density': 36000, 'avg_income': 64000, 'gdp_local': 5.9, 'dist_center': 4.5},
        '3': {'pop_density': 38000, 'avg_income': 59000, 'gdp_local': 5.3, 'dist_center': 8.0},
        '4': {'pop_density': 19000, 'avg_income': 55000, 'gdp_local': 5.0, 'dist_center': 11.5},
        '5': {'pop_density':  9000, 'avg_income': 74000, 'gdp_local': 6.2, 'dist_center': 16.0},
    }

    df['borough_str'] = df['borough'].astype(str)

    for key in ['pop_density', 'avg_income', 'gdp_local', 'dist_center']:
        df[key] = df['borough_str'].map(
            lambda x, k=key: economic_indicators.get(x, economic_indicators['1'])[k]
        )

    # Amenity score: kết hợp mật độ đơn vị và khoảng cách trung tâm
    df['amenity_score'] = (
        df['total_units'] * 0.15 + (1 / df['dist_center']) * 10
    ).clip(1, 10)

    return df


def load_data(file_path: str = None):
    """Load raw data from CSV file."""
    if file_path is None:
        file_path = RAW_DATA_PATH
    
    print(f"[LOG] Loading data from: {file_path}")
    df = pd.read_csv(file_path)
    print(f"       Loaded {len(df):,} records with {len(df.columns)} columns")
    return df


def clean_data(df: pd.DataFrame):
    """Clean and preprocess the data."""
    print("[LOG] Step 2: Làm sạch dữ liệu (dedup, impute, IQR, encoding)...")

    numeric_cols = df.select_dtypes(include=[np.number]).columns

    # Thống kê mô tả
    stats = df[numeric_cols].describe().transpose()
    stats['variance'] = df[numeric_cols].var()
    stats['IQR'] = stats['75%'] - stats['25%']

    # 2.1 Loại bỏ trùng lặp
    before = len(df)
    df = df.drop_duplicates()
    print(f"       Đã xóa {before - len(df)} dòng trùng lặp.")

    # 2.2 Điền missing: median cho số, mode cho phân loại
    for col in df.select_dtypes(include=[np.number]).columns:
        df[col] = df[col].fillna(df[col].median())
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].mode()[0])

    # 2.3 Xử lý ngoại lệ bằng IQR clipping
    for col in ['sale_price', 'gross_square_feet', 'land_square_feet']:
        if col in df.columns:
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            df[col] = np.clip(df[col], Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)

    # 2.4 Tạo biến phái sinh
    df['is_residential'] = df.get('tax_class_present', pd.Series(dtype=str)).apply(
        lambda x: 1 if str(x).startswith('1') else 0
    )

    # Price per sqft thực sự (loại sqft = 0)
    df['price_per_sqft_real'] = np.where(
        df['gross_square_feet'] > 0,
        df['sale_price'] / df['gross_square_feet'],
        np.nan,
    )

    # Parse ngày bán
    df['sale_date_parsed'] = pd.to_datetime(df.get('sale_date', pd.Series(dtype=str)),
                                            dayfirst=True, errors='coerce')
    df['sale_month'] = df['sale_date_parsed'].dt.month

    # Thêm tên borough tiếng Anh
    df['borough_name'] = df['borough'].astype(str).map(BOROUGH_MAP).fillna('Unknown')

    return df, stats


def save_cleaned_data(df: pd.DataFrame, output_path: str = None):
    """Save cleaned data to CSV file."""
    if output_path is None:
        output_path = CLEAN_DATA_PATH
    
    df.to_csv(output_path, index=False)
    print(f"       Dữ liệu sạch đã lưu: {output_path} ({len(df):,} dòng)")
    return output_path


def preprocess_pipeline(input_path: str = None, output_path: str = None):
    """Run the complete preprocessing pipeline."""
    print('\n=== PREPROCESSING PIPELINE START ===\n')
    
    # Load data
    df = load_data(input_path)
    
    # Add external data
    df = collect_external_data(df)
    
    # Clean data
    df_clean, stats = clean_data(df)
    
    # Save cleaned data
    save_path = save_cleaned_data(df_clean, output_path)
    
    print('\n=== PREPROCESSING PIPELINE COMPLETE ===')
    print(f'  • Input  : {input_path or RAW_DATA_PATH}')
    print(f'  • Output : {save_path}')
    
    return df_clean, stats


if __name__ == '__main__':
    try:
        df_clean, stats = preprocess_pipeline()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Preprocessing failed: {e}")
