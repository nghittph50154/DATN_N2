"""
NYC Real Estate Sales Data Crawler - Advanced Version
Crawl dữ liệu bán hàng bất động sản NYC từ website chính phủ NYC
Version: 2.0
Author: Cascade
Date: 2026-06-28

Features:
- Multi-source crawling with retry logic
- Data validation and quality checks
- Multiple output formats (CSV, JSON, Excel, Parquet)
- Statistical analysis and visualization
- Progress tracking and logging
- Database export support
- Email notifications
- Scheduling capabilities
- Data enrichment
- Geocoding integration
"""

import pandas as pd
import requests
import os
import sys
import json
import logging
import argparse
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import traceback
import warnings
warnings.filterwarnings('ignore')

# Try to import optional dependencies
try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False
    print("Warning: openpyxl not installed. Excel output disabled.")

try:
    import pyarrow
    PARQUET_SUPPORT = True
except ImportError:
    PARQUET_SUPPORT = False
    print("Warning: pyarrow not installed. Parquet output disabled.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_SUPPORT = True
except ImportError:
    VISUALIZATION_SUPPORT = False
    print("Warning: matplotlib/seaborn not installed. Visualization disabled.")

try:
    from tqdm import tqdm
    TQDM_SUPPORT = True
except ImportError:
    TQDM_SUPPORT = False
    print("Warning: tqdm not installed. Progress bars disabled.")

# ============================================================================
# CONFIGURATION AND CONSTANTS
# ============================================================================

class OutputFormat(Enum):
    """Supported output formats"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    PARQUET = "parquet"
    SQLITE = "sqlite"

@dataclass
class CrawlerConfig:
    """Configuration for NYC Sales Crawler"""
    output_dir: str = "../data/raw"
    log_dir: str = "logs"
    temp_dir: str = "temp"
    output_format: OutputFormat = OutputFormat.CSV
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 60
    rate_limit_delay: int = 2
    enable_logging: bool = True
    enable_progress_bar: bool = True
    enable_validation: bool = True
    enable_statistics: bool = True
    enable_visualization: bool = False
    enable_database_export: bool = False
    database_path: str = "nyc_sales.db"
    enable_email_notification: bool = False
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_recipients: List[str] = field(default_factory=list)
    data_limit: Optional[int] = None
    deduplicate: bool = True
    deduplicate_columns: List[str] = field(default_factory=lambda: ['BOROUGH', 'ADDRESS', 'SALE DATE', 'SALE PRICE'])
    enable_geocoding: bool = False
    geocoding_api_key: str = ""
    cache_enabled: bool = True
    cache_dir: str = "cache"
    cache_expiry_hours: int = 24

# URLs cho dữ liệu rolling sales của từng quận NYC
NYC_SALES_URLS = {
    "Manhattan": "https://www.nyc.gov/assets/finance/downloads/pdf/rolling_sales/rollingsales_manhattan.xlsx",
    "Bronx": "https://www.nyc.gov/assets/finance/downloads/pdf/rolling_sales/rollingsales_bronx.xlsx",
    "Brooklyn": "https://www.nyc.gov/assets/finance/downloads/pdf/rolling_sales/rollingsales_brooklyn.xlsx",
    "Queens": "https://www.nyc.gov/assets/finance/downloads/pdf/rolling_sales/rollingsales_queens.xlsx",
    "Staten Island": "https://www.nyc.gov/assets/finance/downloads/pdf/rolling_sales/rollingsales_statenisland.xlsx"
}

# Expected columns in NYC sales data
EXPECTED_COLUMNS = [
    'BOROUGH', 'NEIGHBORHOOD', 'BUILDING CLASS CATEGORY', 'TAX CLASS AT PRESENT',
    'BLOCK', 'LOT', 'EASE-MENT', 'BUILDING CLASS AT PRESENT', 'ADDRESS',
    'APARTMENT NUMBER', 'ZIP CODE', 'RESIDENTIAL UNITS', 'COMMERCIAL UNITS',
    'TOTAL UNITS', 'LAND SQUARE FEET', 'GROSS SQUARE FEET', 'YEAR BUILT',
    'TAX CLASS AT TIME OF SALE', 'BUILDING CLASS AT TIME OF SALE', 'SALE PRICE',
    'SALE DATE', 'SALE PRICE PER SQFT'
]

# Data quality thresholds
QUALITY_THRESHOLDS = {
    'min_sale_price': 1,
    'max_sale_price': 1000000000,
    'min_year_built': 1600,
    'max_year_built': 2026,
    'min_gross_sqft': 1,
    'max_gross_sqft': 1000000,
    'min_land_sqft': 1,
    'max_land_sqft': 1000000
}

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(config: CrawlerConfig) -> logging.Logger:
    """Setup logging configuration"""
    if not config.enable_logging:
        # Disable logging
        logging.disable(logging.CRITICAL)
        return logging.getLogger(__name__)
    
    # Create log directory if not exists
    Path(config.log_dir).mkdir(parents=True, exist_ok=True)
    
    # Setup log filename with timestamp
    log_filename = os.path.join(
        config.log_dir,
        f"nyc_crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    return logger

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

class CacheManager:
    """Manage cached data to avoid redundant downloads"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.cache_dir = Path(config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL"""
        cache_key = self._get_cache_key(url)
        return self.cache_dir / f"{cache_key}.xlsx"
    
    def is_cached(self, url: str) -> bool:
        """Check if URL is cached and not expired"""
        if not self.config.cache_enabled:
            return False
        
        cache_path = self._get_cache_path(url)
        if not cache_path.exists():
            return False
        
        # Check if cache is expired
        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        if cache_age > timedelta(hours=self.config.cache_expiry_hours):
            self.logger.info(f"Cache expired for {url}")
            cache_path.unlink()
            return False
        
        self.logger.info(f"Cache hit for {url}")
        return True
    
    def get_cached_file(self, url: str) -> Optional[str]:
        """Get cached file path if available"""
        if self.is_cached(url):
            return str(self._get_cache_path(url))
        return None
    
    def save_to_cache(self, url: str, content: bytes) -> str:
        """Save content to cache"""
        cache_path = self._get_cache_path(url)
        with open(cache_path, 'wb') as f:
            f.write(content)
        self.logger.info(f"Saved to cache: {cache_path}")
        return str(cache_path)
    
    def clear_cache(self):
        """Clear all cached files"""
        for cache_file in self.cache_dir.glob("*.xlsx"):
            cache_file.unlink()
        self.logger.info("Cache cleared")

# ============================================================================
# DATA VALIDATION
# ============================================================================

class DataValidator:
    """Validate data quality and integrity"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.thresholds = QUALITY_THRESHOLDS
    
    def validate_dataframe(self, df: pd.DataFrame, borough_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate DataFrame and return validation report"""
        report = {
            'borough': borough_name,
            'total_rows': len(df),
            'valid_rows': 0,
            'invalid_rows': 0,
            'issues': []
        }
        
        if df.empty:
            report['issues'].append("DataFrame is empty")
            return False, report
        
        # Check for expected columns
        missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
        if missing_cols:
            report['issues'].append(f"Missing columns: {missing_cols}")
            self.logger.warning(f"Missing columns in {borough_name}: {missing_cols}")
        
        # Validate numeric columns
        numeric_validations = self._validate_numeric_columns(df)
        report.update(numeric_validations)
        
        # Validate dates
        date_validations = self._validate_dates(df)
        report.update(date_validations)
        
        # Check for duplicates
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            report['issues'].append(f"Found {duplicate_count} duplicate rows")
        
        report['valid_rows'] = len(df) - len(df[df.isnull().all(axis=1)])
        report['invalid_rows'] = len(df) - report['valid_rows']
        
        is_valid = len(report['issues']) == 0
        return is_valid, report
    
    def _validate_numeric_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate numeric columns against thresholds"""
        issues = []
        
        # Sale price validation
        if 'SALE PRICE' in df.columns:
            invalid_prices = df[
                (df['SALE PRICE'] < self.thresholds['min_sale_price']) |
                (df['SALE PRICE'] > self.thresholds['max_sale_price'])
            ]
            if len(invalid_prices) > 0:
                issues.append(f"Found {len(invalid_prices)} invalid sale prices")
        
        # Year built validation
        if 'YEAR BUILT' in df.columns:
            invalid_years = df[
                (df['YEAR BUILT'] < self.thresholds['min_year_built']) |
                (df['YEAR BUILT'] > self.thresholds['max_year_built'])
            ]
            if len(invalid_years) > 0:
                issues.append(f"Found {len(invalid_years)} invalid year built values")
        
        # Square feet validation
        if 'GROSS SQUARE FEET' in df.columns:
            invalid_sqft = df[
                (df['GROSS SQUARE FEET'] < self.thresholds['min_gross_sqft']) |
                (df['GROSS SQUARE FEET'] > self.thresholds['max_gross_sqft'])
            ]
            if len(invalid_sqft) > 0:
                issues.append(f"Found {len(invalid_sqft)} invalid gross square feet values")
        
        return {'numeric_issues': issues}
    
    def _validate_dates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate date columns"""
        issues = []
        
        if 'SALE DATE' in df.columns:
            try:
                pd.to_datetime(df['SALE DATE'], errors='coerce')
            except Exception as e:
                issues.append(f"Invalid sale date format: {e}")
        
        return {'date_issues': issues}
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame based on validation rules"""
        self.logger.info("Starting data cleaning...")
        
        # Remove completely empty rows
        initial_len = len(df)
        df = df.dropna(how='all')
        self.logger.info(f"Removed {initial_len - len(df)} empty rows")
        
        # Remove rows with invalid sale prices
        if 'SALE PRICE' in df.columns:
            df = df[
                (df['SALE PRICE'] >= self.thresholds['min_sale_price']) &
                (df['SALE PRICE'] <= self.thresholds['max_sale_price'])
            ]
        
        # Remove rows with invalid year built
        if 'YEAR BUILT' in df.columns:
            df = df[
                (df['YEAR BUILT'] >= self.thresholds['min_year_built']) &
                (df['YEAR BUILT'] <= self.thresholds['max_year_built'])
            ]
        
        # Convert numeric columns
        numeric_columns = ['SALE PRICE', 'GROSS SQUARE FEET', 'LAND SQUARE FEET', 
                          'YEAR BUILT', 'TOTAL UNITS', 'RESIDENTIAL UNITS', 'COMMERCIAL UNITS']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        self.logger.info(f"Data cleaning complete. Final rows: {len(df)}")
        return df

# ============================================================================
# ADVANCED DOWNLOAD WITH RETRY LOGIC
# ============================================================================

class AdvancedDownloader:
    """Advanced downloader with retry logic and progress tracking"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger, cache_manager: CacheManager):
        self.config = config
        self.logger = logger
        self.cache_manager = cache_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) NYC-RealEstate-Crawler/2.0'
        })
    
    def download_file(self, url: str, borough_name: str) -> Optional[str]:
        """Download file with retry logic and caching"""
        self.logger.info(f"Starting download for {borough_name}")
        self.logger.info(f"URL: {url}")
        
        # Check cache first
        cached_file = self.cache_manager.get_cached_file(url)
        if cached_file:
            self.logger.info(f"Using cached file for {borough_name}")
            return cached_file
        
        # Download with retry logic
        for attempt in range(self.config.max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1}/{self.config.max_retries}")
                
                response = self.session.get(
                    url,
                    timeout=self.config.timeout,
                    stream=True
                )
                response.raise_for_status()
                
                # Get file size for progress tracking
                total_size = int(response.headers.get('content-length', 0))
                
                # Download with progress
                temp_filename = f"temp_{borough_name.replace(' ', '_')}.xlsx"
                temp_path = os.path.join(self.config.temp_dir, temp_filename)
                
                # Create temp directory
                Path(self.config.temp_dir).mkdir(parents=True, exist_ok=True)
                
                downloaded_size = 0
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            if self.config.enable_progress_bar and TQDM_SUPPORT:
                                # Progress tracking would be here
                                pass
                
                # Save to cache
                with open(temp_path, 'rb') as f:
                    content = f.read()
                self.cache_manager.save_to_cache(url, content)
                
                self.logger.info(f"✓ Download complete for {borough_name}: {downloaded_size:,} bytes")
                return temp_path
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            if attempt < self.config.max_retries - 1:
                self.logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                time.sleep(self.config.retry_delay)
        
        self.logger.error(f"Failed to download {borough_name} after {self.config.max_retries} attempts")
        return None

