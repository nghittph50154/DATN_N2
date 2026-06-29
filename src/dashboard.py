import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os

# ════════════════════════════════════════════════════════════
# CẤU HÌNH TRANG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Phân tích Thị trường Bất động sản NYC",
    layout="wide",
    page_icon="🏙️",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; font-weight: 500; }
.main { background-color: #f0f4ff; }
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
# HẰNG SỐ & BẢN MÀU
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
# HELPER UI
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
    🏙️ Phân tích Thị trường Bất động sản NYC
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
    <span style='font-size:12px;opacity:0.88'>Tổng quan về quy mô, mặt bằng giá và cơ cấu thị trường
    bất động sản NYC trong bộ lọc hiện tại.</span>
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
        fig.update_layout(yaxis=dict(automargin=True), xaxis=dict(automargin=True),
                          title_font=dict(size=13, color='#374151'))
        st.plotly_chart(fig, width='stretch')
    with cb:
        fig = px.bar(bor_med.sort_values('Giá trung vị'), x='Giá trung vị', y='Borough', orientation='h',
                     color='Borough', color_discrete_map=BOROUGH_COLORS,
                     text=bor_med.sort_values('Giá trung vị')['Giá trung vị'].apply(fmt_M),
                     title="Giá trung vị theo quận ($)")
        fig.update_traces(textposition='auto')
        clayout(fig, h=280, t=40, r=100)
        fig.update_layout(yaxis=dict(automargin=True), xaxis=dict(tickformat='$,.0f', automargin=True),
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
                     points=False, labels={'building_type':'','sale_price':'Giá bán ($)'},
                     category_orders={'building_type': med_bt0.index.tolist()},
                     title="Phân bố giá theo loại hình (top 6)")
        clayout(fig, h=320, t=40, b=60, l=10, r=10)
        fig.update_layout(xaxis=dict(automargin=True, tickangle=-15, tickfont_size=10),
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

# ════════════════════════════════════════════════════════════
# TAB 1 — PHÂN TÍCH KHU VỰC
# ════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f766e,#0d9488,#34d399);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(16,185,129,0.3)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>🗺️ Borough và khu vực nào đang dẫn đầu thị trường?</b><br>
    <span style='font-size:12px;opacity:0.88'>Phân tích chênh lệch giá và hoạt động giao dịch
    theo từng quận và khu dân cư cụ thể.</span>
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

    section_q("Giá bán phân bố như thế nào trong từng quận?",
              "Đường giữa = trung vị. Hộp = khoảng tứ phân vị (25%–75%). Nhãn giá trung vị được ghi trực tiếp.")

    bor_ord1 = df.groupby('borough_name')['sale_price'].median().sort_values(ascending=False).index.tolist()
    fig = px.box(df, x='borough_name', y='sale_price', color='borough_name',
                 color_discrete_map=BOROUGH_COLORS, points=False,
                 labels={'borough_name':'Quận','sale_price':'Giá bán ($)'},
                 category_orders={'borough_name': bor_ord1})
    for b in bor_ord1:
        m = df[df['borough_name']==b]['sale_price'].median()
        fig.add_annotation(x=b, y=m, text=fmt_M(m), showarrow=False,
                           font=dict(size=11,color='#111827',weight=700),
                           yshift=20, bgcolor='rgba(255,255,255,0.88)', borderpad=3)
    clayout(fig, h=360, t=20, b=20)
    fig.update_layout(yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá bán ($)'),
                      xaxis=dict(automargin=True))
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
        fig.update_layout(yaxis=dict(automargin=True, tickfont_size=11), xaxis=dict(automargin=True),
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
            fig.update_layout(yaxis=dict(automargin=True, tickfont_size=11),
                              xaxis=dict(tickformat='$,.0f', automargin=True),
                              legend=dict(orientation='h', y=-0.1, x=0, font_size=11),
                              title_font=dict(size=13, color='#374151'))
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Không đủ dữ liệu giá/sqft.")

    divider()
    ppsf_insight = ""
    if top_n_ppsf_row is not None:
        ppsf_insight = (f"• Khu vực định giá cao nhất theo $/sqft: <b>{top_n_ppsf_row['Khu vực']}</b> "
                        f"({top_n_ppsf_row['borough_name']}) — trung vị "
                        f"<b>${top_n_ppsf_row['med_ppsf']:,.0f}/sqft</b>.")
    insight_box(f"""
    <b>📌 Khu vực nào đáng chú ý nhất?</b><br>
    • <b>{top_neigh.title()}</b> là khu vực sôi động nhất:
      <b>{top_n_cnt:,} giao dịch</b> ({top_n_cnt/len(df)*100:.1f}% thị trường đang lọc).<br>
    • Chênh lệch giá trung vị: <b>{top_bor_p}</b> ({fmt_M(bor_med_f.max())})
      so với thấp nhất ({fmt_M(bor_med_f.min())}) —
      khoảng cách <b>{bor_med_f.max()/bor_med_f.min():.1f}×</b>.<br>
    {ppsf_insight}
    """)

# ════════════════════════════════════════════════════════════
# TAB 2 — YẾU TỐ QUYẾT ĐỊNH GIÁ
# ════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#5b21b6,#7c3aed,#a78bfa);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(124,58,237,0.35)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>📐 Điều gì thực sự kéo giá bất động sản lên?</b><br>
    <span style='font-size:12px;opacity:0.88'>Phân tích tương quan và tác động của các yếu tố
    vật lý, kinh tế, địa lý đến giá bán thực tế.</span>
    </div>
    """, unsafe_allow_html=True)

    section_q("Diện tích có thực sự giải thích được giá bán?",
              "Dữ liệu được nhóm theo khoảng 200 sqft. Mỗi điểm = giá trung vị nhóm. "
              "Kích thước điểm = số giao dịch. Loại điểm bất thường từ p97 trở lên để giảm nhiễu.")

    df_sq = df[df['gross_sqft'].notna() & df['gross_sqft'].between(100,4000)].copy()
    df_sq = df_sq[df_sq['sale_price'] < df_sq['sale_price'].quantile(0.97)]
    corr_sq = df_sq['gross_sqft'].corr(df_sq['sale_price']) if len(df_sq) >= 20 else 0
    top_bt2_name = 'N/A'; top_bt2_ppsf = 0
    med_bt2 = pd.Series(dtype=float)

    if len(df_sq) >= 50:
        df_sq['bin'] = pd.cut(df_sq['gross_sqft'], bins=range(100,4200,200),
                              labels=[f"{i}–{i+200}" for i in range(100,4000,200)])
        ba = (df_sq.groupby('bin', observed=True)
              .agg(med_price=('sale_price','median'), cnt=('sale_price','count'),
                   sqft_mid=('gross_sqft','median')).reset_index())
        ba = ba[ba['cnt'] >= 10]
        fig = px.scatter(ba, x='sqft_mid', y='med_price', size='cnt', size_max=30,
                         color='med_price', color_continuous_scale='Blues', trendline='ols',
                         labels={'sqft_mid':'Diện tích trung vị (sqft)',
                                 'med_price':'Giá trung vị ($)','cnt':'Số GD'})
        clayout(fig, h=340, t=20, b=20)
        fig.update_layout(coloraxis_showscale=False,
                          yaxis=dict(tickformat='$,.0f', automargin=True),
                          xaxis=dict(automargin=True))
        st.plotly_chart(fig, width='stretch')
        st.caption(f"Tương quan Pearson: **r = {corr_sq:.3f}** ({len(df_sq):,} giao dịch có dữ liệu diện tích).")

    divider()
    section_q("Loại hình nào có giá/sqft cao nhất và biến động nhất?",
              "Biểu đồ phân bố kết hợp hộp số liệu. Chỉ giữ top 5 loại hình nhiều giao dịch nhất. Loại điểm bất thường >$5,000/sqft.")

    if len(df_ppsf) >= 20:
        top5_bt2 = df_ppsf['building_type'].value_counts().head(5).index
        df_vln2  = df_ppsf[df_ppsf['building_type'].isin(top5_bt2)]
        med_bt2  = df_vln2.groupby('building_type')['price_per_sqft'].median().sort_values(ascending=False)
        top_bt2_name = med_bt2.index[0]; top_bt2_ppsf = med_bt2.iloc[0]
        fig = px.violin(df_vln2, x='building_type', y='price_per_sqft',
                        box=True, points=False, color='building_type',
                        color_discrete_sequence=[C_BLUE,C_SKY,C_ORANGE,C_GREEN,'#8b5cf6'],
                        labels={'building_type':'Loại hình','price_per_sqft':'$/sqft'},
                        category_orders={'building_type': med_bt2.index.tolist()})
        for bn, mv in med_bt2.items():
            fig.add_annotation(x=bn, y=mv, text=f"${mv:,.0f}", showarrow=False,
                               font=dict(size=10,color='#1f2937',weight=600),
                               yshift=16, bgcolor='rgba(255,255,255,0.9)', borderpad=2)
        clayout(fig, h=360, t=20, b=60)
        fig.update_layout(xaxis=dict(automargin=True, tickangle=-12, tickfont_size=10),
                          yaxis=dict(tickformat='$,.0f', automargin=True, title='$/sqft'))
        st.plotly_chart(fig, width='stretch')

    divider()
    section_q("Yếu tố nào có tương quan mạnh nhất với giá bán?",
              "Chỉ giữ 5 biến có ý nghĩa kinh tế. r > 0.3 = đáng chú ý. r > 0.5 = tương quan mạnh. "
              "Màu đỏ = tương quan dương, xanh = tương quan âm.")

    cc_cols = ['sale_price','gross_sqft','building_age','avg_income','amenity_score']
    cc_lbl  = {'sale_price':'Giá bán','gross_sqft':'Diện tích',
               'building_age':'Tuổi CT','avg_income':'Thu nhập TB','amenity_score':'Tiện ích'}
    cc_data = df[cc_cols].dropna()
    cc_mat  = cc_data.corr()
    cc_mat.columns = [cc_lbl[c] for c in cc_mat.columns]
    cc_mat.index   = [cc_lbl[c] for c in cc_mat.index]
    fig = px.imshow(cc_mat, text_auto='.2f', color_continuous_scale='RdBu_r',
                    zmin=-1, zmax=1, aspect='equal')
    clayout(fig, h=320, t=20, b=20)
    fig.update_layout(coloraxis_colorbar=dict(title='r', len=0.8))
    st.plotly_chart(fig, width='stretch')

    divider()
    corr_inc2 = cc_data['sale_price'].corr(cc_data['avg_income'])
    corr_age2 = cc_data['sale_price'].corr(cc_data['building_age'])
    insight_box(f"""
    <b>📌 Điều gì kéo giá lên mạnh nhất?</b><br>
    • <b>Diện tích</b> là yếu tố vật lý quan trọng nhất — tương quan
      <b>r = {corr_sq:.3f}</b> với giá bán.<br>
    • <b>Thu nhập bình quân khu vực</b>: r = <b>{corr_inc2:.3f}</b> —
      sức mua cộng đồng ảnh hưởng trực tiếp đến mặt bằng giá.<br>
    • <b>Tuổi công trình</b>: r = <b>{corr_age2:.3f}</b>
      {'(nhà cũ hơn → giá thấp hơn)' if corr_age2 < 0 else '(tương quan dương)'}.<br>
    • Loại hình <b>{top_bt2_name}</b> có giá/sqft trung vị cao nhất:
      <b>${top_bt2_ppsf:,.0f}/sqft</b>.
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
              "Xanh = giá thực tế theo tháng. Cam nét chấm = xu hướng đa thức bậc 2. "
              "Đỏ ◆ = dự báo 6 tháng tới. Vùng mờ = khoảng tin cậy ±1σ.")

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
        fig_t.add_vline(x=future_d3[0].timestamp()*1000,
                        line_dash='dash', line_color=C_GRAY, line_width=1.2,
                        annotation_text='▶ Bắt đầu dự báo',
                        annotation_position='top left',
                        annotation_font=dict(color=C_GRAY, size=11))
        clayout(fig_t, h=420, t=30, b=20, leg=True)
        fig_t.update_layout(
            xaxis_title='Tháng',
            yaxis=dict(tickformat='$,.0f', automargin=True, title='Giá trung bình ($)'),
            legend=dict(orientation='h', y=1.08, x=0, font_size=11),
            hovermode='x unified')
        st.plotly_chart(fig_t, width='stretch')

        fore_tbl = pd.DataFrame({
            'Tháng dự báo': [d.strftime('%m/%Y') for d in future_d3],
            'Giá dự báo':   [f'${v:,.0f}' for v in y_fore3],
            'Khoảng thấp':  [f'${max(0,v-std3*1.5):,.0f}' for v in y_fore3],
            'Khoảng cao':   [f'${v+std3*1.5:,.0f}' for v in y_fore3],
            'Δ vs tháng trước': [
                f'{(y_fore3[i]/y_fore3[i-1]-1)*100:+.2f}%' if i > 0
                else f'{(y_fore3[0]/yh3[-1]-1)*100:+.2f}%'
                for i in range(6)
            ],
        })
        st.dataframe(fore_tbl, width='stretch', hide_index=True)
    else:
        st.info("⚠️ Cần ít nhất 4 tháng dữ liệu để vẽ đường xu hướng.")

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
    clayout(fig_m3, h=300, t=50, b=20)
    fig_m3.update_layout(
        yaxis=dict(automargin=True, title='Số giao dịch'), xaxis_title='Tháng',
        uniformtext_minsize=10, uniformtext_mode='hide',
        annotations=[dict(x=peak_bar3, y=mb3['Số giao dịch'].max(),
                          text=f"🔴 Cao điểm: {MONTH_FULL.get(peak_m3,'?')}",
                          showarrow=True, arrowhead=2, arrowcolor=C_RED,
                          font=dict(color=C_RED, size=11, weight=600),
                          yshift=22, bgcolor='rgba(255,255,255,0.9)', borderpad=4)])
    st.plotly_chart(fig_m3, width='stretch')

    if len(yrs3) >= 2:
        divider()
        section_q(f"Giá trung bình thay đổi thế nào từ {yrs3[-2]} sang {yrs3[-1]}?")
        yoy_b3 = df.groupby(['borough_name','sale_year'])['sale_price'].mean().reset_index()
        yoy_p3 = yoy_b3.pivot(index='borough_name', columns='sale_year',
                              values='sale_price').reset_index()
        if yrs3[-2] in yoy_p3.columns and yrs3[-1] in yoy_p3.columns:
            yoy_p3['YoY (%)'] = (yoy_p3[yrs3[-1]]/yoy_p3[yrs3[-2]]-1)*100
            yoy_p3 = yoy_p3.dropna(subset=['YoY (%)']).sort_values('YoY (%)')
            fig_yoy3 = go.Figure(go.Bar(
                x=yoy_p3['borough_name'], y=yoy_p3['YoY (%)'],
                marker_color=[C_GREEN if v>=0 else C_RED for v in yoy_p3['YoY (%)']],
                text=[f'{v:+.1f}%' for v in yoy_p3['YoY (%)']],
                textposition='outside',
                hovertemplate='%{x}<br>Tăng trưởng năm: %{y:+.1f}%<extra></extra>'))
            clayout(fig_yoy3, h=280, t=40, b=20)
            fig_yoy3.update_layout(
                yaxis=dict(tickformat='+.1f', ticksuffix='%', zeroline=True,
                           zerolinecolor='#d1d5db', automargin=True, title='Thay đổi (%)'),
                xaxis=dict(automargin=True),
                uniformtext_minsize=10, uniformtext_mode='hide')
            st.plotly_chart(fig_yoy3, width='stretch')

    divider()
    avg_monthly3 = mb3['Số giao dịch'].mean()
    if y_fore3 is not None and y_h3 is not None:
        chg3 = (y_fore3[-1]-y_h3[-1])/y_h3[-1]*100
        dir3 = "📈 tăng" if chg3 > 0 else "📉 giảm"
        insight_box(f"""
        <b>📌 Thị trường đang đi về đâu?</b><br>
        • Giá TB dự kiến <b>{dir3} {abs(chg3):.1f}%</b> trong 6 tháng tới —
          từ <b>${y_h3[-1]:,.0f}</b> → <b>${y_fore3[-1]:,.0f}</b>.<br>
        • Tháng sôi động nhất: <b>{MONTH_FULL.get(peak_m3,'?')}</b>
          ({monthly_cnt3.max():,} GD) — cao hơn trung bình <b>{monthly_cnt3.max()/avg_monthly3:.1f}×</b>.<br>
        • Tăng trưởng YoY (trung vị): <b>{yoy_pct3:+.1f}%</b>.<br>
        • ⚠️ Dự báo polynomial — mang tính tham khảo, không tính lãi suất / chính sách vĩ mô.
        """)
    else:
        insight_box(f"""
        <b>📌 Nhận xét xu hướng:</b><br>
        • Tháng sôi động nhất: <b>{MONTH_FULL.get(peak_m3,'?')}</b> ({monthly_cnt3.max():,} GD).<br>
        • Tăng trưởng YoY (trung vị): <b>{yoy_pct3:+.1f}%</b>.
        """)

# ════════════════════════════════════════════════════════════
# TAB 4 — DỰ BÁO & MÔ HÌNH ML
# ════════════════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f172a,#1e293b,#334155);border-radius:14px;
    padding:18px 24px;color:#fff;margin-bottom:22px;
    box-shadow:0 6px 24px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.07)'>
    <b style='font-size:15px;letter-spacing:-0.3px'>🤖 Mô hình Machine Learning dự báo giá như thế nào?</b><br>
    <span style='font-size:12px;opacity:0.75'>So sánh hiệu suất mô hình, yếu tố quan trọng
    và công cụ ước tính giá tương tác.</span>
    </div>
    """, unsafe_allow_html=True)

    pred_df4, imp4, ml4 = load_ml_data()

    if not ml4:
        st.warning("⚠️ Chưa có kết quả ML. Hãy chạy `main.py` trước.")
    else:
        rf4 = ml4.get('Random Forest', {}); lr4 = ml4.get('Linear Regression', {})
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("R² (Rừng ngẫu nhiên)",    f"{rf4.get('R2',0):.4f}",
                  delta=f"+{rf4.get('R2',0)-lr4.get('R2',0):.4f} so với Hồi quy tuyến tính")
        m2.metric("Sai số tuyệt đối (SAL)", f"${rf4.get('MAE',0):,.0f}")
        m3.metric("Căn bậc hai sai số bình phương", f"${rf4.get('RMSE',0):,.0f}")
        acc4 = max(0,(1-rf4.get('MAE',0)/df['sale_price'].median())*100)
        m4.metric("Độ chính xác ước tính", f"{acc4:.1f}%")
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

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
                               text=imp4s['Importance'].apply(lambda v: f'{v*100:.1f}%'))
                fig_i.update_traces(textposition='auto')
                clayout(fig_i, h=360, t=10, b=10, r=80)
                fig_i.update_layout(coloraxis_showscale=False,
                                    xaxis=dict(tickformat='.0%', automargin=True),
                                    yaxis=dict(automargin=True))
                st.plotly_chart(fig_i, width='stretch')
        with ci2:
            section_q("Dự báo sát thực tế đến mức nào?","")
            if pred_df4 is not None:
                pp4 = pred_df4.sample(n=min(1500,len(pred_df4)), random_state=42)
                fig_av4 = px.scatter(pp4, x='Actual', y='Predicted', opacity=0.4,
                                     color_discrete_sequence=[C_BLUE2],
                                     labels={'Actual':'Giá thực ($)','Predicted':'Giá dự báo ($)'},
                                     trendline='ols')
                vm4 = max(pred_df4['Actual'].max(), pred_df4['Predicted'].max())
                fig_av4.add_trace(go.Scatter(x=[0,vm4], y=[0,vm4], mode='lines',
                                             name='Lý tưởng (y=x)',
                                             line=dict(color=C_RED, dash='dash', width=1.5)))
                clayout(fig_av4, h=360, t=10, b=10, leg=True)
                fig_av4.update_layout(
                    xaxis=dict(tickformat='$,.0f', automargin=True),
                    yaxis=dict(tickformat='$,.0f', automargin=True),
                    legend=dict(font_size=11))
                st.plotly_chart(fig_av4, width='stretch')

        seg4 = None
        if pred_df4 is not None:
            divider()
            section_q("Mô hình chính xác hơn ở phân khúc giá nào?",
                      "Sai số thấp = tin cậy hơn. Phân khúc cao cấp thường khó dự báo hơn.")
            err4 = pred_df4.copy()
            err4['err_pct'] = (err4['Predicted']-err4['Actual']).abs()/err4['Actual']*100
            bins4 = [0,200_000,500_000,1_000_000,2_000_000,float('inf')]
            lb4   = ['< $200K','$200K–$500K','$500K–$1M','$1M–$2M','> $2M']
            err4['Phân khúc'] = pd.cut(err4['Actual'], bins=bins4, labels=lb4)
            seg4 = (err4.groupby('Phân khúc',observed=True)['err_pct']
                    .agg(Sai_so='mean',N='count').reset_index())
            seg4.columns = ['Phân khúc','Sai số TB (%)','Số mẫu']

            sc1, sc2 = st.columns(2)
            with sc1:
                fig_se = px.bar(seg4, x='Phân khúc', y='Sai số TB (%)',
                                color='Sai số TB (%)', color_continuous_scale='RdYlGn_r',
                                text=seg4['Sai số TB (%)'].apply(lambda v: f'{v:.1f}%'),
                                title="Sai số trung bình theo phân khúc giá")
                fig_se.update_traces(textposition='outside')
                clayout(fig_se, h=280, t=40, b=20)
                fig_se.update_layout(coloraxis_showscale=False, yaxis=dict(automargin=True),
                                     uniformtext_minsize=10, uniformtext_mode='hide',
                                     title_font=dict(size=13,color='#374151'))
                st.plotly_chart(fig_se, width='stretch')
            with sc2:
                fig_sn = px.bar(seg4, x='Phân khúc', y='Số mẫu',
                                color='Số mẫu', color_continuous_scale='Blues',
                                text='Số mẫu', title="Số mẫu kiểm tra theo phân khúc")
                fig_sn.update_traces(texttemplate='%{text:,}', textposition='outside')
                clayout(fig_sn, h=280, t=40, b=20)
                fig_sn.update_layout(coloraxis_showscale=False, yaxis=dict(automargin=True),
                                     uniformtext_minsize=10, uniformtext_mode='hide',
                                     title_font=dict(size=13,color='#374151'))
                st.plotly_chart(fig_sn, width='stretch')

        divider()
        section_q("Ước tính giá theo thông số tùy chỉnh",
                  "Điều chỉnh các thanh trượt để xem giá ước tính dựa trên mặt bằng thị trường "
                  "và mức độ ảnh hưởng đặc trưng của Rừng ngẫu nhiên (Random Forest).")

        df_v4 = df[df['gross_sqft'].notna() &
                   df['sale_price'].between(df['sale_price'].quantile(0.05),
                                            df['sale_price'].quantile(0.95))].copy()
        el, er = st.columns([3,2])
        with el:
            if len(df_v4) > 0:
                inp_sq = st.slider("🏗️ Diện tích tổng (sqft)", 100,
                                   int(df_v4['gross_sqft'].quantile(0.95)),
                                   int(df_v4['gross_sqft'].median()), step=50)
                inp_ag = st.slider("🕰️ Tuổi công trình (năm)", 0, 120,
                                   int(df_v4['building_age'].median()), step=1)
                inp_am = st.slider("🎯 Điểm tiện ích (0–10)", 0.0, 10.0,
                                   round(float(df_v4['amenity_score'].median()),1), step=0.1)
                inp_in = st.slider("💵 Thu nhập TB ($)",
                                   int(df_v4['avg_income'].min()),
                                   int(df_v4['avg_income'].max()),
                                   int(df_v4['avg_income'].median()), step=1000)
                inp_di = st.slider("📍 KC trung tâm (km)", 0.0,
                                   float(df_v4['dist_center'].max()),
                                   round(float(df_v4['dist_center'].median()),1), step=0.5)
        with er:
            if len(df_v4) > 0 and imp4 is not None:
                imp_d4 = dict(zip(imp4['Feature'], imp4['Importance']))
                def n4(v,c):
                    mn,mx = df_v4[c].min(), df_v4[c].max()
                    return (v-mn)/(mx-mn+1e-9) if mx>mn else 0.5
                sc4 = (n4(inp_sq,'gross_sqft')    * imp_d4.get('gross_sqft',0) +
                       (1-n4(inp_ag,'building_age'))* imp_d4.get('building_age',0) +
                       n4(inp_am,'amenity_score')  * imp_d4.get('amenity_score',0) +
                       n4(inp_in,'avg_income')      * imp_d4.get('avg_income',0) +
                       (1-n4(inp_di,'dist_center')) * imp_d4.get('dist_center',0))
                tw4 = sum(imp_d4.get(f,0) for f in
                          ['gross_sqft','building_age','amenity_score','avg_income','dist_center'])
                sn4  = sc4/(tw4+1e-9)
                mp4  = df_v4['sale_price'].mean()
                est4 = mp4*0.5 + sn4*(mp4*2.5-mp4*0.5)
                mae4 = rf4.get('MAE',393795)
                d4   = (est4-mp4)/mp4*100
                dc4  = C_GREEN if d4>=0 else C_RED
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#0f172a,#1e3a8a);
                border-radius:14px;padding:22px 20px;text-align:center;color:#fff;margin-top:8px'>
                    <div style='font-size:11px;opacity:0.5;text-transform:uppercase;
                    letter-spacing:.1em;margin-bottom:4px'>Giá ước tính</div>
                    <div style='font-size:32px;font-weight:900;letter-spacing:-1px'>${est4:,.0f}</div>
                    <div style='font-size:11px;opacity:0.45;margin:6px 0 2px'>Khoảng dao động</div>
                    <div style='font-size:14px;font-weight:600'>${max(0,est4-mae4):,.0f} – ${est4+mae4:,.0f}</div>
                    <hr style='border-color:rgba(255,255,255,0.12);margin:12px 0'>
                    <div style='font-size:11px;opacity:0.5'>So với giá TB thị trường</div>
                    <div style='font-size:20px;font-weight:700;color:{dc4}'>{d4:+.1f}%</div>
                    <div style='font-size:10px;opacity:0.3;margin-top:8px'>
                        ⚠️ Ước tính tham khảo · MAE ≈ ${mae4:,.0f}
                    </div>
                </div>""", unsafe_allow_html=True)
                fig_g4 = go.Figure(go.Indicator(
                    mode='gauge+number', value=est4/1e6,
                    number=dict(prefix='$',suffix='M',font_size=18),
                    gauge=dict(
                        axis=dict(range=[0, mp4*2.5/1e6]),
                        bar=dict(color=C_BLUE),
                        steps=[dict(range=[0,mp4*0.5/1e6],color='#f0fdf4'),
                               dict(range=[mp4*0.5/1e6,mp4/1e6],color='#dcfce7'),
                               dict(range=[mp4/1e6,mp4*2.5/1e6],color='#fef3c7')],
                        threshold=dict(line=dict(color=C_RED,width=2),
                                       thickness=0.75, value=mp4/1e6)),
                    title=dict(text='Giá (triệu $)',font_size=12)))
                fig_g4.update_layout(height=190, margin=dict(t=28,b=8,l=18,r=18))
                st.plotly_chart(fig_g4, width='stretch')

        divider()
        top_f4  = imp4['Feature'].iloc[imp4['Importance'].argmax()] if imp4 is not None else 'N/A'
        top_fl4 = FEATURE_LABELS.get(top_f4, top_f4)
        top_fi4 = imp4['Importance'].max() if imp4 is not None else 0
        bs4 = seg4.sort_values('Sai số TB (%)').iloc[0]  if seg4 is not None and len(seg4)>0 else None
        ws4 = seg4.sort_values('Sai số TB (%)').iloc[-1] if seg4 is not None and len(seg4)>0 else None
        seg_insight = ""
        if bs4 is not None:
            seg_insight = (f"• Chính xác nhất tại phân khúc <b>{bs4['Phân khúc']}</b> "
                           f"(sai số TB {bs4['Sai số TB (%)']:.1f}%), kém nhất tại "
                           f"<b>{ws4['Phân khúc']}</b> ({ws4['Sai số TB (%)']:.1f}%).")
        insight_box(f"""
        <b>📌 Mô hình dự báo nói gì?</b><br>
        • Rừng ngẫu nhiên (Random Forest) giải thích <b>{rf4.get('R2',0)*100:.1f}%</b> biến động giá
          (R² = {rf4.get('R2',0):.4f}), tốt hơn Hồi quy tuyến tính
          <b>{(rf4.get('R2',0)-lr4.get('R2',0))*100:.1f} điểm phần trăm</b>.<br>
        • Yếu tố quyết định nhất: <b>{top_fl4}</b> ({top_fi4*100:.1f}% mức độ ảnh hưởng).<br>
        {seg_insight}<br>
        • Hướng cải thiện: thêm tọa độ GPS, điểm tiện ích lân cận, thử <b>XGBoost / LightGBM</b>.
        """)
