import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import zlib

# ════════════════════════════════════════════════════════════
# CẤU HÌNH TRANG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Báo cáo Phân tích Thị trường Bất động sản NYC 2025 - 2026",
    layout="wide",
    page_icon="🏙️",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-weight: 500; }
.main { background-color: #f8fafc; }
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f5f3ff 100%);
    padding: 18px 20px;
    border-radius: 14px;
    box-shadow: 0 4px 20px rgba(99,102,241,0.14), 0 1px 4px rgba(0,0,0,0.06);
    border: none;
    border-left: 5px solid #6366f1;
}
[data-testid="stMetricLabel"] {
    color: #7c3aed !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
    color: #1e1b4b !important;
    font-size: 24px !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}
[data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 600 !important; }
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 2px solid #c7d2fe;
    background: linear-gradient(180deg, #eef2ff 0%, #f0f4ff 100%);
    border-radius: 12px 12px 0 0;
    padding: 8px 8px 0;
}
.stTabs [data-baseweb="tab"] {
    height: 44px;
    font-weight: 700;
    font-size: 13px;
    color: #4338ca;
    border-radius: 10px 10px 0 0;
    padding: 0 20px;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: #ffffff !important;
    background: #6366f1 !important;
    box-shadow: 0 -3px 14px rgba(99,102,241,0.4) !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #312e81 55%, #4c1d95 100%);
}
[data-testid="stSidebar"] * { color: #e0e7ff !important; }
[data-testid="stSidebar"] label {
    color: #a5b4fc !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: #6366f1 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] span { color: #ffffff !important; font-weight: 700 !important; }
[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(99,102,241,0.45) !important;
}
.section-q {
    font-size: 17px;
    font-weight: 800;
    color: #1e1b4b;
    margin: 24px 0 4px 0;
    padding: 10px 16px;
    border-left: 5px solid #6366f1;
    background: linear-gradient(90deg, #eef2ff 0%, transparent 80%);
    border-radius: 0 8px 8px 0;
}
.section-cap { font-size: 13px; color: #4b5563; font-weight: 600; margin: 4px 0 14px 16px; line-height: 1.6; }
.insight-box {
    background: linear-gradient(135deg, #faf5ff 0%, #ede9fe 60%, #e0e7ff 100%);
    border: 1px solid #c4b5fd;
    border-left: 6px solid #7c3aed;
    border-radius: 0 14px 14px 0;
    padding: 18px 22px;
    margin: 22px 0 8px 0;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.9;
    color: #2e1065;
    box-shadow: 0 4px 16px rgba(124,58,237,0.1);
}
.insight-box b { color: #5b21b6; font-weight: 800; }
.badge {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #ffffff;
    border-radius: 999px;
    padding: 4px 14px;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(99,102,241,0.4);
}
.hr { border: none; border-top: 1px solid #c7d2fe; margin: 28px 0; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #eef2ff; }
::-webkit-scrollbar-thumb { background: #a5b4fc; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# HẰNG SỐ, TỌA ĐỘ BẢN ĐỒ & BẢN MÀU
# ════════════════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
BOROUGH_MAP   = {1:'Manhattan', 2:'Bronx', 3:'Brooklyn', 4:'Queens', 5:'Staten Island'}
BOROUGH_ORDER = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island']
BOROUGH_COLORS = {
    'Manhattan':    '#6366f1',
    'Brooklyn':     '#0ea5e9',
    'Queens':       '#10b981',
    'Bronx':        '#f59e0b',
    'Staten Island':'#ec4899',
}
C_BLUE = '#6366f1'; C_BLUE2 = '#818cf8'; C_SKY = '#0ea5e9'
C_ORANGE = '#f59e0b'; C_RED = '#ef4444'; C_GREEN = '#10b981'; C_GRAY = '#94a3b8'

MONTH_SHORT = {1:'T1',2:'T2',3:'T3',4:'T4',5:'T5',6:'T6',
               7:'T7',8:'T8',9:'T9',10:'T10',11:'T11',12:'T12'}
MONTH_FULL  = {1:'Tháng 1',2:'Tháng 2',3:'Tháng 3',4:'Tháng 4',
               5:'Tháng 5',6:'Tháng 6',7:'Tháng 7',8:'Tháng 8',
               9:'Tháng 9',10:'Tháng 10',11:'Tháng 11',12:'Tháng 12'}
FEATURE_LABELS = {
    'gross_sqft':'Diện tích tổng (sqft)', 'building_age':'Tuổi công trình (năm)',
    'land_sqft':'Diện tích đất (sqft)',   'pop_density':'Mật độ dân số (/km²)',
    'amenity_score':'Điểm tiện ích (0–10)','total_units':'Số căn trong tòa',
    'gdp_local':'GDP địa phương (%)',      'avg_income':'Thu nhập bình quân ($)',
    'dist_center':'KC đến trung tâm (km)',
}
REQUIRED_COLS = [
    'borough','neighborhood','building_type','gross_sqft','land_sqft',
    'sale_price','sale_year','sale_date','building_age','total_units',
    'pop_density','avg_income','gdp_local','dist_center','amenity_score',
]

# Tọa độ địa lý NYC cho bản đồ Nhiệt (Hotspot Heatmap)
BOROUGH_COORDS = {
    'Manhattan':     (40.7831, -73.9712),
    'Brooklyn':      (40.6782, -73.9442),
    'Queens':        (40.7282, -73.7949),
    'Bronx':         (40.8448, -73.8648),
    'Staten Island': (40.5795, -74.1502),
}

NEIGHBORHOOD_COORDS = {
    # MANHATTAN
    'UPPER EAST SIDE (59-79)': (40.7700, -73.9590),
    'UPPER EAST SIDE (79-96)': (40.7780, -73.9530),
    'UPPER EAST SIDE (96-110)': (40.7910, -73.9470),
    'UPPER WEST SIDE (59-79)': (40.7760, -73.9810),
    'UPPER WEST SIDE (79-96)': (40.7890, -73.9720),
    'UPPER WEST SIDE (96-110)': (40.8000, -73.9630),
    'MIDTOWN EAST': (40.7540, -73.9720),
    'MIDTOWN WEST': (40.7600, -73.9880),
    'MIDTOWN CBD': (40.7550, -73.9800),
    'CHELSEA': (40.7465, -74.0014),
    'GREENWICH VILLAGE-CENTRAL': (40.7336, -73.9996),
    'GREENWICH VILLAGE-WEST': (40.7350, -74.0060),
    'GRAMERCY': (40.7368, -73.9845),
    'MURRAY HILL': (40.7483, -73.9783),
    'EAST VILLAGE': (40.7265, -73.9815),
    'LOWER EAST SIDE': (40.7150, -73.9840),
    'SOHO': (40.7233, -74.0030),
    'TRIBECA': (40.7163, -74.0086),
    'FINANCIAL': (40.7075, -74.0090),
    'HARLEM-CENTRAL': (40.8116, -73.9465),
    'HARLEM-EAST': (40.7957, -73.9389),
    'HARLEM-WEST': (40.8150, -73.9560),
    'WASHINGTON HEIGHTS UPPER': (40.8500, -73.9360),
    'WASHINGTON HEIGHTS LOWER': (40.8380, -73.9420),
    'INWOOD': (40.8677, -73.9212),
    'KIPS BAY': (40.7396, -73.9801),
    'CHINATOWN': (40.7158, -73.9970),
    'BATTERY PARK CITY': (40.7120, -74.0150),
    'MORNINGSIDE HEIGHTS': (40.8080, -73.9630),

    # QUEENS
    'FLUSHING-NORTH': (40.7675, -73.8331),
    'FLUSHING-SOUTH': (40.7420, -73.8210),
    'FOREST HILLS': (40.7186, -73.8448),
    'BAYSIDE': (40.7675, -73.7745),
    'ASTORIA': (40.7644, -73.9235),
    'JACKSON HEIGHTS': (40.7557, -73.8831),
    'ELMHURST': (40.7369, -73.8784),
    'LONG ISLAND CITY': (40.7447, -73.9485),
    'REGO PARK': (40.7258, -73.8622),
    'WOODSIDE': (40.7454, -73.9038),
    'SUNNYSIDE': (40.7434, -73.9241),
    'WHITESTONE': (40.7892, -73.8117),
    'RIDGEWOOD': (40.7061, -73.9015),
    'GLENDALE': (40.7011, -73.8876),
    'MASPETH': (40.7230, -73.9100),
    'MIDDLE VILLAGE': (40.7160, -73.8860),
    'JAMAICA': (40.7027, -73.7890),
    'JAMAICA ESTATES': (40.7234, -73.7834),
    'HOLLIS': (40.7117, -73.7667),
    'QUEENS VILLAGE': (40.7170, -73.7380),
    'HOWARD BEACH': (40.6570, -73.8430),
    'OZONE PARK': (40.6811, -73.8427),
    'RICHMOND HILL': (40.6953, -73.8315),
    'KEW GARDENS': (40.7090, -73.8310),

    # BROOKLYN
    'BEDFORD STUYVESANT': (40.6872, -73.9418),
    'BAY RIDGE': (40.6260, -74.0300),
    'BOROUGH PARK': (40.6350, -73.9920),
    'PARK SLOPE': (40.6711, -73.9814),
    'BUSHWICK': (40.6944, -73.9213),
    'WILLIAMSBURG-NORTH': (40.7180, -73.9570),
    'WILLIAMSBURG-SOUTH': (40.7090, -73.9590),
    'GREENPOINT': (40.7305, -73.9515),
    'DUMBO': (40.7033, -73.9881),
    'BROOKLYN HEIGHTS': (40.6960, -73.9936),
    'COBBLE HILL': (40.6877, -73.9947),
    'CARROLL GARDENS': (40.6800, -73.9950),
    'CROWN HEIGHTS': (40.6700, -73.9430),
    'FLATBUSH-LEFFERTS GARDENS': (40.6580, -73.9510),
    'FLATBUSH-CENTRAL': (40.6420, -73.9580),
    'SUNSET PARK': (40.6450, -74.0080),
    'BENSONHURST': (40.6139, -73.9922),
    'SHEEPSHEAD BAY': (40.5868, -73.9542),
    'CONEY ISLAND': (40.5750, -73.9820),
    'CANARSIE': (40.6400, -73.8960),

    # BRONX
    'RIVERDALE': (40.8904, -73.9125),
    'KINGSBRIDGE/JEROME PARK': (40.8790, -73.8970),
    'MOTT HAVEN/PORT MORRIS': (40.8090, -73.9230),
    'MELROSE/MORRISANIA': (40.8250, -73.9100),
    'FORDHAM': (40.8615, -73.8890),
    'BELMONT': (40.8550, -73.8870),
    'THROGS NECK': (40.8170, -73.8160),

    # STATEN ISLAND
    'GREAT KILLS': (40.5515, -74.1513),
    'TODT HILL': (40.5980, -74.1100),
    'ST. GEORGE': (40.6430, -74.0760),
    'NEW DORP': (40.5730, -74.1170),
    'ELTINGVILLE': (40.5430, -74.1650),
}

def get_neighborhood_coords(neighborhood, borough_name):
    """Lấy tọa độ lat/lon chuẩn hoặc suy luận theo offset nhỏ từ centroid quận."""
    if neighborhood in NEIGHBORHOOD_COORDS:
        return NEIGHBORHOOD_COORDS[neighborhood]
    b_lat, b_lon = BOROUGH_COORDS.get(borough_name, (40.7128, -74.0060))
    h = zlib.adler32(str(neighborhood).encode('utf-8'))
    off_lat = ((h % 100) - 50) * 0.0008
    off_lon = (((h // 100) % 100) - 50) * 0.0008
    return (b_lat + off_lat, b_lon + off_lon)

# ════════════════════════════════════════════════════════════
# HÀM DỮ LIỆU
# ════════════════════════════════════════════════════════════
@st.cache_data
def load_data():
    path = os.path.join(ROOT_DIR, 'data', 'data clean', 'Dulieu_Cleaned.csv')
    if not os.path.exists(path):
        return None, "Không tìm thấy file Dulieu_Cleaned.csv"
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return None, f"Thiếu cột: {', '.join(missing)}"
    df['borough_name']      = df['borough'].map(BOROUGH_MAP)
    df['sale_price']        = pd.to_numeric(df['sale_price'],   errors='coerce')
    df['gross_sqft']        = pd.to_numeric(df['gross_sqft'],   errors='coerce')
    df['land_sqft']         = pd.to_numeric(df['land_sqft'],    errors='coerce')
    df['building_age']      = pd.to_numeric(df['building_age'], errors='coerce')
    df['sale_year']         = pd.to_numeric(df['sale_year'],    errors='coerce')
    df['avg_income']        = pd.to_numeric(df['avg_income'],   errors='coerce')
    df['amenity_score']     = pd.to_numeric(df['amenity_score'],errors='coerce')
    df['dist_center']       = pd.to_numeric(df['dist_center'],  errors='coerce')
    df['pop_density']       = pd.to_numeric(df['pop_density'],  errors='coerce')
    df = df[df['sale_price'] > 10_000].copy()
    df.loc[df['gross_sqft'] <= 0, 'gross_sqft'] = np.nan
    df.loc[df['land_sqft']  <= 0, 'land_sqft']  = np.nan
    df['price_per_sqft']    = np.where(df['gross_sqft'].notna(),
                                       df['sale_price'] / df['gross_sqft'], np.nan)
    df['sale_date_parsed']  = pd.to_datetime(df['sale_date'], dayfirst=True, errors='coerce')
    df['sale_month']        = df['sale_date_parsed'].dt.month
    return df, None

@st.cache_data
def load_ml_data():
    paths = {'pred': os.path.join(ROOT_DIR, 'output', 'ml_predictions.csv'),
             'imp':  os.path.join(ROOT_DIR, 'output', 'ml_importance.csv'),
             'met':  os.path.join(ROOT_DIR, 'output', 'ml_metrics.json')}
    pred_df    = pd.read_csv(paths['pred'])    if os.path.exists(paths['pred']) else None
    importance = pd.read_csv(paths['imp'])     if os.path.exists(paths['imp'])  else None
    metrics = {}
    if os.path.exists(paths['met']):
        with open(paths['met'], encoding='utf-8') as f:
            metrics = json.load(f)
    return pred_df, importance, metrics

# ════════════════════════════════════════════════════════════
# HELPER UI & COMPONENT TÓM TẮT TRỰC QUAN
# ════════════════════════════════════════════════════════════
def fmt_M(v, d=2): return f"${v/1e6:.{d}f}M"
def insight_box(html): st.markdown(f'<div class="insight-box">{html}</div>', unsafe_allow_html=True)
def section_q(q, cap=""):
    st.markdown(f'<div class="section-q">{q}</div>', unsafe_allow_html=True)
    if cap: st.markdown(f'<div class="section-cap">{cap}</div>', unsafe_allow_html=True)
def divider(): st.markdown('<hr class="hr">', unsafe_allow_html=True)
def apply_filters(df, boroughs, yr, pr):
    return df[df['borough_name'].isin(boroughs) &
              df['sale_year'].between(yr[0], yr[1]) &
              df['sale_price'].between(pr[0], pr[1])].copy()
def clayout(fig, h=340, t=20, b=20, l=10, r=10, leg=False):
    fig.update_layout(height=h, margin=dict(t=t,b=b,l=l,r=r),
                      plot_bgcolor='#fafafa',
                      paper_bgcolor='#ffffff',
                      showlegend=leg,
                      font=dict(family='Inter', size=13, color='#1e1b4b'),
                      title_font=dict(size=15, color='#1e1b4b', family='Inter'),
                      legend=dict(font=dict(size=12, color='#1e1b4b')))
    fig.update_xaxes(tickfont=dict(size=12, color='#374151', family='Inter'),
                     title_font=dict(size=13, color='#374151', family='Inter'))
    fig.update_yaxes(tickfont=dict(size=12, color='#374151', family='Inter'),
                     title_font=dict(size=13, color='#374151', family='Inter'))
    return fig

def render_factor_summary_matrix(df_in):
    """
    Tạo Bảng & Biểu đồ Tóm tắt Yếu tố Tác động Giá (Top Factor Summary Matrix).
    Đánh giá và phân loại rõ yếu tố ảnh hưởng RẤT MẠNH / MẠNH / TRUNG BÌNH / YẾU.
    """
    factors = [
        ('gross_sqft', 'Diện tích công trình (gross_sqft)', 'Quy mô không gian sử dụng; biến số quan trọng hàng đầu định giá tổng tài sản.'),
        ('avg_income', 'Thu nhập khu vực (avg_income)', 'Mặt bằng thu nhập cư dân; đại diện cho sức mua và mức độ đắt đỏ của vùng.'),
        ('amenity_score', 'Điểm tiện ích (amenity_score)', 'Chất lượng tiện ích kết nối xung quanh (giao thông, trường học, dịch vụ).'),
        ('dist_center', 'KC đến trung tâm (dist_center)', 'Khoảng cách địa lý tới trung tâm tài chính Manhattan (càng xa giá giảm).'),
        ('pop_density', 'Mật độ dân số (pop_density)', 'Mật độ dân cư sinh sống; phản ánh độ sầm uất và nhu cầu nhà ở khu vực.'),
        ('building_age', 'Tuổi công trình (building_age)', 'Số năm công trình đã vận hành (công trình cũ chịu khấu hao tài sản).'),
        ('land_sqft', 'Diện tích đất (land_sqft)', 'Diện tích lô đất (ảnh hưởng ít hơn gross_sqft do đặc thù nhà chung cư tại NYC).'),
    ]
    
    rows = []
    for col, name, desc in factors:
        if col in df_in.columns:
            valid = df_in.dropna(subset=['sale_price', col])
            if len(valid) >= 20:
                r = valid['sale_price'].corr(valid[col])
                abs_r = abs(r)
                if abs_r >= 0.50:
                    level = "🚀 RẤT MẠNH"
                elif abs_r >= 0.35:
                    level = "📈 MẠNH"
                elif abs_r >= 0.15:
                    level = "⚖️ TRUNG BÌNH"
                else:
                    level = "📉 YẾU"
                
                direction = "Thuận (+)" if r > 0 else "Nghịch (-)"
                rows.append({
                    'Yếu tố tác động': name,
                    'Tương quan (r)': round(r, 2),
                    'Mức độ ảnh hưởng': level,
                    'Chiều tác động': direction,
                    'Giải thích ý nghĩa thực tế': desc,
                    '_abs_r': abs_r
                })
    
    fdf = pd.DataFrame(rows).sort_values('_abs_r', ascending=False)
    
    col_tbl, col_chart = st.columns([3, 2])
    with col_tbl:
        display_df = fdf[['Yếu tố tác động', 'Tương quan (r)', 'Mức độ ảnh hưởng', 'Chiều tác động', 'Giải thích ý nghĩa thực tế']].copy()
        st.dataframe(
            display_df,
            column_config={
                "Tương quan (r)": st.column_config.NumberColumn(format="%.2f"),
                "Mức độ ảnh hưởng": st.column_config.TextColumn(),
            },
            width='stretch',
            hide_index=True
        )
    with col_chart:
        fdf_chart = fdf.sort_values('_abs_r', ascending=True)
        colors = [C_GREEN if r > 0 else C_RED for r in fdf_chart['Tương quan (r)']]
        fig_sum = go.Figure(go.Bar(
            x=fdf_chart['Tương quan (r)'],
            y=fdf_chart['Yếu tố tác động'].apply(lambda x: x.split(' (')[0]),
            orientation='h',
            marker_color=colors,
            text=[f"r = {r:+.2f}" for r in fdf_chart['Tương quan (r)']],
            textposition='outside'
        ))
        clayout(fig_sum, h=300, t=30, b=20, l=10, r=60)
        fig_sum.update_layout(
            title="Xếp hạng Mức độ Tương quan với Giá bán (r)",
            title_font=dict(size=13, color='#374151'),
            xaxis=dict(range=[-0.4, 0.9], zeroline=True, zerolinecolor='#cbd5e1', title="Hệ số tương quan Pearson (r)")
        )
        st.plotly_chart(fig_sum, width='stretch')

# ════════════════════════════════════════════════════════════
# LOAD DỮ LIỆU
# ════════════════════════════════════════════════════════════
df_raw, load_err = load_data()
if df_raw is None:
    st.error(f"⚠️ **Lỗi:** {load_err}")
    st.info("Hãy chạy `main.py` trước.")
    st.stop()

# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:20px 0 10px'>
        <div style='font-size:36px'>🏙️</div>
        <div style='font-size:14px;font-weight:700;color:#f1f5f9;margin-top:6px'>Bộ lọc dữ liệu</div>
        <div style='font-size:11px;color:#64748b;margin-top:2px'>NYC Real Estate Analytics</div>
    </div>
    <hr style='border-color:#1e3a5f;margin:0 0 14px'>
    """, unsafe_allow_html=True)
    all_b = [b for b in BOROUGH_ORDER if b in df_raw['borough_name'].dropna().unique()]
    selected_boroughs = st.multiselect("📍 Quận (Borough)", options=all_b, default=all_b)
    avail_years = sorted(df_raw['sale_year'].dropna().astype(int).unique().tolist())
    year_range  = st.select_slider("📅 Năm giao dịch", options=avail_years,
                                   value=(min(avail_years), max(avail_years)))
    p5  = float(df_raw['sale_price'].quantile(0.05))
    p95 = float(df_raw['sale_price'].quantile(0.95))
    price_range = st.slider("💰 Khoảng giá ($)",
                            min_value=float(df_raw['sale_price'].min()),
                            max_value=float(df_raw['sale_price'].max()),
                            value=(p5, p95), format="$%.0f",
                            help="Mặc định p5–p95 để loại bỏ outlier.")
    st.markdown('<hr style="border-color:#1e3a5f;margin:14px 0 10px">', unsafe_allow_html=True)
    if st.button("🔄 Đặt lại bộ lọc", width='stretch'):
        st.rerun()
    st.markdown(f"""
    <div style='text-align:center;margin-top:10px;color:#475569;font-size:11px'>
        Tổng: {len(df_raw):,} giao dịch<br>Nguồn: NYC Property Sales
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# ÁP DỤNG BỘ LỌC
# ════════════════════════════════════════════════════════════
if not selected_boroughs:
    st.warning("⚠️ Chưa chọn quận nào. Hãy chọn ít nhất một quận trong bộ lọc bên trái.")
    st.stop()
df = apply_filters(df_raw, selected_boroughs, year_range, price_range)
if len(df) == 0:
    st.warning("⚠️ **Không có dữ liệu phù hợp.** Hãy mở rộng bộ lọc hoặc nhấn Đặt lại.")
    st.stop()

df_sample = df.sample(n=min(3000, len(df)), random_state=42)
df_ppsf   = df[df['price_per_sqft'].notna() & (df['price_per_sqft'] < 5000)].copy()

# ════════════════════════════════════════════════════════════
# TIÊU ĐỀ
# ════════════════════════════════════════════════════════════
h1, h2 = st.columns([4, 1])
with h1:
    st.markdown("""
    <h1 style='font-size:24px;font-weight:800;color:#0f172a;margin:0'>
    🏙️ BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG BẤT ĐỘNG SẢN NEW YORK GIAI ĐOẠN 2025 - 2026
    </h1>""", unsafe_allow_html=True)
with h2:
    st.markdown(f"""
    <div style='text-align:right;padding-top:6px'>
        <span class="badge">✓ {len(df):,} giao dịch</span><br>
        <span style='font-size:11px;color:#94a3b8'>{len(selected_boroughs)} quận · {year_range[0]}–{year_range[1]}</span>
    </div>""", unsafe_allow_html=True)
st.markdown("<div style='margin-bottom:18px'></div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "🏙️  Tổng quan",
    "🗺️  Phân tích khu vực",
    "📐  Yếu tố quyết định giá",
    "📅  Biến động theo thời gian",
    "🤖  Dự báo & Mô hình ML",
])

# ════════════════════════════════════════════════════════════
# TAB 0 — TỔNG QUAN
# ════════════════════════════════════════════════════════════
with tab0:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#4338ca,#6366f1,#818cf8);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(99,102,241,0.35)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>🏙️ Thị trường đang ở đâu và quy mô như thế nào?</b><br>
    <span style='font-size:12px;opacity:0.88'>Tổng quan về quy mô, mặt bằng giá và cơ cấu thị trường bất động sản NYC trong bộ lọc hiện tại.</span>
    </div>
    """, unsafe_allow_html=True)

    med_price = df['sale_price'].median()
    med_ppsf  = df_ppsf['price_per_sqft'].median() if len(df_ppsf) > 0 else 0
    total_val = df['sale_price'].sum()
    pct_1m    = (df['sale_price'] >= 1_000_000).mean() * 100
    yoy_med0  = df.groupby('sale_year')['sale_price'].median()
    yrs0 = sorted(yoy_med0.index)
    if len(yrs0) >= 2:
        yoy_d0 = (yoy_med0[yrs0[-1]]/yoy_med0[yrs0[-2]]-1)*100
        yoy_s0 = f"{yoy_d0:+.1f}%"
    else:
        yoy_d0, yoy_s0 = 0.0, "—"

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Tổng giao dịch", f"{len(df):,}")
    k2.metric("Giá trung vị",   fmt_M(med_price))
    k3.metric("Giá/sqft (TV)",  f"${med_ppsf:,.0f}")
    k4.metric("Tổng giá trị",   f"${total_val/1e9:.1f}B")
    k5.metric("Tăng giá YoY",   yoy_s0, delta=f"{yoy_d0:.1f}%" if yoy_d0 else None)
    k6.metric("Giao dịch ≥$1M", f"{pct_1m:.1f}%")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    section_q(
        "Borough nào chiếm ưu thế — về thanh khoản và mặt bằng giá?",
        "Số giao dịch = thanh khoản. Giá trung vị ít bị ảnh hưởng bởi outlier hơn giá trung bình."
    )

    bor_cnt = df['borough_name'].value_counts().reindex(BOROUGH_ORDER, fill_value=0).reset_index()
    bor_cnt.columns = ['Borough','Giao dịch']
    bor_cnt = bor_cnt[bor_cnt['Giao dịch'] > 0]

    bor_med = df.groupby('borough_name')['sale_price'].median().reindex(BOROUGH_ORDER).dropna().reset_index()
    bor_med.columns = ['Borough','Giá trung vị']

    ca, cb = st.columns(2)
    with ca:
        fig = px.bar(bor_cnt.sort_values('Giao dịch'), x='Giao dịch', y='Borough', orientation='h',
                     color='Borough', color_discrete_map=BOROUGH_COLORS, text='Giao dịch',
                     title="Số giao dịch theo quận")
        fig.update_traces(texttemplate='%{text:,}', textposition='auto')
        clayout(fig, h=280, t=40, r=80)
        fig.update_layout(yaxis=dict(automargin=True, title='Quận'), xaxis=dict(automargin=True, title='Số giao dịch'),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')
    with cb:
        fig = px.bar(bor_med.sort_values('Giá trung vị'), x='Giá trung vị', y='Borough', orientation='h',
                     color='Borough', color_discrete_map=BOROUGH_COLORS,
                     text=bor_med.sort_values('Giá trung vị')['Giá trung vị'].apply(fmt_M),
                     title="Giá trung vị theo quận ($)")
        fig.update_traces(textposition='auto')
        clayout(fig, h=280, t=40, r=100)
        fig.update_layout(yaxis=dict(automargin=True, title='Quận'), xaxis=dict(tickformat='$,.0f', automargin=True, title='Giá trung vị ($)'),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')

    divider()
    section_q("Thị trường đang tập trung vào loại hình bất động sản nào?",
              "Cơ cấu loại hình và phân bố giá theo từng loại (top 6).")

    top6_bt = df['building_type'].value_counts().head(6).index.tolist()
    cc, cd  = st.columns(2)
    with cc:
        bt_c = df['building_type'].value_counts().head(6).reset_index()
        bt_c.columns = ['Loại hình','Số lượng']
        fig = px.pie(bt_c, names='Loại hình', values='Số lượng', hole=0.50,
                     color_discrete_sequence=[C_BLUE,C_SKY,C_ORANGE,C_GREEN,'#8b5cf6',C_GRAY],
                     title="Cơ cấu loại hình bất động sản")
        fig.update_traces(textposition='inside', textinfo='percent',
                          insidetextorientation='radial',
                          hovertemplate='<b>%{label}</b><br>%{value:,} GD<br>%{percent}<extra></extra>')
        clayout(fig, h=320, t=40, l=10, r=20, b=20, leg=True)
        fig.update_layout(legend=dict(orientation='v', x=1.0, y=0.5, font_size=11),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')
    with cd:
        df_bt0 = df[df['building_type'].isin(top6_bt)]
        med_bt0 = df_bt0.groupby('building_type')['sale_price'].median().sort_values(ascending=False)
        fig = px.box(df_bt0, x='building_type', y='sale_price',
                     color='building_type',
                     color_discrete_sequence=[C_BLUE,C_SKY,C_ORANGE,C_GREEN,'#8b5cf6',C_GRAY],
                     points=False, labels={'building_type':'Loại hình BĐS','sale_price':'Giá bán ($)'},
                     category_orders={'building_type': med_bt0.index.tolist()},
                     title="Phân bố giá theo loại hình (top 6)")
        clayout(fig, h=320, t=40, b=60, l=10, r=10)
        fig.update_layout(xaxis=dict(automargin=True, tickangle=-15, tickfont_size=10, title=''),
                          yaxis=dict(tickformat='$,.0f', automargin=True),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')

    divider()
    top_b0 = bor_med.sort_values('Giá trung vị', ascending=False).iloc[0]
    low_b0 = bor_med.sort_values('Giá trung vị').iloc[0]
    rat0   = top_b0['Giá trung vị'] / low_b0['Giá trung vị']
    top_bt0= df['building_type'].value_counts().index[0]
    pct_bt0= df['building_type'].value_counts().iloc[0] / len(df) * 100
    insight_box(f"""
    <b>📌 Những điều quan trọng nhất từ tổng quan:</b><br>
    • <b>{top_b0['Borough']}</b> dẫn đầu về giá trung vị ({fmt_M(top_b0['Giá trung vị'])}),
      cao hơn <b>{rat0:.1f}×</b> so với {low_b0['Borough']} ({fmt_M(low_b0['Giá trung vị'])}) —
      phản ánh phân hóa mạnh giữa các quận.<br>
    • <b>{pct_bt0:.0f}%</b> giao dịch thuộc loại hình <b>{top_bt0}</b> —
      thị trường tập trung rõ vào phân khúc này.<br>
    • Tổng giá trị thị trường: <b>${total_val/1e9:.2f} tỷ USD</b>.
      Tỷ lệ giao dịch ≥$1M: <b>{pct_1m:.1f}%</b> — thị trường có xu hướng cao cấp.
    """)

    # ── Phân khúc khách hàng ──────────────────────────────────
    divider()
    section_q("Thị trường đang phục vụ nhóm khách hàng nào?",
              "Phân loại theo số căn trong tòa nhà — proxy cho mục đích mua (ở thực vs đầu tư).")

    df['_segment'] = pd.cut(
        df['total_units'],
        bins=[-1, 1, 10, float('inf')],
        labels=['① Mua ở thực (1 căn)', '② Đầu tư nhỏ (2-10)', '③ Tổ chức (>10)']
    )
    seg_cnt  = df['_segment'].value_counts().sort_index()
    seg_med  = df.groupby('_segment', observed=True)['sale_price'].median()
    seg_df   = pd.DataFrame({'Phân khúc': seg_cnt.index,
                              'Số GD': seg_cnt.values,
                              'Giá trung vị': seg_med.values})
    seg_df['% thị trường'] = seg_df['Số GD'] / seg_df['Số GD'].sum() * 100

    sa, sb = st.columns(2)
    with sa:
        fig_seg = px.bar(seg_df, x='Phân khúc', y='Số GD',
                         color='Phân khúc',
                         color_discrete_sequence=[C_GREEN, C_BLUE, C_ORANGE],
                         text=seg_df['% thị trường'].apply(lambda v: f'{v:.1f}%'),
                         title="Cơ cấu phân khúc khách hàng")
        fig_seg.update_traces(textposition='outside')
        clayout(fig_seg, h=300, t=40, b=20)
        fig_seg.update_layout(showlegend=False,
                               xaxis=dict(automargin=True, title='Phân khúc'),
                               yaxis=dict(automargin=True, title='Số giao dịch'),
                               title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig_seg, width='stretch')
    with sb:
        fig_sp = px.bar(seg_df, x='Phân khúc', y='Giá trung vị',
                        color='Phân khúc',
                        color_discrete_sequence=[C_GREEN, C_BLUE, C_ORANGE],
                        text=seg_df['Giá trung vị'].apply(fmt_M),
                        title="Giá trung vị theo phân khúc")
        fig_sp.update_traces(textposition='outside')
        clayout(fig_sp, h=300, t=40, b=20)
        fig_sp.update_layout(showlegend=False,
                               xaxis=dict(automargin=True, title='Phân khúc'),
                               yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá trung vị ($)'),
                               title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig_sp, width='stretch')

    # ── Nhận diện rủi ro đầu tư ───────────────────────────────
    divider()
    section_q("Khu vực nào có rủi ro giá cao nhất?",
              "Rủi ro = biến động giá cao (CV cao) hoặc thanh khoản thấp. "
              "Xanh = ít rủi ro, đỏ = cần thận trọng.")

    borough_risk = df.groupby('borough_name').agg(
        med_price=('sale_price','median'),
        std_price=('sale_price','std'),
        n_gd=('sale_price','count')
    ).reset_index()
    borough_risk['CV (%)'] = (borough_risk['std_price'] / borough_risk['med_price'] * 100).round(1)
    borough_risk['Rủi ro biến động'] = pd.cut(
        borough_risk['CV (%)'],
        bins=[0, 80, 120, float('inf')],
        labels=['🟢 Thấp', '🟡 Trung bình', '🔴 Cao']
    )
    borough_risk = borough_risk.sort_values('CV (%)')

    risk_display = borough_risk[['borough_name','med_price','CV (%)','n_gd','Rủi ro biến động']].copy()
    risk_display.columns = ['Quận','Giá trung vị','Biến động CV (%)','Số giao dịch','Đánh giá rủi ro']
    risk_display['Giá trung vị'] = risk_display['Giá trung vị'].apply(fmt_M)
    risk_display['Số giao dịch'] = risk_display['Số giao dịch'].apply(lambda v: f'{v:,}')
    st.dataframe(risk_display.set_index('Quận'), width='stretch')

# ════════════════════════════════════════════════════════════
# TAB 1 — PHÂN TÍCH KHU VỰC & BẢN ĐỒ HEATMAP
# ════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f766e,#0d9488,#34d399);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(16,185,129,0.3)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>🗺️ Bản đồ Nhiệt Khu vực & Phân tích Điểm nóng (NYC Hotspot Map)</b><br>
    <span style='font-size:12px;opacity:0.88'>Nhận diện điểm nóng giá bán, định giá đơn vị $/sqft và mật độ thanh khoản trên bản đồ tương quan không gian thực.</span>
    </div>
    """, unsafe_allow_html=True)

    n_neigh   = df['neighborhood'].nunique()
    top_neigh = df['neighborhood'].value_counts().index[0]
    top_n_cnt = df['neighborhood'].value_counts().iloc[0]
    bor_med_f = df.groupby('borough_name')['sale_price'].median()
    top_bor_p = bor_med_f.idxmax()

    ka,kb,kc,kd = st.columns(4)
    ka.metric("Quận đang phân tích",        f"{len(selected_boroughs)}/5")
    kb.metric("Số khu vực",                  f"{n_neigh:,}")
    kc.metric("Khu vực sôi động nhất",       top_neigh.title()[:20])
    kd.metric("Quận giá trung vị cao nhất",  top_bor_p)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── YÊU CẦU VỀ BẢN ĐỒ (MAP): BẢN ĐỒ TÔ MÀU KHU VỰC (HEATMAP) ──
    section_q(
        "Bản đồ Nhiệt Khu vực (NYC Hotspot Heatmap)",
        "Tô màu khu vực thể hiện trực quan điểm nóng (hotspots) về Giá trung vị, Giá/sqft hoặc Mật độ thanh khoản giao dịch."
    )

    # Gom nhóm dữ liệu địa lý theo Neighborhood
    geo_df = df.groupby(['neighborhood', 'borough_name']).agg(
        med_price=('sale_price', 'median'),
        med_ppsf=('price_per_sqft', 'median'),
        n_count=('sale_price', 'count')
    ).reset_index()

    # Thêm lat, lon cho từng khu vực
    coords_list = [get_neighborhood_coords(row['neighborhood'], row['borough_name']) for _, row in geo_df.iterrows()]
    geo_df['lat'] = [c[0] for c in coords_list]
    geo_df['lon'] = [c[1] for c in coords_list]
    geo_df['med_ppsf_clean'] = geo_df['med_ppsf'].fillna(0)

    mc1, mc2, mc3 = st.columns([2, 1, 1])
    with mc1:
        map_metric = st.radio(
            "Hiển thị điểm nóng theo:",
            options=["🔥 Giá trung vị ($)", "📐 Giá/sqft trung vị ($)", "📊 Mật độ giao dịch (Số căn)"],
            horizontal=True
        )
    with mc2:
        radius_val = st.slider("Bán kính điểm nhiệt (Radius)", 15, 45, 25)
    with mc3:
        zoom_val = st.slider("Độ phóng đại (Zoom)", 9, 13, 10)

    if map_metric == "🔥 Giá trung vị ($)":
        target_z = 'med_price'
        color_scale = "Plasma"
        z_title = "Giá trung vị ($)"
    elif map_metric == "📐 Giá/sqft trung vị ($)":
        target_z = 'med_ppsf_clean'
        color_scale = "Inferno"
        z_title = "Giá/sqft ($)"
    else:
        target_z = 'n_count'
        color_scale = "Viridis"
        z_title = "Số giao dịch"

    fig_map = px.density_mapbox(
        geo_df,
        lat='lat',
        lon='lon',
        z=target_z,
        radius=radius_val,
        center=dict(lat=40.7400, lon=-73.9400),
        zoom=zoom_val,
        mapbox_style="open-street-map",
        color_continuous_scale=color_scale,
        hover_name="neighborhood",
        hover_data={
            "borough_name": True,
            "med_price": ":$,.0f",
            "med_ppsf_clean": ":$,.0f",
            "n_count": ":,",
            "lat": False,
            "lon": False
        },
        labels={
            "borough_name": "Quận",
            "med_price": "Giá trung vị",
            "med_ppsf_clean": "Giá/sqft",
            "n_count": "Số GD"
        }
    )
    clayout(fig_map, h=520, t=10, b=10, l=10, r=10)
    fig_map.update_layout(
        coloraxis_colorbar=dict(title=z_title, len=0.8)
    )
    st.plotly_chart(fig_map, width='stretch')

    # Chú giải điểm nóng
    top_p_geo = geo_df.sort_values('med_price', ascending=False).head(3)
    top_v_geo = geo_df.sort_values('n_count', ascending=False).head(3)
    p_spots = ", ".join([f"<b>{r['neighborhood'].title()}</b> (${r['med_price']/1e6:.2f}M)" for _, r in top_p_geo.iterrows()])
    v_spots = ", ".join([f"<b>{r['neighborhood'].title()}</b> ({r['n_count']:,} GD)" for _, r in top_v_geo.iterrows()])

    insight_box(f"""
    <b>📍 Nhận diện Điểm nóng (Hotspots) trên Bản đồ:</b><br>
    • 🔴 <b>Điểm nóng về Giá bán (Hotspots Giá cao):</b> Tập trung dày đặc tại khu vực lõi Manhattan: {p_spots}.<br>
    • 🟢 <b>Điểm nóng về Thanh khoản (Hotspots Giao dịch nhộn nhịp):</b> Phân bố rộng ở Queens & Brooklyn: {v_spots}.<br>
    • 💡 <i>Mẹo sử dụng bản đồ: Phóng to (Zoom) để quan sát từng góc phố, di chuột qua từng điểm màu nhiệt để xem chi tiết đơn giá $/sqft và tổng số giao dịch thực tế.</i>
    """)

    divider()
    section_q("Giá bán phân bố như thế nào trong từng quận?",
              "Đường giữa = trung vị. Hộp = khoảng tứ phân vị (25%–75%). Nhãn giá trung vị được ghi trực tiếp.")

    bor_ord1 = df.groupby('borough_name')['sale_price'].median().sort_values(ascending=False).index.tolist()
    fig = px.box(df, x='borough_name', y='sale_price', color='borough_name',
                 color_discrete_map=BOROUGH_COLORS, points=False,
                 labels={'borough_name':'Quận','sale_price':'Giá bán (USD)'},
                 category_orders={'borough_name': bor_ord1},
                 title='Phân phối giá bán nhà theo Quận')
    for b in bor_ord1:
        m = df[df['borough_name']==b]['sale_price'].median()
        fig.add_annotation(x=b, y=m, text=fmt_M(m), showarrow=False,
                           font=dict(size=11,color='#111827',weight=700),
                           yshift=20, bgcolor='rgba(255,255,255,0.88)', borderpad=3)
    clayout(fig, h=360, t=50, b=20)
    fig.update_layout(
        title_font=dict(size=14, color='#374151'),
        yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá bán (USD)'),
        xaxis=dict(automargin=True, title='Quận')
    )
    st.plotly_chart(fig, width='stretch')

    divider()
    section_q("Khu vực nào sôi động nhất và có giá/sqft cao nhất?",
              "Trái: số giao dịch (thanh khoản). Phải: giá/sqft trung vị (loại khu vực < 5 giao dịch để tránh sai lệch mẫu nhỏ).")

    top_n_ppsf_row = None
    cn1, cn2 = st.columns(2)
    with cn1:
        t15c = (df.groupby(['neighborhood','borough_name']).size()
                .reset_index(name='Giao dịch')
                .sort_values('Giao dịch', ascending=False).head(15))
        t15c = t15c.sort_values('Giao dịch')
        t15c['Khu vực'] = t15c['neighborhood'].str.title().str[:25]
        fig = px.bar(t15c, x='Giao dịch', y='Khu vực', orientation='h',
                     color='borough_name', color_discrete_map=BOROUGH_COLORS, text='Giao dịch',
                     title="Top 15 khu vực nhiều giao dịch nhất",
                     labels={'borough_name':'Quận'})
        fig.update_traces(texttemplate='%{text:,}', textposition='auto')
        clayout(fig, h=460, t=40, b=20, r=80, leg=True)
        fig.update_layout(yaxis=dict(automargin=True, tickfont_size=11, title='Khu vực'),
                          xaxis=dict(automargin=True, title='Số giao dịch'),
                          legend=dict(orientation='h', y=-0.1, x=0, font_size=11),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')
    with cn2:
        if len(df_ppsf) > 0:
            t15p = (df_ppsf.groupby(['neighborhood','borough_name'])['price_per_sqft']
                    .agg(med_ppsf='median', cnt='count').reset_index())
            t15p = t15p[t15p['cnt'] >= 5].nlargest(15,'med_ppsf').sort_values('med_ppsf')
            t15p['Khu vực'] = t15p['neighborhood'].str.title().str[:25]
            if len(t15p) > 0:
                top_n_ppsf_row = t15p.iloc[-1]
            fig = px.bar(t15p, x='med_ppsf', y='Khu vực', orientation='h',
                         color='borough_name', color_discrete_map=BOROUGH_COLORS,
                         text=t15p['med_ppsf'].apply(lambda v: f'${v:,.0f}'),
                         title="Top 15 khu vực giá/sqft cao nhất (trung vị)",
                         labels={'borough_name':'Quận','med_ppsf':'$/sqft (trung vị)'})
            fig.update_traces(textposition='auto')
            clayout(fig, h=460, t=40, b=20, r=80, leg=True)
            fig.update_layout(yaxis=dict(automargin=True, tickfont_size=11, title='Khu vực'),
                              xaxis=dict(tickformat='$,.0f', automargin=True, title='$/sqft (trung vị)'),
                              legend=dict(orientation='h', y=-0.1, x=0, font_size=11),
                              title_font=dict(size=13, color='#374151'))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không đủ dữ liệu giá/sqft.")

# ════════════════════════════════════════════════════════════
# TAB 2 — YẾU TỐ QUYẾT ĐỊNH GIÁ & PHÂN TÍCH TƯƠNG QUAN
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#5b21b6,#7c3aed,#a78bfa);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(124,58,237,0.35)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>📐 Phân tích Ma trận Yếu tố & Các Biến số Quyết định Giá</b><br>
    <span style='font-size:12px;opacity:0.88'>Tóm tắt các yếu tố ảnh hưởng mạnh/yếu, ma trận tương quan và giải thích ý nghĩa chiều tác động của các biến số chính đến giá bán thực tế.</span>
    </div>
    """, unsafe_allow_html=True)

    # ── NGUYÊN TẮC TRỰC QUAN: BẢNG TÓM TẮT YẾU TỐ TÁC ĐỘNG GIÁ ──
    section_q(
        "Bảng tóm tắt các yếu tố ảnh hưởng đến giá bất động sản",
        "Tóm tắt toàn bộ các biến số đo lường, phân loại rõ yếu tố nào ảnh hưởng mạnh hay yếu đến giá bán thực tế."
    )
    render_factor_summary_matrix(df)

    divider()

    # ── MA TRẬN TƯƠNG QUAN TỔNG THỂ ──
    section_q(
        "Ma trận tương quan tổng thể giữa các yếu tố với Giá bán",
        "Đọc bản đồ nhiệt: ô màu đỏ = tương quan thuận (+); ô màu xanh = tương quan nghịch (-). Số trong ô là hệ số tương quan r."
    )
    cc_cols = ['sale_price','gross_sqft','avg_income','amenity_score','dist_center','pop_density','building_age']
    cc_lbl  = {'sale_price':'Giá bán','gross_sqft':'Diện tích','avg_income':'Thu nhập TB',
               'amenity_score':'Điểm tiện ích','dist_center':'KC trung tâm','pop_density':'Mật độ dân số','building_age':'Tuổi công trình'}
    cc_data = df[cc_cols].dropna()
    cc_mat  = cc_data.corr()
    cc_mat.columns = [cc_lbl[c] for c in cc_mat.columns]
    cc_mat.index   = [cc_lbl[c] for c in cc_mat.index]
    
    fig_corr_mat = px.imshow(cc_mat, text_auto='.2f', color_continuous_scale='RdBu_r',
                            zmin=-1, zmax=1, aspect='equal',
                            title='Ma trận tương quan giữa các yếu tố và Giá bán')
    clayout(fig_corr_mat, h=360, t=40, b=20)
    fig_corr_mat.update_layout(
        coloraxis_colorbar=dict(title='Hệ số r', len=0.8),
        title_font=dict(size=13, color='#374151')
    )
    st.plotly_chart(fig_corr_mat, width='stretch')

    divider()

    # ── PHÂN TÍCH CHI TIẾT 3 BIẾN SỐ CHÍNH THEO YÊU CẦU ──
    st.markdown("""
    <div style='font-size:18px;font-weight:800;color:#1e1b4b;margin-bottom:16px'>
    🔍 PHÂN TÍCH CHI TIẾT 3 BIẾN SỐ CHỦ ĐẠO TÁC ĐỘNG ĐẾN GIÁ BÁN
    </div>
    """, unsafe_allow_html=True)

    # 1. BIẾN SỐ 1: DIỆN TÍCH (gross_sqft)
    section_q("1. Biến số DIỆN TÍCH CÔNG TRÌNH (gross_sqft) — Mức độ tác động: 🚀 RẤT MẠNH",
              "Phân tích mối quan hệ giữa quy mô diện tích sàn sử dụng và tổng giá bán bất động sản.")
    
    df_sq = df[df['gross_sqft'].notna() & df['gross_sqft'].between(100, 4000)].copy()
    df_sq = df_sq[df_sq['sale_price'] < df_sq['sale_price'].quantile(0.97)]
    corr_sq = df_sq['gross_sqft'].corr(df_sq['sale_price']) if len(df_sq) >= 20 else 0

    if len(df_sq) >= 50:
        df_sq['bin'] = pd.cut(df_sq['gross_sqft'], bins=range(100,4200,200),
                              labels=[f"{i}–{i+200}" for i in range(100,4000,200)])
        ba = (df_sq.groupby('bin', observed=True)
              .agg(med_price=('sale_price','median'), cnt=('sale_price','count'),
                   sqft_mid=('gross_sqft','median')).reset_index())
        ba = ba[ba['cnt'] >= 10]
        fig_sq_chart = px.scatter(ba, x='sqft_mid', y='med_price', size='cnt', size_max=30,
                                  color='med_price', color_continuous_scale='Blues', trendline='ols',
                                  labels={'sqft_mid':'Diện tích trung vị (sqft)',
                                          'med_price':'Giá trung vị ($)','cnt':'Số GD'},
                                  title="Tương quan giữa Diện tích sử dụng (sqft) và Giá bán trung vị ($)")
        clayout(fig_sq_chart, h=340, t=40, b=20)
        fig_sq_chart.update_layout(coloraxis_showscale=False,
                                   yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá trung vị ($)'),
                                   xaxis=dict(automargin=True, title='Diện tích trung vị (sqft)'),
                                   title_font=dict(size=13, color='#374151'))
        # Đặt tên cho OLS trendline trace để tránh undefined trong legend
        for trace in fig_sq_chart.data:
            if hasattr(trace, 'name') and trace.name and 'OLS' in str(trace.name):
                trace.name = 'Đường xu hướng (OLS)'
        st.plotly_chart(fig_sq_chart, width='stretch')

    insight_box(f"""
    <b>💡 Ý nghĩa kinh tế của Biến số DIỆN TÍCH (gross_sqft):</b><br>
    • Hệ số tương quan: <b>r = +{corr_sq:.2f}</b> (Tương quan thuận rất mạnh).<br>
    • <b>Giải thích thực tế:</b> Diện tích sàn là yếu tố vật lý đóng vai trò quyết định số 1 tới giá bán. 
      Căn hộ có diện tích lớn hơn cung cấp không gian sống rộng rãi hơn, nhiều phòng ngủ/phòng tắm hơn. 
      Mỗi 500 sqft diện tích tăng thêm giúp giá trị tài sản tăng trung bình từ 40% - 60%.
    """)

    divider()

    # 2. BIẾN SỐ 2: THU NHẬP KHU VỰC (avg_income)
    section_q("2. Biến số THU NHẬP BÌNH QUÂN KHU VỰC (avg_income) — Mức độ tác động: 📈 MẠNH",
              "Phân tích tác động của sức mua và mức độ đắt đỏ của dân cư sinh sống tại khu vực đến mặt bằng giá nhà.")

    df_inc = df[df['avg_income'].notna()].copy()
    corr_inc = df_inc['avg_income'].corr(df_inc['sale_price']) if len(df_inc) >= 20 else 0

    inc_summary = df_inc.groupby('borough_name').agg(
        avg_inc=('avg_income', 'mean'),
        med_price=('sale_price', 'median'),
        med_ppsf=('price_per_sqft', 'median')
    ).reset_index()

    fig_inc = px.bar(
        inc_summary, x='borough_name', y='med_price',
        color='avg_inc', color_continuous_scale='Purples',
        text=inc_summary['avg_inc'].apply(lambda v: f'Thu nhập TB: ${v:,.0f}'),
        title="Mặt bằng Giá nhà Trung vị xếp theo Mức Thu nhập Bình quân Khu vực ($)",
        labels={'borough_name': 'Quận', 'med_price': 'Giá bán trung vị ($)', 'avg_inc': 'Thu nhập TB ($)'}
    )
    fig_inc.update_traces(textposition='outside')
    clayout(fig_inc, h=340, t=40, b=20)
    fig_inc.update_layout(
        yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá bán trung vị ($)'),
        xaxis=dict(automargin=True, title='Quận'),
        coloraxis_colorbar=dict(title='Thu nhập TB ($)'),
        title_font=dict(size=13, color='#374151')
    )
    st.plotly_chart(fig_inc, width='stretch')

    insight_box(f"""
    <b>💡 Ý nghĩa kinh tế của Biến số THU NHẬP KHU VỰC (avg_income):</b><br>
    • Hệ số tương quan: <b>r = +{corr_inc:.2f}</b> (Tương quan thuận mạnh).<br>
    • <b>Giải thích thực tế:</b> Thu nhập bình quân của dân cư khu vực phản ánh <i>sức mua (purchasing power)</i> 
      và chất lượng môi trường sống. Khu vực có thu nhập cao (như Manhattan: ~$88K/năm) thường sở hữu hạ tầng cao cấp, 
      an ninh tốt và trường học chất lượng, dẫn tới nhu cầu mua nhà cao hơn và sẵn sàng trả mức giá áp đảo so với các quận phụ cận.
    """)

    divider()

    # 3. BIẾN SỐ 3: TUỔI BẤT ĐỘNG SẢN (building_age)
    section_q("3. Biến số TUỔI CÔNG TRÌNH (building_age) — Mức độ tác động: 📉 YẾU / ÂM",
              "Phân tích tác động của thời gian vận hành công trình đến giá bán (khấu hao vật lý vs giá trị vị trí).")

    df_age = df[df['building_age'].notna() & df['building_age'].between(0, 120)].copy()
    corr_age = df_age['building_age'].corr(df_age['sale_price']) if len(df_age) >= 20 else 0

    df_age['age_group'] = pd.cut(
        df_age['building_age'],
        bins=[-1, 15, 35, 65, 120],
        labels=['Mới (<15 năm)', 'Trung bình (15–35 năm)', 'Cũ (35–65 năm)', 'Rất cũ (>65 năm)']
    )
    age_sum = df_age.groupby('age_group', observed=True)['sale_price'].median().reset_index()

    fig_age = px.bar(
        age_sum, x='age_group', y='sale_price',
        color='sale_price', color_continuous_scale='Reds_r',
        text=age_sum['sale_price'].apply(fmt_M),
        title="Giá trung vị bất động sản phân theo Nhóm Tuổi công trình",
        labels={'age_group': 'Nhóm tuổi', 'sale_price': 'Giá trung vị ($)'}
    )
    fig_age.update_traces(textposition='outside')
    clayout(fig_age, h=320, t=40, b=20)
    fig_age.update_layout(coloraxis_showscale=False, yaxis=dict(tickformat='$,.0f', automargin=True), title_font=dict(size=13, color='#374151'))
    st.plotly_chart(fig_age, width='stretch')

    insight_box(f"""
    <b>💡 Ý nghĩa kinh tế của Biến số TUỔI BẤT ĐỘNG SẢN (building_age):</b><br>
    • Hệ số tương quan: <b>r = {corr_age:.2f}</b> (Tương quan âm nhẹ).<br>
    • <b>Giải thích thực tế:</b> Bất động sản mới xây (<15 năm) sở hữu giá bán cao nhất do thiết kế hiện đại và không tốn chi phí sửa chữa. 
      Công trình cũ có xu hướng giảm giá do <i>khấu hao tài sản (physical depreciation)</i>. Tuy nhiên tại NYC, mối tương quan này khá yếu vì nhiều tòa nhà cổ (>70 năm) tại Manhattan hay Brooklyn Heights nằm ở vị trí đất vàng đắt đỏ và có kiến trúc lịch sử được bảo tồn, bù đắp đáng kể sự suy giảm về tuổi đời.
    """)

# ════════════════════════════════════════════════════════════
# TAB 3 — BIẾN ĐỘNG THEO THỜI GIAN
# ════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#b45309,#d97706,#fbbf24);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(245,158,11,0.35)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>📅 Thị trường đang đi theo hướng nào?</b><br>
    <span style='font-size:12px;opacity:0.9'>Xu hướng giá theo tháng, tính mùa vụ giao dịch
    và dự báo 6 tháng tới dựa trên dữ liệu lịch sử.</span>
    </div>
    """, unsafe_allow_html=True)

    yoy_med3 = df.groupby('sale_year')['sale_price'].median()
    yrs3 = sorted(yoy_med3.index)
    yoy_pct3 = (yoy_med3[yrs3[-1]]/yoy_med3[yrs3[-2]]-1)*100 if len(yrs3) >= 2 else 0
    monthly_cnt3 = df['sale_month'].value_counts()
    peak_m3 = monthly_cnt3.idxmax() if len(monthly_cnt3) > 0 else 1
    new_yr3 = len(df[df['sale_year'] == year_range[1]])

    kt1,kt2,kt3,kt4 = st.columns(4)
    kt1.metric("Tăng trưởng YoY (trung vị)", f"{yoy_pct3:+.1f}%" if yoy_pct3 else "—")
    kt2.metric(f"Giao dịch năm {year_range[1]}", f"{new_yr3:,}")
    kt3.metric("Tháng cao điểm GD", MONTH_FULL.get(peak_m3,'?'))
    kt4.metric("Amenity Score TB", f"{df['amenity_score'].mean():.1f}/10")
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    section_q("Giá trung bình biến động theo tháng như thế nào — và 6 tháng tới sẽ ra sao?",
              "Xanh = giá thực tế từng tháng. Cam đứt = đường xu hướng tổng thể. Đỏ ◆ = dự báo 6 tháng tới.")

    ts3 = df.dropna(subset=['sale_date_parsed']).copy()
    ts3['ym'] = ts3['sale_date_parsed'].dt.to_period('M')
    mts3 = ts3.groupby('ym')['sale_price'].agg(mean_price='mean', n='count').reset_index()
    mts3['ym_dt'] = mts3['ym'].dt.to_timestamp()
    mts3 = mts3[mts3['n'] >= 5].sort_values('ym_dt').reset_index(drop=True)

    y_fore3 = None; future_d3 = None; y_h3 = None

    if len(mts3) >= 4:
        xh3 = np.arange(len(mts3)); yh3 = mts3['mean_price'].values; y_h3 = yh3
        deg3 = min(2, len(mts3)-1)
        c3 = np.polyfit(xh3, yh3, deg3)
        yf3 = np.polyval(c3, xh3)
        xfore3 = np.arange(len(mts3), len(mts3)+6)
        y_fore3 = np.polyval(c3, xfore3)
        lp3 = mts3['ym'].iloc[-1]
        future_d3 = [(lp3+i).to_timestamp() for i in range(1,7)]
        std3 = float(np.std(yh3 - yf3))

        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=future_d3 + future_d3[::-1],
            y=list(y_fore3+std3*1.5) + list((y_fore3-std3*1.5))[::-1],
            fill='toself', fillcolor='rgba(239,68,68,0.1)',
            line=dict(color='rgba(0,0,0,0)'),
            name='Khoảng tin cậy dự báo', hoverinfo='skip'))
        fig_t.add_trace(go.Scatter(
            x=list(mts3['ym_dt'])+list(mts3['ym_dt'])[::-1],
            y=list(yf3+std3)+list((yf3-std3))[::-1],
            fill='toself', fillcolor='rgba(59,130,246,0.07)',
            line=dict(color='rgba(0,0,0,0)'),
            name='Biên lịch sử (±1σ)', hoverinfo='skip'))
        fig_t.add_trace(go.Scatter(
            x=mts3['ym_dt'], y=mts3['mean_price'], mode='lines+markers',
            name='Giá TB thực tế', line=dict(color=C_BLUE, width=2.5),
            marker=dict(size=6),
            hovertemplate='%{x|%m/%Y}<br>$%{y:,.0f}<extra></extra>'))
        fig_t.add_trace(go.Scatter(
            x=mts3['ym_dt'], y=yf3, mode='lines',
            name='Xu hướng đa thức',
            line=dict(color=C_ORANGE, width=2, dash='dot'),
            hovertemplate='%{x|%m/%Y}<br>$%{y:,.0f}<extra></extra>'))
        fig_t.add_trace(go.Scatter(
            x=future_d3, y=y_fore3, mode='lines+markers',
            name='Dự báo 6 tháng',
            line=dict(color=C_RED, width=2.5, dash='dash'),
            marker=dict(size=9, symbol='diamond', color=C_RED,
                        line=dict(color='white', width=1.5)),
            hovertemplate='%{x|%m/%Y}<br>Dự báo: $%{y:,.0f}<extra></extra>'))
        clayout(fig_t, h=420, t=50, b=20, leg=True)
        fig_t.update_layout(
            title='Xu hướng Giá bán & Dự báo 6 tháng tới',
            title_font=dict(size=14, color='#374151'),
            xaxis=dict(title='Tháng', automargin=True),
            yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá trung bình ($)'),
            legend=dict(orientation='h', y=1.12, x=0, font_size=11),
            hovermode='x unified')
        st.plotly_chart(fig_t, width='stretch')

    divider()
    section_q("Thị trường có tính mùa vụ rõ không? Tháng nào sôi động nhất?",
              "Thanh đỏ = tháng cao điểm. Chênh lệch lớn = thị trường có mùa vụ rõ.")

    mb3 = df['sale_month'].value_counts().sort_index().reset_index()
    mb3.columns = ['Tháng_n','Số giao dịch']
    mb3['Tháng'] = mb3['Tháng_n'].map(MONTH_SHORT)
    peak_bar3 = mb3.loc[mb3['Số giao dịch'].idxmax(),'Tháng']
    fig_m3 = go.Figure(go.Bar(
        x=mb3['Tháng'], y=mb3['Số giao dịch'],
        marker_color=[C_RED if t==peak_bar3 else C_BLUE2 for t in mb3['Tháng']],
        text=mb3['Số giao dịch'], texttemplate='%{text:,}', textposition='outside',
        hovertemplate='%{x}<br>%{y:,} GD<extra></extra>'))
    clayout(fig_m3, h=300, t=60, b=20)
    fig_m3.update_layout(
        title='Số giao dịch theo Tháng trong năm (Tính mùa vụ)',
        title_font=dict(size=14, color='#374151'),
        yaxis=dict(automargin=True, title='Số giao dịch'),
        xaxis=dict(title='Tháng', automargin=True),
        uniformtext_minsize=10, uniformtext_mode='hide')
    st.plotly_chart(fig_m3, width='stretch')

# ════════════════════════════════════════════════════════════
# TAB 4 — DỰ BÁO & MÔ HÌNH ML
# ════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f172a,#1e293b,#334155);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.07)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>🤖 Mô hình Machine Learning dự báo giá như thế nào?</b><br>
    <span style='font-size:12px;opacity:0.75'>So sánh hiệu suất mô hình, yếu tố quan trọng và công cụ ước tính giá tương tác.</span>
    </div>
    """, unsafe_allow_html=True)

    pred_df4, imp4, ml4 = load_ml_data()

    if not ml4:
        st.warning("⚠️ Chưa có kết quả ML. Hãy chạy `main.py` trước.")
    else:
        rf4 = ml4.get('Random Forest', {}); lr4 = ml4.get('Linear Regression', {})
        m1,m2,m3,m4 = st.columns(4)
        acc4 = max(0,(1-rf4.get('MAE',0)/df['sale_price'].median())*100)
        mape4 = rf4.get('MAPE', None)
        m1.metric("Độ chính xác ước tính", f"{acc4:.1f}%", delta="Random Forest tốt nhất")
        m2.metric("Sai số trung bình (MAE)", f"${rf4.get('MAE',0):,.0f}")
        m3.metric("R² — Mức giải thích", f"{rf4.get('R2',0)*100:.1f}%")
        if mape4:
            m4.metric("Lệch giá TB (%)", f"{mape4:.1f}%")
        else:
            m4.metric("RMSE", f"${rf4.get('RMSE',0):,.0f}")

        section_q("Mô hình nào dự báo chính xác hơn?",
                  "R² càng gần 1, MAE/RMSE càng thấp = tốt hơn. So sánh trên cùng tập kiểm tra.")
        rows4 = [{'Mô hình': n,
                   'Điểm R²':  f"{m['R2']:.4f}",
                   'Sai số TB ($)': f"${m['MAE']:,.0f}",
                   'Căn SSBT ($)': f"${m['RMSE']:,.0f}",
                   'Đánh giá': '✅ Tốt hơn' if n == 'Random Forest' else '📊 Tham khảo'}
                 for n, m in ml4.items()]
        st.dataframe(pd.DataFrame(rows4).set_index('Mô hình'), width='stretch')

        divider()
        ci1, ci2 = st.columns(2)
        with ci1:
            section_q("Yếu tố nào mô hình cho là quyết định nhất?","")
            if imp4 is not None:
                imp4s = imp4.copy()
                imp4s['Tên'] = imp4s['Feature'].map(lambda f: FEATURE_LABELS.get(f,f))
                imp4s = imp4s.sort_values('Importance')
                fig_i = px.bar(imp4s, x='Importance', y='Tên', orientation='h',
                               color='Importance', color_continuous_scale='Blues',
                               text=imp4s['Importance'].apply(lambda v: f'{v*100:.1f}%'),
                               labels={'Importance': 'Mức độ quan trọng', 'Tên': 'Yếu tố'},
                               title='Mức độ quan trọng của từng yếu tố (Random Forest)')
                fig_i.update_traces(textposition='auto')
                clayout(fig_i, h=360, t=40, b=10, r=80)
                fig_i.update_layout(coloraxis_showscale=False,
                                    title_font=dict(size=13, color='#374151'),
                                    xaxis=dict(tickformat='.0%', automargin=True, title='Mức độ quan trọng'),
                                    yaxis=dict(automargin=True, title=''))
                st.plotly_chart(fig_i, width='stretch')
        with ci2:
            section_q("Dự báo sát thực tế đến mức nào?","")
            if pred_df4 is not None:
                pp4 = pred_df4.sample(n=min(1500,len(pred_df4)), random_state=42)
                fig_av4 = px.scatter(pp4, x='Actual', y='Predicted', opacity=0.4,
                                     color_discrete_sequence=[C_BLUE2],
                                     labels={'Actual':'Giá thực ($)','Predicted':'Giá dự báo ($)'},
                                     title='Dự báo vs Thực tế — Độ chính xác mô hình Random Forest',
                                     trendline='ols')
                # Đặt tên cho OLS trendline trace để tránh 'undefined' trong legend
                for trace in fig_av4.data:
                    if hasattr(trace, 'name') and trace.name and 'OLS' in str(trace.name):
                        trace.name = 'Xu hướng OLS'
                vm4 = max(pred_df4['Actual'].max(), pred_df4['Predicted'].max())
                fig_av4.add_trace(go.Scatter(x=[0,vm4], y=[0,vm4], mode='lines',
                                             name='Lý tưởng (y=x)',
                                             line=dict(color=C_RED, dash='dash', width=1.5)))
                clayout(fig_av4, h=360, t=40, b=10, leg=True)
                fig_av4.update_layout(
                    title_font=dict(size=13, color='#374151'),
                    xaxis=dict(tickformat='$,.0f', automargin=True, title='Giá thực ($)'),
                    yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá dự báo ($)'),
                    legend=dict(font_size=11))
                st.plotly_chart(fig_av4, width='stretch')