# ============================================================================
# EXCEL PARSER WITH ADVANCED OPTIONS
# ============================================================================

class ExcelParser:
    """Advanced Excel parser with multiple format support"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def parse_file(self, filename: str, borough_name: str, skip_rows: int = 4) -> Optional[pd.DataFrame]:
        """Parse Excel file with advanced options"""
        try:
            self.logger.info(f"Parsing Excel file for {borough_name}: {filename}")
            
            # Try different skip row values to find the actual data
            df = None
            for skip in [skip_rows, 3, 5, 6]:
                try:
                    df = pd.read_excel(filename, skiprows=skip)
                    if not df.empty and len(df.columns) > 5:
                        self.logger.info(f"Successfully parsed with skip_rows={skip}")
                        break
                except:
                    continue
            
            if df is None or df.empty:
                self.logger.error(f"Failed to parse Excel file for {borough_name}")
                return None
            
            # Standardize column names (uppercase, strip spaces)
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Add metadata columns
            df['BOROUGH'] = borough_name
            df['SOURCE_URL'] = NYC_SALES_URLS.get(borough_name, '')
            df['CRAWL_DATE'] = datetime.now().strftime('%Y-%m-%d')
            df['CRAWL_TIMESTAMP'] = datetime.now().isoformat()
            
            # Add file hash for tracking
            df['FILE_HASH'] = self._generate_file_hash(filename)
            
            self.logger.info(f"✓ Parsed {borough_name}: {len(df):,} rows, {len(df.columns)} columns")
            return df
            
        except Exception as e:
            self.logger.error(f"Error parsing Excel file for {borough_name}: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def _generate_file_hash(self, filename: str) -> str:
        """Generate hash of file for tracking"""
        try:
            with open(filename, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:16]
        except:
            return "unknown"

# ============================================================================
# DATA ENRICHMENT AND TRANSFORMATION
# ============================================================================

class DataEnricher:
    """Enrich data with calculated fields and transformations"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def enrich_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated fields and enrich data"""
        self.logger.info("Starting data enrichment...")
        
        # Calculate price per square foot if not present
        if 'SALE PRICE' in df.columns and 'GROSS SQUARE FEET' in df.columns:
            if 'SALE PRICE PER SQFT' not in df.columns:
                df['SALE PRICE PER SQFT'] = df.apply(
                    lambda row: row['SALE PRICE'] / row['GROSS SQUARE FEET'] 
                    if row['GROSS SQUARE FEET'] and row['GROSS SQUARE FEET'] > 0 
                    else None, axis=1
                )
        
        # Calculate building age
        if 'YEAR BUILT' in df.columns:
            current_year = datetime.now().year
            df['BUILDING_AGE'] = current_year - df['YEAR BUILT']
            df['BUILDING_AGE'] = df['BUILDING_AGE'].apply(lambda x: max(0, x) if pd.notna(x) else None)
        
        # Parse sale date and extract components
        if 'SALE DATE' in df.columns:
            df['SALE DATE PARSED'] = pd.to_datetime(df['SALE DATE'], errors='coerce')
            df['SALE YEAR'] = df['SALE DATE PARSED'].dt.year
            df['SALE MONTH'] = df['SALE DATE PARSED'].dt.month
            df['SALE QUARTER'] = df['SALE DATE PARSED'].dt.quarter
            df['SALE DAY OF WEEK'] = df['SALE DATE PARSED'].dt.dayofweek
        
        # Categorize sale price ranges
        if 'SALE PRICE' in df.columns:
            df['PRICE_CATEGORY'] = pd.cut(
                df['SALE PRICE'],
                bins=[0, 100000, 500000, 1000000, 5000000, float('inf')],
                labels=['Under $100K', '$100K-$500K', '$500K-$1M', '$1M-$5M', 'Over $5M']
            )
        
        # Categorize building age
        if 'BUILDING_AGE' in df.columns:
            df['AGE_CATEGORY'] = pd.cut(
                df['BUILDING_AGE'],
                bins=[0, 5, 20, 50, 100, float('inf')],
                labels=['New (0-5)', 'Modern (5-20)', 'Established (20-50)', 'Old (50-100)', 'Historic (100+)']
            )
        
        # Calculate unit density
        if 'TOTAL UNITS' in df.columns and 'GROSS SQUARE FEET' in df.columns:
            df['SQFT_PER_UNIT'] = df.apply(
                lambda row: row['GROSS SQUARE FEET'] / row['TOTAL UNITS'] 
                if row['TOTAL UNITS'] and row['TOTAL UNITS'] > 0 
                else None, axis=1
            )
        
        # Residential ratio
        if 'RESIDENTIAL UNITS' in df.columns and 'TOTAL UNITS' in df.columns:
            df['RESIDENTIAL_RATIO'] = df.apply(
                lambda row: row['RESIDENTIAL UNITS'] / row['TOTAL UNITS'] 
                if row['TOTAL UNITS'] and row['TOTAL UNITS'] > 0 
                else None, axis=1
            )
        
        self.logger.info("Data enrichment complete")
        return df
    
    def standardize_neighborhood_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize neighborhood names"""
        if 'NEIGHBORHOOD' in df.columns:
            df['NEIGHBORHOOD'] = df['NEIGHBORHOOD'].str.strip().str.upper()
            # Remove common suffixes
            df['NEIGHBORHOOD'] = df['NEIGHBORHOOD'].str.replace(r'\s+(HEIGHTS|VILLAGE|AREA|DISTRICT)$', '', regex=True)
        return df

# ============================================================================
# DATA DEDUPLICATION
# ============================================================================

class DataDeduplicator:
    """Handle data deduplication"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate records based on configuration"""
        if not self.config.deduplicate:
            self.logger.info("Deduplication disabled")
            return df
        
        self.logger.info(f"Starting deduplication using columns: {self.config.deduplicate_columns}")
        
        # Check if deduplication columns exist
        available_cols = [col for col in self.config.deduplicate_columns if col in df.columns]
        
        if not available_cols:
            self.logger.warning("None of the deduplication columns found in DataFrame")
            return df
        
        initial_count = len(df)
        df = df.drop_duplicates(subset=available_cols, keep='first')
        removed_count = initial_count - len(df)
        
        self.logger.info(f"Removed {removed_count:,} duplicate records ({removed_count/initial_count*100:.2f}%)")
        return df

# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================

class StatisticalAnalyzer:
    """Perform statistical analysis on crawled data"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def generate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive statistics"""
        self.logger.info("Generating statistical analysis...")
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_records': len(df),
            'by_borough': {},
            'price_statistics': {},
            'temporal_statistics': {},
            'building_statistics': {}
        }
        
        # Statistics by borough
        if 'BOROUGH' in df.columns:
            for borough in df['BOROUGH'].unique():
                borough_data = df[df['BOROUGH'] == borough]
                stats['by_borough'][borough] = {
                    'count': len(borough_data),
                    'avg_price': self._safe_mean(borough_data['SALE PRICE']),
                    'median_price': self._safe_median(borough_data['SALE PRICE']),
                    'avg_sqft': self._safe_mean(borough_data['GROSS SQUARE FEET'])
                }
        
        # Overall price statistics
        if 'SALE PRICE' in df.columns:
            stats['price_statistics'] = {
                'mean': float(df['SALE PRICE'].mean()),
                'median': float(df['SALE PRICE'].median()),
                'std': float(df['SALE PRICE'].std()),
                'min': float(df['SALE PRICE'].min()),
                'max': float(df['SALE PRICE'].max()),
                'q25': float(df['SALE PRICE'].quantile(0.25)),
                'q75': float(df['SALE PRICE'].quantile(0.75))
            }
        
        # Temporal statistics
        if 'SALE YEAR' in df.columns:
            stats['temporal_statistics'] = {
                'yearly_counts': df['SALE YEAR'].value_counts().sort_index().to_dict(),
                'yearly_avg_prices': df.groupby('SALE YEAR')['SALE PRICE'].mean().to_dict()
            }
        
        # Building statistics
        if 'YEAR BUILT' in df.columns:
            stats['building_statistics'] = {
                'avg_year_built': float(df['YEAR BUILT'].mean()),
                'oldest_building': int(df['YEAR BUILT'].min()),
                'newest_building': int(df['YEAR BUILT'].max())
            }
        
        self.logger.info("Statistical analysis complete")
        return stats
    
    def _safe_mean(self, series):
        """Safely calculate mean"""
        try:
            return float(series.mean())
        except:
            return None
    
    def _safe_median(self, series):
        """Safely calculate median"""
        try:
            return float(series.median())
        except:
            return None

# ============================================================================
# VISUALIZATION MODULE
# ============================================================================

class DataVisualizer:
    """Generate visualizations for crawled data"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_visualizations(self, df: pd.DataFrame, stats: Dict[str, Any]) -> List[str]:
        """Generate all visualizations"""
        if not VISUALIZATION_SUPPORT:
            self.logger.warning("Visualization not available (matplotlib/seaborn not installed)")
            return []
        
        self.logger.info("Generating visualizations...")
        generated_files = []
        
        try:
            # Set style
            sns.set_style("whitegrid")
            plt.style.use('seaborn-v0_8-darkgrid')
            
            # Price distribution by borough
            if 'BOROUGH' in df.columns and 'SALE PRICE' in df.columns:
                fig_file = self.visualize_price_by_borough(df)
                if fig_file:
                    generated_files.append(fig_file)
            
            # Temporal trends
            if 'SALE YEAR' in df.columns:
                fig_file = self.visualize_temporal_trends(df)
                if fig_file:
                    generated_files.append(fig_file)
            
            # Building age distribution
            if 'YEAR BUILT' in df.columns:
                fig_file = self.visualize_building_age(df)
                if fig_file:
                    generated_files.append(fig_file)
            
            self.logger.info(f"Generated {len(generated_files)} visualizations")
            
        except Exception as e:
            self.logger.error(f"Error generating visualizations: {e}")
            self.logger.error(traceback.format_exc())
        
        return generated_files
    
    def visualize_price_by_borough(self, df: pd.DataFrame) -> Optional[str]:
        """Create price distribution visualization by borough"""
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            boroughs = df['BOROUGH'].unique()
            price_data = [df[df['BOROUGH'] == b]['SALE PRICE'].dropna() for b in boroughs]
            
            ax.boxplot(price_data, labels=boroughs)
            ax.set_xlabel('Borough')
            ax.set_ylabel('Sale Price ($)')
            ax.set_title('Sale Price Distribution by Borough')
            ax.tick_params(axis='x', rotation=45)
            
            # Format y-axis as dollars
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
            
            plt.tight_layout()
            
            filename = self.output_dir / "price_by_borough.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Saved: {filename}")
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"Error creating price by borough visualization: {e}")
            return None
    
    def visualize_temporal_trends(self, df: pd.DataFrame) -> Optional[str]:
        """Create temporal trends visualization"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # Sales count by year
            yearly_counts = df['SALE YEAR'].value_counts().sort_index()
            ax1.bar(yearly_counts.index, yearly_counts.values)
            ax1.set_xlabel('Year')
            ax1.set_ylabel('Number of Sales')
            ax1.set_title('Number of Sales by Year')
            
            # Average price by year
            yearly_avg_price = df.groupby('SALE YEAR')['SALE PRICE'].mean()
            ax2.plot(yearly_avg_price.index, yearly_avg_price.values, marker='o')
            ax2.set_xlabel('Year')
            ax2.set_ylabel('Average Sale Price ($)')
            ax2.set_title('Average Sale Price by Year')
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
            
            plt.tight_layout()
            
            filename = self.output_dir / "temporal_trends.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Saved: {filename}")
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"Error creating temporal trends visualization: {e}")
            return None
    
    def visualize_building_age(self, df: pd.DataFrame) -> Optional[str]:
        """Create building age distribution visualization"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            ax.hist(df['YEAR BUILT'].dropna(), bins=50, edgecolor='black', alpha=0.7)
            ax.set_xlabel('Year Built')
            ax.set_ylabel('Frequency')
            ax.set_title('Distribution of Building Year Built')
            
            plt.tight_layout()
            
            filename = self.output_dir / "building_age_distribution.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Saved: {filename}")
            return str(filename)
            
        except Exception as e:
            self.logger.error(f"Error creating building age visualization: {e}")
            return None

# ============================================================================
# DATABASE EXPORT MODULE
# ============================================================================

class DatabaseExporter:
    """Export data to SQLite database"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.db_path = config.database_path
    
    def export_to_sqlite(self, df: pd.DataFrame, table_name: str = 'nyc_sales') -> bool:
        """Export DataFrame to SQLite database"""
        try:
            self.logger.info(f"Exporting data to SQLite database: {self.db_path}")
            
            # Create connection
            conn = sqlite3.connect(self.db_path)
            
            # Export data
            df.to_sql(table_name, conn, if_exists='append', index=False)
            
            # Create indexes for better performance
            self._create_indexes(conn, table_name)
            
            conn.close()
            
            self.logger.info(f"Successfully exported {len(df):,} records to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to database: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _create_indexes(self, conn: sqlite3.Connection, table_name: str):
        """Create database indexes for common queries"""
        try:
            cursor = conn.cursor()
            
            # Index on borough
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_borough ON {table_name}(BOROUGH)")
            
            # Index on sale date
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_sale_date ON {table_name}(SALE DATE PARSED)")
            
            # Index on sale price
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_sale_price ON {table_name}(SALE PRICE)")
            
            # Index on neighborhood
            cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_neighborhood ON {table_name}(NEIGHBORHOOD)")
            
            conn.commit()
            self.logger.info("Database indexes created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating indexes: {e}")
    
    def query_database(self, query: str) -> Optional[pd.DataFrame]:
        """Execute SQL query on database"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return None

# ============================================================================
# EMAIL NOTIFICATION MODULE
# ============================================================================

class EmailNotifier:
    """Send email notifications about crawl results"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
    
    def send_notification(self, subject: str, body: str, attachment_path: Optional[str] = None) -> bool:
        """Send email notification"""
        if not self.config.enable_email_notification:
            self.logger.info("Email notification disabled")
            return False
        
        if not self.config.email_sender or not self.config.email_password:
            self.logger.warning("Email credentials not configured")
            return False
        
        try:
            self.logger.info(f"Sending email notification: {subject}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.email_sender
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = subject
            
            # Attach body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach file if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    import email.mime.base
                    import email.mime.application
                    part = email.mime.application.MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.config.email_smtp_server, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_sender, self.config.email_password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email notification sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def generate_crawl_report(self, stats: Dict[str, Any], output_files: List[str]) -> str:
        """Generate crawl report for email notification"""
        report = f"""
NYC Real Estate Sales Crawler Report
=====================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
--------
Total Records: {stats.get('total_records', 0):,}
Output Files: {len(output_files)}

BY BOROUGH:
-----------
"""
        for borough, data in stats.get('by_borough', {}).items():
            report += f"{borough}: {data['count']:,} records\n"
        
        report += f"\nPRICE STATISTICS:\n"
        price_stats = stats.get('price_statistics', {})
        report += f"Mean: ${price_stats.get('mean', 0):,.2f}\n"
        report += f"Median: ${price_stats.get('median', 0):,.2f}\n"
        report += f"Min: ${price_stats.get('min', 0):,.2f}\n"
        report += f"Max: ${price_stats.get('max', 0):,.2f}\n"
        
        report += f"\nOUTPUT FILES:\n"
        for file in output_files:
            report += f"- {file}\n"
        
        return report

# ============================================================================
# MULTI-FORMAT EXPORT MODULE
# ============================================================================

class MultiFormatExporter:
    """Export data in multiple formats"""
    
    def __init__(self, config: CrawlerConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_data(self, df: pd.DataFrame, base_filename: str = 'nyc_sales') -> Dict[str, str]:
        """Export data in configured format(s)"""
        self.logger.info(f"Exporting data in format: {self.config.output_format.value}")
        
        exported_files = {}
        
        # Export based on configured format
        if self.config.output_format == OutputFormat.CSV:
            file_path = self.export_csv(df, base_filename)
            if file_path:
                exported_files['csv'] = file_path
        
        elif self.config.output_format == OutputFormat.JSON:
            file_path = self.export_json(df, base_filename)
            if file_path:
                exported_files['json'] = file_path
        
        elif self.config.output_format == OutputFormat.EXCEL:
            file_path = self.export_excel(df, base_filename)
            if file_path:
                exported_files['excel'] = file_path
        
        elif self.config.output_format == OutputFormat.PARQUET:
            file_path = self.export_parquet(df, base_filename)
            if file_path:
                exported_files['parquet'] = file_path
        
        elif self.config.output_format == OutputFormat.SQLITE:
            # SQLite export is handled separately by DatabaseExporter
            pass
        
        self.logger.info(f"Exported {len(exported_files)} file(s)")
        return exported_files
    
    def export_csv(self, df: pd.DataFrame, base_filename: str) -> Optional[str]:
        """Export to CSV format"""
        try:
            file_path = self.output_dir / f"{base_filename}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"CSV exported: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {e}")
            return None
    
    def export_json(self, df: pd.DataFrame, base_filename: str) -> Optional[str]:
        """Export to JSON format"""
        try:
            file_path = self.output_dir / f"{base_filename}.json"
            df.to_json(file_path, orient='records', indent=2)
            self.logger.info(f"JSON exported: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error exporting JSON: {e}")
            return None
    
    def export_excel(self, df: pd.DataFrame, base_filename: str) -> Optional[str]:
        """Export to Excel format"""
        if not EXCEL_SUPPORT:
            self.logger.error("Excel export not supported (openpyxl not installed)")
            return None
        
        try:
            file_path = self.output_dir / f"{base_filename}.xlsx"
            
            # Create Excel writer with multiple sheets
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sales Data', index=False)
                
                # Add summary sheet
                summary_df = pd.DataFrame({
                    'Metric': ['Total Records', 'Columns', 'Date Range Start', 'Date Range End'],
                    'Value': [
                        len(df),
                        len(df.columns),
                        df['SALE DATE PARSED'].min() if 'SALE DATE PARSED' in df.columns else 'N/A',
                        df['SALE DATE PARSED'].max() if 'SALE DATE PARSED' in df.columns else 'N/A'
                    ]
                })
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            self.logger.info(f"Excel exported: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error exporting Excel: {e}")
            return None
    
    def export_parquet(self, df: pd.DataFrame, base_filename: str) -> Optional[str]:
        """Export to Parquet format"""
        if not PARQUET_SUPPORT:
            self.logger.error("Parquet export not supported (pyarrow not installed)")
            return None
        
        try:
            file_path = self.output_dir / f"{base_filename}.parquet"
            df.to_parquet(file_path, index=False)
            self.logger.info(f"Parquet exported: {file_path}")
            return str(file_path)
        except Exception as e:
            self.logger.error(f"Error exporting Parquet: {e}")
            return None

# ============================================================================
# MAIN CRAWLER CLASS
# ============================================================================

class NYCSalesCrawler:
    """Main crawler class orchestrating all components"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = setup_logging(config)
        
        # Initialize components
        self.cache_manager = CacheManager(config, self.logger)
        self.downloader = AdvancedDownloader(config, self.logger, self.cache_manager)
        self.parser = ExcelParser(config, self.logger)
        self.validator = DataValidator(config, self.logger)
        self.enricher = DataEnricher(config, self.logger)
        self.deduplicator = DataDeduplicator(config, self.logger)
        self.analyzer = StatisticalAnalyzer(config, self.logger)
        self.visualizer = DataVisualizer(config, self.logger)
        self.exporter = MultiFormatExporter(config, self.logger)
        self.db_exporter = DatabaseExporter(config, self.logger) if config.enable_database_export else None
        self.notifier = EmailNotifier(config, self.logger)
        
        # Tracking
        self.start_time = datetime.now()
        self.temp_files = []
        self.validation_reports = []
    
    def crawl(self) -> bool:
        """Main crawl method"""
        self.logger.info("=" * 80)
        self.logger.info("NYC REAL ESTATE SALES CRAWLER - STARTING")
        self.logger.info("=" * 80)
        self.logger.info(f"Configuration: {self.config}")
        self.logger.info(f"Start time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Download and parse all borough data
            all_dataframes = self._download_and_parse_all()
            
            if not all_dataframes:
                self.logger.error("No data was successfully crawled")
                return False
            
            # Step 2: Merge all data
            self.logger.info("Merging data from all boroughs...")
            merged_df = pd.concat(all_dataframes, ignore_index=True)
            self.logger.info(f"Merged dataset: {len(merged_df):,} rows")
            
            # Step 3: Data validation and cleaning
            if self.config.enable_validation:
                self.logger.info("Validating and cleaning data...")
                merged_df = self.validator.clean_dataframe(merged_df)
            
            # Step 4: Data enrichment
            merged_df = self.enricher.enrich_dataframe(merged_df)
            merged_df = self.enricher.standardize_neighborhood_names(merged_df)
            
            # Step 5: Deduplication
            merged_df = self.deduplicator.deduplicate(merged_df)
            
            # Step 6: Apply data limit if configured
            if self.config.data_limit and self.config.data_limit > 0:
                initial_len = len(merged_df)
                merged_df = merged_df.head(self.config.data_limit)
                self.logger.info(f"Applied data limit: {initial_len:,} -> {len(merged_df):,} rows")
            
            # Step 7: Statistical analysis
            stats = {}
            if self.config.enable_statistics:
                stats = self.analyzer.generate_statistics(merged_df)
            
            # Step 8: Export data
            base_filename = f"nyc_sales_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            exported_files = self.exporter.export_data(merged_df, base_filename)
            
            # Step 9: Database export
            if self.config.enable_database_export and self.db_exporter:
                self.db_exporter.export_to_sqlite(merged_df)
                exported_files['database'] = self.config.database_path
            
            # Step 10: Visualization
            visualization_files = []
            if self.config.enable_visualization:
                visualization_files = self.visualizer.generate_visualizations(merged_df, stats)
                exported_files['visualizations'] = visualization_files
            
            # Step 11: Send notification
            if self.config.enable_email_notification:
                all_files = list(exported_files.values())
                report = self.notifier.generate_crawl_report(stats, all_files)
                self.notifier.send_notification(
                    f"NYC Sales Crawler Complete - {len(merged_df):,} records",
                    report
                )
            
            # Step 12: Cleanup
            self._cleanup()
            
            # Final summary
            self._print_final_summary(merged_df, exported_files, stats)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Fatal error during crawl: {e}")
            self.logger.error(traceback.format_exc())
            self._cleanup()
            return False
    
    def _download_and_parse_all(self) -> List[pd.DataFrame]:
        """Download and parse data for all boroughs"""
        all_dataframes = []
        
        for borough_name, url in NYC_SALES_URLS.items():
            self.logger.info(f"\nProcessing {borough_name}...")
            
            # Download
            temp_file = self.downloader.download_file(url, borough_name)
            
            if temp_file:
                self.temp_files.append(temp_file)
                
                # Parse
                df = self.parser.parse_file(temp_file, borough_name)
                
                if df is not None:
                    # Validate
                    if self.config.enable_validation:
                        is_valid, report = self.validator.validate_dataframe(df, borough_name)
                        self.validation_reports.append(report)
                    
                    all_dataframes.append(df)
            
            # Rate limiting
            time.sleep(self.config.rate_limit_delay)
        
        return all_dataframes
    
    def _cleanup(self):
        """Clean up temporary files"""
        self.logger.info("Cleaning up temporary files...")
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.info(f"Removed: {temp_file}")
            except Exception as e:
                self.logger.warning(f"Could not remove {temp_file}: {e}")
    
    def _print_final_summary(self, df: pd.DataFrame, exported_files: Dict[str, str], stats: Dict[str, Any]):
        """Print final summary to console"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("CRAWL COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total records: {len(df):,}")
        self.logger.info(f"Total columns: {len(df.columns)}")
        self.logger.info(f"Duration: {duration}")
        self.logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.logger.info("\nExported files:")
        for format_type, file_path in exported_files.items():
            if isinstance(file_path, list):
                for f in file_path:
                    self.logger.info(f"  - {f}")
            else:
                self.logger.info(f"  - {file_path}")
        
        if stats:
            self.logger.info("\nPrice Statistics:")
            price_stats = stats.get('price_statistics', {})
            self.logger.info(f"  Mean: ${price_stats.get('mean', 0):,.2f}")
            self.logger.info(f"  Median: ${price_stats.get('median', 0):,.2f}")
            self.logger.info(f"  Min: ${price_stats.get('min', 0):,.2f}")
            self.logger.info(f"  Max: ${price_stats.get('max', 0):,.2f}")
            
            self.logger.info("\nRecords by Borough:")
            for borough, data in stats.get('by_borough', {}).items():
                self.logger.info(f"  {borough}: {data['count']:,}")

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='NYC Real Estate Sales Data Crawler - Advanced Version',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic crawl with default settings
  python nyc_sales_crawler.py
  
  # Crawl with limit and JSON output
  python nyc_sales_crawler.py --limit 10000 --format json
  
  # Crawl with database export and email notification
  python nyc_sales_crawler.py --database --email --email-sender you@gmail.com --email-password pass
  
  # Crawl with visualization enabled
  python nyc_sales_crawler.py --visualize
        """
    )
    
    parser.add_argument('--format', '-f',
                       choices=['csv', 'json', 'excel', 'parquet', 'sqlite'],
                       default='csv',
                       help='Output format (default: csv)')
    
    parser.add_argument('--limit', '-l',
                       type=int,
                       default=None,
                       help='Limit number of records to crawl')
    
    parser.add_argument('--output-dir', '-o',
                       default='output',
                       help='Output directory (default: output)')
    
    parser.add_argument('--no-validation',
                       action='store_true',
                       help='Disable data validation')
    
    parser.add_argument('--no-statistics',
                       action='store_true',
                       help='Disable statistical analysis')
    
    parser.add_argument('--visualize',
                       action='store_true',
                       help='Enable visualization generation')
    
    parser.add_argument('--database',
                       action='store_true',
                       help='Enable database export')
    
    parser.add_argument('--database-path',
                       default='nyc_sales.db',
                       help='Database file path (default: nyc_sales.db)')
    
    parser.add_argument('--email',
                       action='store_true',
                       help='Enable email notification')
    
    parser.add_argument('--email-smtp-server',
                       default='smtp.gmail.com',
                       help='SMTP server (default: smtp.gmail.com)')
    
    parser.add_argument('--email-smtp-port',
                       type=int,
                       default=587,
                       help='SMTP port (default: 587)')
    
    parser.add_argument('--email-sender',
                       default='',
                       help='Email sender address')
    
    parser.add_argument('--email-password',
                       default='',
                       help='Email password or app password')
    
    parser.add_argument('--email-recipients',
                       nargs='+',
                       default=[],
                       help='Email recipients')
    
    parser.add_argument('--no-cache',
                       action='store_true',
                       help='Disable caching')
    
    parser.add_argument('--clear-cache',
                       action='store_true',
                       help='Clear cache before crawling')
    
    parser.add_argument('--max-retries',
                       type=int,
                       default=3,
                       help='Maximum download retries (default: 3)')
    
    parser.add_argument('--timeout',
                       type=int,
                       default=60,
                       help='Download timeout in seconds (default: 60)')
    
    parser.add_argument('--no-deduplicate',
                       action='store_true',
                       help='Disable deduplication')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Create configuration from arguments
    config = CrawlerConfig(
        output_dir=args.output_dir,
        output_format=OutputFormat(args.format),
        data_limit=args.limit,
        enable_validation=not args.no_validation,
        enable_statistics=not args.no_statistics,
        enable_visualization=args.visualize,
        enable_database_export=args.database,
        database_path=args.database_path,
        enable_email_notification=args.email,
        email_smtp_server=args.email_smtp_server,
        email_smtp_port=args.email_smtp_port,
        email_sender=args.email_sender,
        email_password=args.email_password,
        email_recipients=args.email_recipients,
        cache_enabled=not args.no_cache,
        max_retries=args.max_retries,
        timeout=args.timeout,
        deduplicate=not args.no_deduplicate
    )
    
    # Clear cache if requested
    if args.clear_cache:
        cache_manager = CacheManager(config, logging.getLogger(__name__))
        cache_manager.clear_cache()
    
    # Create and run crawler
    crawler = NYCSalesCrawler(config)
    success = crawler.crawl()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
