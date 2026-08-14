"""
NYC Property Intelligence Platform
Merge + Enrich + Retrain + Comprehensive Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import math
import pickle
import warnings
warnings.filterwarnings("ignore")

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from xgboost import XGBRegressor

# ══════════════════════════════════════════════════════
st.set_page_config(
    page_title="NYC Property Intelligence",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (Light / White Theme) ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
* { font-family: 'Inter', sans-serif !important; }

/* Nền trắng toàn bộ */
.main, [data-testid="stAppViewContainer"] { background: #f8f9fc !important; }
.block-container { padding: 1.2rem 2rem 2rem; background: #f8f9fc; }

/* KPI card — nền trắng, viền nhẹ, shadow */
.kpi-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: .7rem;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
}
.kpi-card .label { color:#64748b;font-size:.72rem;font-weight:600;
    text-transform:uppercase;letter-spacing:.08em;margin:0 0 .3rem }
.kpi-card .val   { color:#0f172a;font-size:1.75rem;font-weight:800;margin:0 }
.kpi-card .sub   { color:#94a3b8;font-size:.7rem;margin:.2rem 0 0 }
.kpi-card .delta-up   { color:#16a34a;font-size:.75rem;font-weight:600 }
.kpi-card .delta-down { color:#dc2626;font-size:.75rem;font-weight:600 }

/* Section title */
.section-title {
    color:#1e293b;font-size:1.15rem;font-weight:700;
    border-left:4px solid #4f46e5;padding-left:.8rem;
    margin:1.4rem 0 .7rem;
}

/* Insight box */
.insight-box {
    background:#ffffff;
    border:1px solid #e2e8f0;border-radius:12px;
    padding:1rem 1.2rem;margin-bottom:.7rem;
    box-shadow:0 1px 4px rgba(0,0,0,.05);
}
.insight-box .icon { font-size:1.5rem }
.insight-box h4 { color:#1e40af;font-size:.85rem;font-weight:700;margin:.3rem 0 .2rem }
.insight-box p  { color:#64748b;font-size:.75rem;margin:0 }

/* Sidebar — xám nhạt */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"] * { color: #334155 !important; }
[data-testid="stSidebar"] .stRadio label { color:#334155 !important; }

/* Headers */
h1,h2,h3 { color: #0f172a !important; }
p, span, label { color: #334155; }

/* Divider */
hr { border-color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# DATA LOADING & MERGE
# ══════════════════════════════════════════════════════
BORO_NAME_MAP = {
    "The Bronx": "Bronx",
    "Manhattan": "Manhattan",
    "Brooklyn": "Brooklyn",
    "Queens": "Queens",
    "Staten Island": "Staten Island",
}

@st.cache_data
def load_borough_data():
    with open("nyc_combined_data.json", encoding="utf-8") as f:
        raw = json.load(f)
    records = {}
    for b in raw:
        r = {}
        for k, v in b.items():
            s = str(v).strip()
            s = re.sub(r'^USD\s*', '', s)
            s = re.sub(r'\s*per\s+\d+k.*$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'\s+yrs?$', '', s, flags=re.IGNORECASE)
            s = s.replace('%','').replace('$','').replace(',','').strip()
            try: r[k] = float(s)
            except: r[k] = v
        name = b["Quận"]
        records[name] = r
    return records

@st.cache_data
def load_real_estate():
    df = pd.read_csv("Dulieu_Cleaned_v2.csv", low_memory=False)
    df["sale_date_parsed"] = pd.to_datetime(df["sale_date_clean"], errors="coerce")
    df["sale_quarter"] = df["sale_date_parsed"].dt.quarter
    return df

@st.cache_data
def merge_datasets():
    df = load_real_estate()
    bdata = load_borough_data()

    # Map borough_name real estate → JSON key
    RE_TO_JSON = {
        "Manhattan":    "Manhattan",
        "Brooklyn":     "Brooklyn",
        "Queens":       "Queens",
        "Bronx":        "The Bronx",
        "Staten Island":"Staten Island",
    }
    COLS_TO_ADD = {
        "crime_rate":      "Tỷ_lệ_tổng_tội_phạm_per_100k_dân",
        "life_expectancy": "Tuổi_thọ_trung_bình_(năm)",
        "pm25":            "Chất_lượng_không_khí_PM2.5_(µg/m³)",
        "bachelor_pct":    "Tỷ_lệ_có_bằng_đại_học_%",
        "poverty_child":   "Tỷ_lệ_nghèo_trẻ_em_%",
        "gini":            "Chỉ_số_Gini",
        "subway_count":    "Số_ga_tàu_điện_ngầm_(OSM)",
        "commute_min":     "Thời_gian_di_chuyển_TB_(phút)",
        "renter_pct":      "Tỷ_lệ_thuê_nhà_%",
        "boro_income":     "Thu_nhập_trung_vị",
        "obesity_pct":     "Tỷ_lệ_béo_phì_%",
        "uninsured_pct":   "Tỷ_lệ_không_có_BHYT_%",
        "school_rating":   "Chất_lượng_trường_học_(thang_10)",
        "walk_score":      "Điểm_thân_thiện_đi_bộ_(Walk_Score)",
        "property_tax":    "Thuế_bất_động_sản_TB_%",
        "mcdonalds_count": "Số_cửa_hàng_McDonalds",
        "starbucks_count": "Số_cửa_hàng_Starbucks",
        "parks_count":     "Số_công_viên",
        "supermarkets_count": "Số_siêu_thị",
        "hospitals_count":  "Số_bệnh_viện_phòng_khám",
        "ev_charging_count": "Số_trạm_sạc_xe_điện",
    }
    for col_out, col_src in COLS_TO_ADD.items():
        df[col_out] = df["borough_name"].map(
            lambda b: bdata.get(RE_TO_JSON.get(b, b), {}).get(col_src, np.nan)
        )
    return df

# ── Livability score ──────────────────────────────────
ABSOLUTE_SCALES = {
    "crime_rate":      (0,    15000),
    "life_expectancy": (90,   60),
    "obesity_pct":     (0,    50),
    "uninsured_pct":   (0,    30),
    "boro_income":     (150000, 0),
    "pm25":            (0,    25),
    "poverty_child":   (0,    60),
    "bachelor_pct":    (100,  0),
    "school_rating":   (10,   0),
    "walk_score":      (100,  0),
    "starbucks_count": (210,  0),
    "parks_count":     (1100, 0),
    "supermarkets_count": (600, 0),
    "hospitals_count":  (350, 0),
    "ev_charging_count": (60,  0),
}

def livability(boro_row):
    MAP_KEYS = {
        "Tỷ_lệ_tổng_tội_phạm_per_100k_dân": "crime_rate",
        "Tuổi_thọ_trung_bình_(năm)": "life_expectancy",
        "Tỷ_lệ_béo_phì_%": "obesity_pct",
        "Tỷ_lệ_không_có_BHYT_%": "uninsured_pct",
        "Thu_nhập_trung_vị": "boro_income",
        "Tỷ_lệ_nghèo_trẻ_em_%": "poverty_child",
        "Tỷ_lệ_có_bằng_đại_học_%": "bachelor_pct",
        "Chất_lượng_không_khí_PM2.5_(µg/m³)": "pm25",
        "Chất_lượng_trường_học_(thang_10)": "school_rating",
        "Điểm_thân_thiện_đi_bộ_(Walk_Score)": "walk_score",
        "Số_ga_tàu_điện_ngầm_(OSM)": "subway_count",
        "Số_cửa_hàng_McDonalds": "mcdonalds_count",
        "Số_cửa_hàng_Starbucks": "starbucks_count",
        "Số_công_viên": "parks_count",
        "Số_siêu_thị": "supermarkets_count",
        "Số_bệnh_viện_phòng_khám": "hospitals_count",
        "Số_trạm_sạc_xe_điện": "ev_charging_count",
    }
    row = {}
    for vk, ek in MAP_KEYS.items():
        v = boro_row.get(vk, np.nan)
        if isinstance(v, str):
            v = v.replace("%","").replace("$","").replace(",","").strip()
        try: row[ek] = float(v)
        except: row[ek] = np.nan

    def sc(col, best, worst):
        v = row.get(col, np.nan)
        if pd.isna(v): return 0.5
        return max(0, min(1, (float(v)-worst)/(best-worst)))

    return round(
        sc("crime_rate",      0,    15000) * 15 +
        (sc("life_expectancy",90,60)*0.5 + sc("obesity_pct",0,50)*0.25 + sc("uninsured_pct",0,30)*0.25) * 15 +
        (sc("boro_income",150000,0)*0.5 + sc("poverty_child",0,60)*0.3) * 15 +
        (sc("bachelor_pct",    100,  0)*0.5 + sc("school_rating", 10, 0)*0.5) * 15 +
        (sc("pm25",            0,    25)*0.5 + sc("parks_count", 1100, 0)*0.5) * 15 +
        (sc("subway_count",    300,  0)*0.5 + sc("walk_score", 100, 0)*0.5) * 15 +
        (sc("starbucks_count", 210,  0)*0.4 + sc("supermarkets_count", 600, 0)*0.4 + sc("hospitals_count", 350, 0)*0.2) * 10
    , 1)

# ── ML model ─────────────────────────────────────────
@st.cache_resource
def train_model(df):
    dft = df.copy()
    dft["log_price"] = np.log1p(dft["sale_price"])
    for col in ["borough_name","building_category","building_type","neighborhood"]:
        if col in dft.columns:
            le = LabelEncoder()
            dft[col+"_enc"] = le.fit_transform(dft[col].fillna("UNKNOWN").astype(str))
    neigh_med = dft.groupby("neighborhood")["log_price"].median()
    dft["neighborhood_target"] = dft["neighborhood"].map(neigh_med)
    bcat_med  = dft.groupby("building_category")["log_price"].median()
    dft["bcat_target"] = dft["building_category"].map(bcat_med)
    dft["sale_quarter"] = pd.to_datetime(dft["sale_date_clean"], errors="coerce").dt.quarter
    dft["is_condo"]  = dft["building_category"].str.contains("CONDO", na=False).astype(int)
    dft["sqft_x_age"] = dft["gross_sqft"].fillna(0) * dft["building_age_calc"].fillna(70)
    dft["income_x_amenity"] = dft["avg_income"] * dft["amenity_score"]

    FEATS = ["gross_sqft","land_sqft","total_units","residential_units","commercial_units",
             "building_age_calc","pop_density","avg_income","gdp_local","dist_center",
             "amenity_score","borough_name_enc","building_category_enc","building_type_enc",
             "neighborhood_target","bcat_target","sale_year","sale_quarter","sale_month",
             "is_residential","is_condo","has_sqft","tax_class_sale","sqft_x_age",
             "income_x_amenity",
             # Borough socioeconomic (NEW)
             "crime_rate","life_expectancy","pm25","bachelor_pct",
             "poverty_child","gini","subway_count","commute_min","boro_income",
             "school_rating","walk_score","property_tax",
             "mcdonalds_count","starbucks_count","parks_count","supermarkets_count","hospitals_count","ev_charging_count"]
    FEATS = [f for f in FEATS if f in dft.columns]

    X = dft[FEATS].copy()
    y = dft["log_price"]
    imp = SimpleImputer(strategy="median")
    Xi  = imp.fit_transform(X)
    Xtr,Xte,ytr,yte = train_test_split(Xi, y, test_size=0.2, random_state=42)

    model = XGBRegressor(n_estimators=500, max_depth=7, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8,
                         reg_alpha=0.5, reg_lambda=2,
                         random_state=42, verbosity=0, n_jobs=-1)
    model.fit(Xtr, ytr)
    pred  = np.expm1(model.predict(Xte))
    r2    = r2_score(yte, model.predict(Xte))
    mae   = mean_absolute_error(np.expm1(yte), pred)

    n_feats = len(model.feature_importances_)
    imp_df = pd.DataFrame({"Feature": FEATS[:n_feats], "Importance": model.feature_importances_})\
               .sort_values("Importance", ascending=False)

    return model, imp, FEATS, r2, mae, imp_df

# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════
COLORS = {
    "Manhattan":"#4f46e5","Brooklyn":"#0891b2",
    "Queens":"#059669","Bronx":"#dc2626","Staten Island":"#d97706"
}
def hex_rgba(h, a=.15):
    h=h.lstrip('#'); r,g,b=int(h[:2],16),int(h[2:4],16),int(h[4:],16)
    return f"rgba({r},{g},{b},{a})"

# Light theme layout cho plotly
LAYOUT = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8f9fc",
    font=dict(color="#334155", family="Inter"),
    margin=dict(t=20,b=10,l=10,r=10)
)

def fig_layout(fig, **kw):
    fig.update_layout(**LAYOUT, **kw)
    return fig

# ══════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════
with st.spinner("Đang tải & xử lý dữ liệu..."):
    df = merge_datasets()
    bdata = load_borough_data()

BOROUGHS = ["Manhattan","Brooklyn","Queens","Bronx","Staten Island"]
BORO_JSON = {"Manhattan":"Manhattan","Brooklyn":"Brooklyn",
             "Queens":"Queens","Bronx":"The Bronx","Staten Island":"Staten Island"}

# Livability per borough
LSCORE = {b: livability(bdata.get(BORO_JSON[b],{})) for b in BOROUGHS}

# Investment score = livability_normalized × price_affordability
med_price = df.groupby("borough_name")["sale_price"].median()
max_med = med_price.max()
INVEST_SCORE = {
    b: round(LSCORE[b] * 0.6 + (1 - med_price.get(b,max_med)/max_med)*100*0.4, 1)
    for b in BOROUGHS
}

# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🗽 NYC Smart Property Guide")
    st.caption("Cẩm nang Mua nhà & Đầu tư Thông minh\nDữ liệu 42,017 giao dịch & 40+ tiện ích")
    st.markdown("---")
    page = st.radio("📍 Chế độ xem", [
        "🏠 Khám phá Thị trường BĐS",
        "💡 Tư vấn Định cư & Đầu tư",
        "🔮 Định giá AI & Tài chính",
        "🏙️ Đánh giá Chất lượng Sống",
        "📈 Cơ hội & Tăng trưởng",
        "🛡️ Kiểm chứng Độ tin cậy AI",
    ], label_visibility="collapsed")
    st.markdown("---")
    sel_boros = st.multiselect("Lọc quận nghiên cứu:", BOROUGHS, default=BOROUGHS)
    dff = df[df["borough_name"].isin(sel_boros)].copy()
    st.markdown("---")
    st.caption("**Nguồn dữ liệu an toàn:**\n• NYPD CompStat 2025\n• RWJF Health Rankings 2024\n• Census ACS 2023\n• OSM Overpass 2025\n• Hệ thống BĐS NYC 2025–2026")

# ══════════════════════════════════════════════════════
# PAGE 1: KHÁM PHÁ THỊ TRƯỜNG BĐS
# ══════════════════════════════════════════════════════
if page == "🏠 Khám phá Thị trường BĐS":
    st.markdown("# 🗽 Khám phá Thị trường Bất động sản NYC")
    st.markdown("**42,017 giao dịch BĐS (2025–2026)** × **40+ chỉ số kinh tế-xã hội** — phân tích toàn diện thị trường bất động sản NYC")

    # KPI row
    col1,col2,col3,col4,col5 = st.columns(5)
    total_vol  = len(dff)
    avg_price  = dff["sale_price"].mean()
    med_price2 = dff["sale_price"].median()
    avg_ppf    = dff["price_per_sqft_calc"].dropna().mean()
    # YoY
    p25 = dff[dff["sale_year"]==2025]["sale_price"].median()
    p26 = dff[dff["sale_year"]==2026]["sale_price"].median()
    yoy = (p26-p25)/p25*100 if p25>0 else 0

    for col, label, val, sub, delta in [
        (col1,"Giao dịch",   f"{total_vol:,}","2025–2026",None),
        (col2,"Giá TB",      f"${avg_price/1e6:.2f}M","trung bình",None),
        (col3,"Giá trung vị",f"${med_price2/1e3:.0f}K","median",None),
        (col4,"$/sqft TB",   f"${avg_ppf:,.0f}" if not np.isnan(avg_ppf) else "N/A","price per sqft",None),
        (col5,"Tăng trưởng YoY",f"{yoy:+.1f}%","2025 → 2026",yoy),
    ]:
        d_html = ""
        if delta is not None:
            cls = "delta-up" if delta >= 0 else "delta-down"
            icon = "▲" if delta >= 0 else "▼"
            d_html = f'<p class="{cls}">{icon} so với 2025</p>'
        col.markdown(f"""<div class="kpi-card">
            <p class="label">{label}</p>
            <p class="val">{val}</p>
            <p class="sub">{sub}</p>{d_html}
        </div>""", unsafe_allow_html=True)

    # ══ INNOVATION DASHBOARD ══════════════════════════════
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e1b4b 0%,#312e81 50%,#1e40af 100%);
                border-radius:18px;padding:1.6rem 2rem 1.2rem;margin:1rem 0 1.2rem;">
        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:.6rem">
            <span style="font-size:2rem">🚀</span>
            <div>
                <p style="color:#e0e7ff;font-size:.7rem;font-weight:700;letter-spacing:.12em;margin:0;text-transform:uppercase">
                    Lợi thế Công nghệ
                </p>
                <h2 style="color:#ffffff;font-size:1.4rem;font-weight:900;margin:0;line-height:1.2">
                    40+ Chỉ số Độc quyền — Mà Các Nền Tảng Khác Không Có
                </h2>
            </div>
        </div>
        <p style="color:#c7d2fe;font-size:.82rem;margin:.3rem 0 0;max-width:700px">
            Trong khi các trang BĐS thông thường chỉ dùng <b style="color:#fbbf24">3–5 chỉ số</b> (diện tích, giá, vị trí),
            nền tảng này phân tích <b style="color:#fbbf24">40+ chỉ số</b> kinh tế-xã hội thực tế để cho bạn biết
            <i>nơi đó thực sự đáng sống hay không</i> — không chỉ đắt hay rẻ.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 5 Pillar cards + Radar ──────────────────────────
    st.markdown('<div class="section-title">📊 5 Nhóm Chỉ số Phân tích Độc quyền</div>', unsafe_allow_html=True)

    # Pull live bdata values for quick "city average" or best borough
    def _safe(b_key, field):
        v = bdata.get(b_key, {}).get(field, None)
        try: return float(v)
        except: return None

    PILLARS = [
        {
            "icon": "🛡️",
            "name": "An toàn & Trị an",
            "color": "#dc2626",
            "bg": "#fef2f2",
            "border": "#fecaca",
            "indices": ["Tỷ lệ tội phạm / 100k dân", "Mật độ đèn đường", "Tỷ lệ tội phạm bạo lực"],
            "insight": lambda: f"Bronx {_safe('The Bronx','Tỷ_lệ_tổng_tội_phạm_per_100k_dân') or '—':.0f} vs Manhattan {_safe('Manhattan','Tỷ_lệ_tổng_tội_phạm_per_100k_dân') or '—':.0f} vụ/100k" if _safe('The Bronx','Tỷ_lệ_tổng_tội_phạm_per_100k_dân') else "Dữ liệu NYPD 2025",
            "why": "Biết nơi bạn định sống có an toàn không — TRƯỚC khi mua"
        },
        {
            "icon": "💚",
            "name": "Sức khỏe & Y tế",
            "color": "#059669",
            "bg": "#f0fdf4",
            "border": "#bbf7d0",
            "indices": ["Tuổi thọ trung bình", "Tỷ lệ béo phì", "Không có bảo hiểm y tế", "Số bệnh viện / phòng khám"],
            "insight": lambda: f"Tuổi thọ TB: {_safe('Manhattan','Tuổi_thọ_trung_bình_(năm)') or 83:.0f} tuổi (Manhattan) vs {_safe('The Bronx','Tuổi_thọ_trung_bình_(năm)') or 76:.0f} (Bronx)",
            "why": "Môi trường sống ảnh hưởng trực tiếp đến sức khỏe gia đình bạn"
        },
        {
            "icon": "🎓",
            "name": "Giáo dục & Dân trí",
            "color": "#7c3aed",
            "bg": "#faf5ff",
            "border": "#e9d5ff",
            "indices": ["Tỷ lệ có bằng đại học", "Chất lượng trường học (1–10)", "Tỷ lệ nghèo trẻ em"],
            "insight": lambda: f"Manhattan: {_safe('Manhattan','Tỷ_lệ_có_bằng_đại_học_%') or 62:.0f}% có bằng ĐH — gần gấp đôi Bronx ({_safe('The Bronx','Tỷ_lệ_có_bằng_đại_học_%') or 28:.0f}%)",
            "why": "Trường tốt = con cái bạn có tương lai tốt hơn"
        },
        {
            "icon": "🌿",
            "name": "Môi trường sống",
            "color": "#0891b2",
            "bg": "#f0f9ff",
            "border": "#bae6fd",
            "indices": ["Chỉ số PM2.5 (bụi mịn)", "Số công viên / cây xanh", "Trạm sạc xe điện", "Walk Score"],
            "insight": lambda: f"Queens: {_safe('Queens','Số_công_viên') or 1011:.0f} công viên — nhiều nhất NYC",
            "why": "Bạn hít thở không khí gì mỗi ngày ở đó"
        },
        {
            "icon": "🚇",
            "name": "Tiện ích & Hạ tầng",
            "color": "#d97706",
            "bg": "#fffbeb",
            "border": "#fde68a",
            "indices": ["Số ga Metro", "Thời gian di chuyển TB", "Số siêu thị / Starbucks / McDonald's", "Thuế BĐS TB"],
            "insight": lambda: f"Manhattan: {_safe('Manhattan','Số_ga_tàu_điện_ngầm_(OSM)') or 147:.0f} ga Metro — di chuyển dễ nhất",
            "why": "Nhà tiện nghi quyết định chất lượng sống hàng ngày"
        },
    ]

    pillar_cols = st.columns(5)
    for i, p in enumerate(PILLARS):
        with pillar_cols[i]:
            indices_html = "".join(
                f'<p style="color:#475569;font-size:.68rem;margin:.1rem 0;padding:.15rem .4rem;background:#f1f5f9;border-radius:4px">• {idx}</p>'
                for idx in p["indices"]
            )
            try: insight_text = p["insight"]()
            except: insight_text = ""
            st.markdown(f"""
            <div style="background:{p['bg']};border:1.5px solid {p['border']};
                        border-radius:14px;padding:1rem;height:100%;min-height:230px">
                <div style="text-align:center;margin-bottom:.5rem">
                    <span style="font-size:1.8rem">{p['icon']}</span>
                    <p style="color:{p['color']};font-size:.78rem;font-weight:800;margin:.2rem 0 .5rem;
                               text-transform:uppercase;letter-spacing:.05em">{p['name']}</p>
                </div>
                {indices_html}
                <div style="background:{p['border']};border-radius:8px;padding:.45rem .6rem;margin-top:.6rem">
                    <p style="font-size:.65rem;color:{p['color']};font-weight:700;margin:0 0 .2rem">📌 Ví dụ thực tế</p>
                    <p style="font-size:.65rem;color:#334155;margin:0">{insight_text}</p>
                </div>
                <p style="font-size:.62rem;color:#94a3b8;font-style:italic;margin:.5rem 0 0;text-align:center">
                    💡 {p['why']}
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ── Radar: 5 quận × 5 nhóm chỉ số ─────────────────
    st.markdown('<div class="section-title">🕸️ Toàn cảnh 5 Nhóm Chỉ số — So sánh 5 Quận</div>', unsafe_allow_html=True)

    def _norm(val, best, worst):
        if val is None or (isinstance(val, float) and np.isnan(val)): return 50
        return round(max(0, min(100, (float(val) - worst) / (best - worst) * 100)), 1)

    radar_dims = ["An toàn", "Sức khỏe", "Giáo dục", "Môi trường", "Hạ tầng"]
    BORO_RADAR = {
        "Manhattan":    [_norm(_safe("Manhattan","Tỷ_lệ_tổng_tội_phạm_per_100k_dân"),0,15000),
                         _norm(_safe("Manhattan","Tuổi_thọ_trung_bình_(năm)"),90,60),
                         _norm(_safe("Manhattan","Tỷ_lệ_có_bằng_đại_học_%"),100,0),
                         _norm(_safe("Manhattan","Chất_lượng_không_khí_PM2.5_(µg/m³)"),0,25),
                         _norm(_safe("Manhattan","Số_ga_tàu_điện_ngầm_(OSM)"),300,0)],
        "Brooklyn":     [_norm(_safe("Brooklyn","Tỷ_lệ_tổng_tội_phạm_per_100k_dân"),0,15000),
                         _norm(_safe("Brooklyn","Tuổi_thọ_trung_bình_(năm)"),90,60),
                         _norm(_safe("Brooklyn","Tỷ_lệ_có_bằng_đại_học_%"),100,0),
                         _norm(_safe("Brooklyn","Chất_lượng_không_khí_PM2.5_(µg/m³)"),0,25),
                         _norm(_safe("Brooklyn","Số_ga_tàu_điện_ngầm_(OSM)"),300,0)],
        "Queens":       [_norm(_safe("Queens","Tỷ_lệ_tổng_tội_phạm_per_100k_dân"),0,15000),
                         _norm(_safe("Queens","Tuổi_thọ_trung_bình_(năm)"),90,60),
                         _norm(_safe("Queens","Tỷ_lệ_có_bằng_đại_học_%"),100,0),
                         _norm(_safe("Queens","Chất_lượng_không_khí_PM2.5_(µg/m³)"),0,25),
                         _norm(_safe("Queens","Số_ga_tàu_điện_ngầm_(OSM)"),300,0)],
        "Bronx":        [_norm(_safe("The Bronx","Tỷ_lệ_tổng_tội_phạm_per_100k_dân"),0,15000),
                         _norm(_safe("The Bronx","Tuổi_thọ_trung_bình_(năm)"),90,60),
                         _norm(_safe("The Bronx","Tỷ_lệ_có_bằng_đại_học_%"),100,0),
                         _norm(_safe("The Bronx","Chất_lượng_không_khí_PM2.5_(µg/m³)"),0,25),
                         _norm(_safe("The Bronx","Số_ga_tàu_điện_ngầm_(OSM)"),300,0)],
        "Staten Island":[_norm(_safe("Staten Island","Tỷ_lệ_tổng_tội_phạm_per_100k_dân"),0,15000),
                         _norm(_safe("Staten Island","Tuổi_thọ_trung_bình_(năm)"),90,60),
                         _norm(_safe("Staten Island","Tỷ_lệ_có_bằng_đại_học_%"),100,0),
                         _norm(_safe("Staten Island","Chất_lượng_không_khí_PM2.5_(µg/m³)"),0,25),
                         _norm(_safe("Staten Island","Số_ga_tàu_điện_ngầm_(OSM)"),300,0)],
    }

    rc1, rc2 = st.columns([3, 2])
    with rc1:
        fig_radar = go.Figure()
        for boro in sel_boros:
            vals = BORO_RADAR.get(boro, [50]*5)
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=radar_dims + [radar_dims[0]],
                fill="toself",
                name=boro,
                line=dict(color=COLORS[boro], width=2),
                fillcolor=hex_rgba(COLORS[boro], .15),
                hovertemplate="%{theta}: %{r:.0f}/100<extra>" + boro + "</extra>"
            ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor="#f8f9fc",
                radialaxis=dict(visible=True, range=[0,100], tickfont=dict(size=9,color="#94a3b8"),
                                gridcolor="#e2e8f0", linecolor="#e2e8f0"),
                angularaxis=dict(tickfont=dict(size=11, color="#334155", family="Inter"), linecolor="#cbd5e1"),
            ),
            paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
                        font=dict(size=11,color="#334155")),
            height=360,
            margin=dict(t=20,b=40,l=40,r=40)
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with rc2:
        st.markdown("""
        <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:1.2rem;margin-top:.5rem">
            <p style="color:#1e293b;font-weight:800;font-size:.9rem;margin:0 0 .8rem">
                🆚 So sánh với Nền tảng Khác
            </p>
            <table style="width:100%;font-size:.72rem;border-collapse:collapse">
                <tr style="background:#f1f5f9">
                    <th style="padding:.4rem .6rem;color:#64748b;text-align:left;border-radius:6px 0 0 6px">Tính năng</th>
                    <th style="padding:.4rem .6rem;color:#4f46e5;text-align:center">Nền tảng này</th>
                    <th style="padding:.4rem .6rem;color:#94a3b8;text-align:center">Nền tảng khác</th>
                </tr>
                <tr><td style="padding:.35rem .6rem;color:#475569;border-bottom:1px solid #f1f5f9">Số chỉ số phân tích</td>
                    <td style="text-align:center;color:#059669;font-weight:700">40+</td>
                    <td style="text-align:center;color:#94a3b8">3–5</td></tr>
                <tr style="background:#fafafa"><td style="padding:.35rem .6rem;color:#475569;border-bottom:1px solid #f1f5f9">Dữ liệu tội phạm thực</td>
                    <td style="text-align:center">✅</td><td style="text-align:center">❌</td></tr>
                <tr><td style="padding:.35rem .6rem;color:#475569;border-bottom:1px solid #f1f5f9">Chất lượng không khí</td>
                    <td style="text-align:center">✅</td><td style="text-align:center">❌</td></tr>
                <tr style="background:#fafafa"><td style="padding:.35rem .6rem;color:#475569;border-bottom:1px solid #f1f5f9">Trường học + Y tế</td>
                    <td style="text-align:center">✅</td><td style="text-align:center">❌</td></tr>
                <tr><td style="padding:.35rem .6rem;color:#475569;border-bottom:1px solid #f1f5f9">AI định giá nhà</td>
                    <td style="text-align:center">✅</td><td style="text-align:center">❌</td></tr>
                <tr style="background:#fafafa"><td style="padding:.35rem .6rem;color:#475569">Giao thông / Tiện ích</td>
                    <td style="text-align:center">✅</td><td style="text-align:center">⚠️ Một phần</td></tr>
            </table>
            <div style="background:linear-gradient(135deg,#f0f9ff,#e0f2fe);border-radius:10px;
                        padding:.8rem;margin-top:.8rem;border-left:3px solid #0891b2">
                <p style="color:#0891b2;font-size:.72rem;font-weight:700;margin:0 0 .3rem">
                    💡 Tại sao điều này quan trọng?
                </p>
                <p style="color:#475569;font-size:.68rem;margin:0">
                    Mua nhà là quyết định lớn nhất đời. 40+ chỉ số giúp bạn thấy bức tranh
                    <b>đầy đủ và thực tế</b> — không chỉ giá cả.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns([3,2])

    with c1:
        st.markdown('<div class="section-title">💰 Phân phối giá theo quận</div>', unsafe_allow_html=True)
        fig = go.Figure()
        for b in sel_boros:
            sub = dff[dff["borough_name"]==b]["sale_price"]/1e3
            fig.add_trace(go.Box(
                y=sub, name=b,
                marker_color=COLORS[b],
                line_color=COLORS[b],
                fillcolor=hex_rgba(COLORS[b],.3),
                boxpoints="outliers",
                marker_size=3,
            ))
        fig_layout(fig, yaxis=dict(gridcolor="#e2e8f0", tickprefix="$", ticksuffix="K"),
                   height=340, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ══ BẢNG 40+ CHỈ SỐ CRAWL ═══════════════════════════
    st.markdown("---")
    st.markdown('<div class="section-title">📋 Bảng Chi tiết 40+ Chỉ số Kinh tế–Xã hội (Dữ liệu Crawl Thực tế)</div>', unsafe_allow_html=True)
    st.caption("Toàn bộ dữ liệu được thu thập từ NYPD, Census ACS, RWJF, OpenStreetMap — cập nhật 2024–2025. Màu xanh = tốt hơn, màu đỏ = kém hơn.")

    # Định nghĩa tất cả chỉ số: (tên hiển thị, key trong bdata, đơn vị, best_is_high)
    ALL_INDICES = [
        # ── AN TOÀN ──
        ("🛡️ Tỷ lệ tội phạm tổng / 100k dân",        "Tỷ_lệ_tổng_tội_phạm_per_100k_dân",          "vụ/100k",  False),
        ("🛡️ Tỷ lệ tội phạm bạo lực / 100k dân",      "Tỷ_lệ_tội_phạm_bạo_lực_per_100k",           "vụ/100k",  False),
        # ── SỨC KHỎE ──
        ("💚 Tuổi thọ trung bình",                     "Tuổi_thọ_trung_bình_(năm)",                  "tuổi",     True),
        ("💚 Tỷ lệ béo phì",                           "Tỷ_lệ_béo_phì_%",                            "%",        False),
        ("💚 Tỷ lệ không có BHYT",                     "Tỷ_lệ_không_có_BHYT_%",                      "%",        False),
        ("💚 Số bệnh viện / phòng khám",               "Số_bệnh_viện_phòng_khám",                    "cơ sở",    True),
        # ── KINH TẾ ──
        ("💰 Thu nhập trung vị hộ gia đình",           "Thu_nhập_trung_vị",                           "$",        True),
        ("💰 Chỉ số Gini (bất bình đẳng)",             "Chỉ_số_Gini",                                 "",         False),
        ("💰 Tỷ lệ nghèo trẻ em",                      "Tỷ_lệ_nghèo_trẻ_em_%",                       "%",        False),
        ("💰 Tỷ lệ thuê nhà",                          "Tỷ_lệ_thuê_nhà_%",                            "%",        False),
        ("💰 Thuế BĐS trung bình",                     "Thuế_bất_động_sản_TB_%",                      "%",        False),
        # ── GIÁO DỤC ──
        ("🎓 Tỷ lệ có bằng đại học",                  "Tỷ_lệ_có_bằng_đại_học_%",                    "%",        True),
        ("🎓 Chất lượng trường học (1–10)",            "Chất_lượng_trường_học_(thang_10)",            "/10",      True),
        # ── MÔI TRƯỜNG ──
        ("🌿 Chất lượng không khí PM2.5",              "Chất_lượng_không_khí_PM2.5_(µg/m³)",         "µg/m³",    False),
        ("🌿 Số công viên / cây xanh",                 "Số_công_viên",                                "công viên",True),
        ("🌿 Số trạm sạc xe điện",                     "Số_trạm_sạc_xe_điện",                         "trạm",     True),
        ("🌿 Walk Score (thân thiện đi bộ)",            "Điểm_thân_thiện_đi_bộ_(Walk_Score)",          "/100",     True),
        # ── HẠ TẦNG & TIỆN ÍCH ──
        ("🚇 Số ga tàu điện ngầm (OSM)",               "Số_ga_tàu_điện_ngầm_(OSM)",                   "ga",       True),
        ("🚇 Thời gian di chuyển TB",                  "Thời_gian_di_chuyển_TB_(phút)",               "phút",     False),
        ("🏪 Số siêu thị",                             "Số_siêu_thị",                                 "cửa hàng", True),
        ("🏪 Số cửa hàng Starbucks",                   "Số_cửa_hàng_Starbucks",                       "cửa hàng", True),
        ("🏪 Số cửa hàng McDonald's",                  "Số_cửa_hàng_McDonalds",                       "cửa hàng", True),
    ]

    BORO_KEYS = {
        "Manhattan":    "Manhattan",
        "Brooklyn":     "Brooklyn",
        "Queens":       "Queens",
        "Bronx":        "The Bronx",
        "Staten Island":"Staten Island",
    }

    def _fmt(v, unit):
        if v is None: return "—"
        try:
            fv = float(v)
            if unit == "$":    return f"${fv:,.0f}"
            if unit == "tuổi": return f"{fv:.1f}"
            if unit in ("%", "/10", "/100"): return f"{fv:.1f}{unit}"
            return f"{fv:,.0f} {unit}".strip()
        except:
            return str(v)

    def _color_cell(val, all_vals, best_is_high):
        """Return background color based on rank among boroughs."""
        try:
            nums = [float(x) for x in all_vals if x is not None]
            if not nums: return "#f8f9fc"
            mn, mx = min(nums), max(nums)
            if mx == mn: return "#f8f9fc"
            norm = (float(val) - mn) / (mx - mn)   # 0=worst, 1=best
            if not best_is_high: norm = 1 - norm
            # green shades: 0→red, 0.5→yellow, 1→green
            if norm >= 0.75:   return "#dcfce7"
            elif norm >= 0.5:  return "#fef9c3"
            elif norm >= 0.25: return "#ffedd5"
            else:              return "#fee2e2"
        except:
            return "#f8f9fc"

    # Build HTML table
    header_cols = ["Chỉ số"] + list(BORO_KEYS.keys())
    hdr_html = "".join(
        f'<th style="padding:.5rem .7rem;background:#1e293b;color:{"#a5b4fc" if b!="Chỉ số" else "#94a3b8"};'
        f'font-size:.72rem;font-weight:700;text-align:{"left" if b=="Chỉ số" else "center"};'
        f'border-right:1px solid #334155;white-space:nowrap">{b}</th>'
        for b in header_cols
    )

    rows_html = ""
    for i, (label, key, unit, best_is_high) in enumerate(ALL_INDICES):
        raw_vals = {b: bdata.get(jk, {}).get(key) for b, jk in BORO_KEYS.items()}
        bg_row = "#ffffff" if i % 2 == 0 else "#f8fafc"
        row_td = f'<td style="padding:.45rem .7rem;font-size:.72rem;color:#334155;border-right:1px solid #e2e8f0;background:{bg_row}">{label}</td>'
        for b in BORO_KEYS:
            v = raw_vals[b]
            cell_bg = _color_cell(v, list(raw_vals.values()), best_is_high) if v is not None else bg_row
            try:    display = _fmt(float(v), unit)
            except: display = "—"
            row_td += (
                f'<td style="padding:.45rem .7rem;font-size:.73rem;font-weight:600;color:#1e293b;'
                f'text-align:center;background:{cell_bg};border-right:1px solid #e2e8f0">{display}</td>'
            )
        rows_html += f"<tr>{row_td}</tr>"

    table_html = f"""
    <div style="overflow-x:auto;border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 2px 8px rgba(0,0,0,.06)">
    <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif">
      <thead><tr>{hdr_html}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>
    <div style="display:flex;gap:1rem;margin-top:.6rem;flex-wrap:wrap">
      <span style="font-size:.65rem;color:#64748b">🟢 Tốt nhất &nbsp; 🟡 Trung bình &nbsp; 🟠 Dưới TB &nbsp; 🔴 Kém nhất</span>
      <span style="font-size:.65rem;color:#94a3b8">Nguồn: NYPD 2025 · RWJF 2024 · Census ACS 2023 · OSM 2025</span>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

 # PAGE 2: TƯ VẤN ĐỊNH CƯ & ĐẦU TƯ
# ══════════════════════════════════════════════════════
elif page == "💡 Tư vấn Định cư & Đầu tư":
    st.markdown("# 💡 Tư vấn Định cư & Đầu tư Bất động sản")
    st.markdown("Phân tích nâng cao kết hợp **Chất lượng sống (Livability)** và **Giá trị giao dịch** giúp khách hàng chọn quận phù hợp nhất để định cư lâu dài hoặc đầu tư sinh lời.")

    # Investment score cards
    ranked = sorted(INVEST_SCORE.items(), key=lambda x: x[1], reverse=True)
    cols = st.columns(5)
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    for i, (boro, iscore) in enumerate(ranked):
        lscore = LSCORE[boro]
        med_p  = df[df["borough_name"]==boro]["sale_price"].median()/1e3
        with cols[i]:
            cols[i].markdown(f"""<div class="kpi-card" style="border-color:{COLORS[boro]}55;text-align:center">
                <p style="font-size:2rem;margin:0">{medals[i]}</p>
                <p class="label" style="color:{COLORS[boro]};margin:.3rem 0">{boro}</p>
                <p class="val" style="color:{COLORS[boro]}">{iscore:.0f}</p>
                <p class="sub">Chỉ số Đầu tư</p>
                <p class="sub">🏠 ${med_p:.0f}K trung vị</p>
                <p class="sub">⭐ Sống tốt {lscore:.0f}/100</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-title">⚖️ So sánh Mức sống (Livability) vs Giá nhà</div>', unsafe_allow_html=True)
        scatter_data = pd.DataFrame({
            "Borough":   BOROUGHS,
            "Livability": [LSCORE[b] for b in BOROUGHS],
            "Med Price": [df[df["borough_name"]==b]["sale_price"].median()/1e3 for b in BOROUGHS],
            "Invest":    [INVEST_SCORE[b] for b in BOROUGHS],
            "Volume":    [df[df["borough_name"]==b].shape[0] for b in BOROUGHS],
        })
        fig = go.Figure()
        for _, row in scatter_data.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["Med Price"]], y=[row["Livability"]],
                mode="markers+text",
                marker=dict(size=row["Volume"]/80, color=COLORS[row["Borough"]],
                            opacity=0.85, line=dict(color="white",width=1.5)),
                text=[row["Borough"]], textposition="top center",
                textfont=dict(color=COLORS[row["Borough"]],size=12,family="Inter"),
                name=row["Borough"],
                hovertemplate=f"<b>{row['Borough']}</b><br>Giá: ${row['Med Price']:.0f}K<br>Chất lượng sống: {row['Livability']:.0f}/100<extra></extra>"
            ))
        # Tứ phân góc
        fig.add_shape(type="line", x0=900,x1=900,y0=40,y1=80,
                      line=dict(color="#cbd5e1",dash="dash",width=1))
        fig.add_shape(type="line", x0=400,x1=1400,y0=60,y1=60,
                      line=dict(color="#cbd5e1",dash="dash",width=1))
        fig.add_annotation(x=650,y=72, text="🌟 Đáng sống & Giá tốt (Queens/Brooklyn)", font=dict(color="#059669",size=10))
        fig.add_annotation(x=1200,y=72, text="💎 Đáng sống & Đắt đỏ (Manhattan)", font=dict(color="#d97706",size=10))
        fig.add_annotation(x=650,y=52, text="⚠️ Giá rẻ & Tiện ích thấp (Bronx)", font=dict(color="#dc2626",size=10))
        fig_layout(fig,
            xaxis=dict(title="Giá nhà trung vị (nghìn $)", gridcolor="#e2e8f0", tickprefix="$", ticksuffix="K"),
            yaxis=dict(title="Chất lượng sống (Livability)", gridcolor="#e2e8f0"),
            height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">📊 Chi tiết cơ cấu điểm số từng Quận</div>', unsafe_allow_html=True)

        boro_sel = st.selectbox("Chọn quận muốn phân tích:", BOROUGHS, key="inv_boro")
        bd = bdata.get(BORO_JSON[boro_sel], {})
        def pct(col, best, worst):
            v = bd.get(col, np.nan)
            if pd.isna(v): return 50
            return round(max(0,min(100,(float(v)-worst)/(best-worst)*100)),1)

        dims = {
            "🛡️ An toàn (Tội phạm thấp)": pct("Tỷ_lệ_tổng_tội_phạm_per_100k_dân", 0, 15000),
            "💚 Sức khỏe (Tuổi thọ cao)": pct("Tuổi_thọ_trung_bình_(năm)", 90, 60),
            "💰 Thu nhập dân cư":        pct("Thu_nhập_trung_vị", 150000, 0),
            "🎓 Trình độ học vấn":       pct("Tỷ_lệ_có_bằng_đại_học_%", 100, 0),
            "🌿 Không khí sạch":         pct("Chất_lượng_không_khí_PM2.5_(µg/m³)", 0, 25),
            "🚇 Giao thông Metro":        pct("Số_ga_tàu_điện_ngầm_(OSM)", 300, 0),
            "🏠 Hợp lý túi tiền":         round((1 - df[df["borough_name"]==boro_sel]["sale_price"].median()/df["sale_price"].max())*100, 1),
        }
        fig2 = go.Figure(go.Bar(
            y=list(dims.keys())[::-1],
            x=list(dims.values())[::-1],
            orientation="h",
            marker=dict(
                color=list(dims.values())[::-1],
                colorscale=[[0,"#fecaca"],[0.5,"#fde68a"],[1,"#bbf7d0"]],
                cmin=0, cmax=100,
                line=dict(color="#e2e8f0",width=0.5),
            ),
            text=[f"{v:.0f}%" for v in list(dims.values())[::-1]],
            textposition="outside",
            textfont=dict(color="#334155",size=11),
        ))
        fig_layout(fig2, xaxis=dict(range=[0,120],gridcolor="#e2e8f0",showticklabels=False),
                   yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                   height=380, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Insight cards
    st.markdown('<div class="section-title">🔍 Gợi ý nhanh cho Khách hàng</div>', unsafe_allow_html=True)
    insights = [
        ("🏆","Queens — Lựa chọn Hợp túi tiền",
         f"Chất lượng sống {LSCORE['Queens']:.0f}/100 nhưng giá trung vị chỉ ${df[df['borough_name']=='Queens']['sale_price'].median()/1e3:.0f}K — tối ưu nhất cho gia đình trẻ định cư."),
        ("💎","Manhattan — Phân khúc Thượng lưu",
         f"Chất lượng sống cao vượt trội {LSCORE['Manhattan']:.0f}/100 nhưng giá đắt đỏ ${df[df['borough_name']=='Manhattan']['sale_price'].median()/1e3:.0f}K — phù hợp nhà đầu tư dài hạn phân khúc cao cấp."),
        ("📈","Bronx — Tiềm năng Đô thị hóa",
         f"Giá thấp nhất ${df[df['borough_name']=='Bronx']['sale_price'].median()/1e3:.0f}K, sở hữu 77 ga metro — tiềm năng sinh lời lớn khi các tiện ích công phát triển."),
        ("🛡️","Staten Island — Định cư Yên bình",
         f"Tỷ lệ tội phạm thấp nhất {bdata['Staten Island']['Tỷ_lệ_tổng_tội_phạm_per_100k_dân']:.0f}/100k — cực kỳ an toàn cho gia đình có con nhỏ, không gian yên tĩnh kiểu ngoại ô."),
    ]
    i_cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(insights):
            i_cols[i].markdown(f"""<div class="insight-box">
            <div class="icon">{icon}</div>
            <h4>{title}</h4>
            <p>{desc}</p>
        </div>""", unsafe_allow_html=True)

    # ── Hướng đi 2: Bộ đề xuất Quận phù hợp (Borough Recommender Wizard) ──
    st.markdown('<div class="section-title">🔮 Trình tư vấn Quận phù hợp (Định cư & Đầu tư)</div>', unsafe_allow_html=True)
    st.markdown("Hệ thống sẽ tự động phân tích 40+ chỉ số và đưa ra đề xuất quận phù hợp nhất cho nhu cầu của bạn:")

    purpose = st.radio("Mục đích mua bất động sản của bạn là gì?", 
                       ["🏠 Mua để ở (Định cư lâu dài)", "📈 Mua để đầu tư (Tối ưu lợi nhuận)"])

    if purpose == "🏠 Mua để ở (Định cư lâu dài)":
        st.info("💡 **Chế độ Mua để ở:** AI sẽ tự động điều chỉnh các trọng số ưu tiên cao cho An ninh (Tội phạm thấp), Trường học tốt và Công viên xanh để gia đình bạn định cư an lành.")
        def_safety, def_schools, def_transit, def_green, def_walk = 9, 8, 7, 7, 6
    else:
        st.info("💡 **Chế độ Mua để đầu tư:** AI sẽ ưu tiên các quận có tiềm năng tăng giá trị YoY, kết nối giao thông tốt (Metro), mật độ kinh tế sôi động (Starbucks, Siêu thị) để tối ưu lợi nhuận.")
        def_safety, def_schools, def_transit, def_green, def_walk = 6, 5, 8, 5, 7

    # Pre-calculate YoY Rates for Investment Mode
    yoy_rates = {}
    for b in BOROUGHS:
        df_b = df[df["borough_name"]==b]
        p25 = df_b[df_b["sale_year"]==2025]["sale_price"].median()
        p26 = df_b[df_b["sale_year"]==2026]["sale_price"].median()
        yoy_rates[b] = (p26 - p25) / p25 * 100 if p25 > 0 else 0.0

    def get_yoy_score(b_name):
        yoy = yoy_rates.get(b_name, 0.0)
        return max(0, min(100, (yoy - (-5)) / (15 - (-5)) * 100))

    with st.container():
        cw1, cw2 = st.columns([2, 3])
        with cw1:
            st.markdown("##### ⚙️ Lọc & Đặt trọng số ưu tiên")
            rec_budget = st.slider("Ngân sách mua nhà tối đa ($K):", 100, 2000, 800, 50)
            
            st.markdown("*(Bạn có thể tự tay tinh chỉnh các thanh trượt bên dưới nếu muốn)*")
            w_safety = st.slider("🛡️ Mức độ an toàn (Tội phạm thấp):", 1, 10, def_safety, key="sl_safety")
            w_schools = st.slider("🎓 Chất lượng trường học:", 1, 10, def_schools, key="sl_schools")
            w_transit = st.slider("🚇 Giao thông công cộng (Ga Metro):", 1, 10, def_transit, key="sl_transit")
            w_green = st.slider("🌿 Không gian xanh & Công viên:", 1, 10, def_green, key="sl_green")
            w_walk = st.slider("🚶 Mức độ thuận tiện đi bộ (Walk Score):", 1, 10, def_walk, key="sl_walk")
            
        with cw2:
            st.markdown("##### 🏆 Kết quả phân tích đối sánh quận")
            
            # Calculate match score for each borough
            match_scores = {}
            w_sum = w_safety + w_schools + w_transit + w_green + w_walk
            
            for b in BOROUGHS:
                bd = bdata.get(BORO_JSON[b], {})
                med_p = df[df["borough_name"]==b]["sale_price"].median()/1e3
                
                # Financial filter: if median price exceeds budget, penalize the score
                price_penalty = 1.0 if med_p <= rec_budget else max(0.1, 1.0 - (med_p - rec_budget)/rec_budget)
                
                # Attribute scores (0 to 100)
                def get_score(val, best, worst):
                    try: return max(0, min(100, (float(val)-worst)/(best-worst)*100))
                    except: return 50
                    
                s_safety = get_score(bd.get("Tỷ_lệ_tổng_tội_phạm_per_100k_dân", 5000), 0, 15000)
                s_schools = get_score(bd.get("Chất_lượng_trường_học_(thang_10)", 7), 10, 0)
                s_transit = get_score(bd.get("Số_ga_tàu_điện_ngầm_(OSM)", 100), 300, 0)
                s_green = get_score(bd.get("Số_công_viên", 400), 1100, 0)
                s_walk = get_score(bd.get("Điểm_thân_thiện_đi_bộ_(Walk_Score)", 70), 100, 0)
                
                if purpose == "📈 Mua để đầu tư (Tối ưu lợi nhuận)":
                    s_growth = get_yoy_score(b)
                    weighted_score = (s_safety*w_safety + s_schools*w_schools + s_transit*w_transit + s_green*w_green + s_walk*w_walk + s_growth*8) / (w_sum + 8)
                else:
                    weighted_score = (s_safety*w_safety + s_schools*w_schools + s_transit*w_transit + s_green*w_green + s_walk*w_walk) / w_sum
                
                final_score = round(weighted_score * price_penalty, 1)
                match_scores[b] = final_score
            
            # Rank boroughs
            ranked_boros = sorted(match_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Display ranked recommendations
            for rank, (boro, score) in enumerate(ranked_boros, 1):
                med_p = df[df["borough_name"]==boro]["sale_price"].median()/1e3
                status_color = COLORS[boro]
                
                if purpose == "🏠 Mua để ở (Định cư lâu dài)":
                    status_text = "Phù hợp sống lâu dài" if score >= 80 else ("Phù hợp sống trung bình" if score >= 60 else "Hạn chế tiện ích định cư")
                    extra_info = f"🌳 Mức sống: {LSCORE[boro]:.0f}/100"
                else:
                    status_text = "Tiềm năng đầu tư cao" if score >= 80 else ("Sinh lời trung bình" if score >= 60 else "Tiềm năng đầu tư thấp")
                    yoy_rate = yoy_rates.get(boro, 0.0)
                    extra_info = f"📈 Tăng trưởng YoY: {yoy_rate:+.1f}%"
                
                st.markdown(f"""
                <div style="background:#ffffff; border-left: 6px solid {status_color}; border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.6rem; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; font-size:1.05rem; color:#0f172a;">#{rank} {boro}</span>
                        <span style="background:{status_color}18; color:{status_color}; font-weight:800; font-size:1.1rem; padding:0.2rem 0.6rem; border-radius:6px;">{score:.0f}% Khớp</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:0.4rem; font-size:0.8rem; color:#64748b;">
                        <span>🏠 Giá trung vị: ${med_p:.0f}K</span>
                        <span>{extra_info}</span>
                        <span>🔍 Trạng thái: {status_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# PAGE 3: ĐỊNH GIÁ AI & TÀI CHÍNH
# ══════════════════════════════════════════════════════
elif page == "🔮 Định giá AI & Tài chính":
    st.markdown("# 🔮 Định giá BĐS bằng AI & Lập Kế hoạch Tài chính")
    st.markdown("Nhập thông tin căn nhà bạn muốn mua — mô hình AI XGBoost (học từ 42,017 căn hộ) sẽ định giá chính xác để bạn tránh bị mua hớ, đồng thời thiết lập kế hoạch trả góp ngân hàng.")

    with st.spinner("Đang khởi động bộ định giá AI (lần đầu tiên mất ~30 giây)..."):
        model, imputer, FEATS, r2_val, mae_val, imp_df = train_model(df)

    # Model badge
    c_badge = st.columns(4)
    for col, label, val in [
        (c_badge[0], "R² Score", f"{r2_val:.4f}"),
        (c_badge[1], "MAE", f"${mae_val:,.0f}"),
        (c_badge[2], "Training data", "42,017 GD"),
        (c_badge[3], "Nguồn socio", "40+ chỉ số"),
    ]:
        col.markdown(f"""<div class="kpi-card">
            <p class="label">{label}</p>
            <p class="val" style="font-size:1.3rem">{val}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    col_inp, col_out = st.columns([1,1])
    with col_inp:
        st.markdown('<div class="section-title">📋 Thông tin bất động sản</div>', unsafe_allow_html=True)
        inp_boro   = st.selectbox("Quận", BOROUGHS)
        inp_bcat   = st.selectbox("Loại công trình", sorted(df["building_category"].dropna().unique()))
        inp_btype  = st.selectbox("Loại tòa nhà", sorted(df["building_type"].dropna().unique()))
        inp_neigh  = st.selectbox("Khu vực (Neighborhood)", sorted(df[df["borough_name"]==inp_boro]["neighborhood"].dropna().unique()))
        c1i,c2i = st.columns(2)
        inp_sqft = c1i.number_input("Diện tích sàn (sqft)", 0, 50000, 1200, 100)
        inp_land = c2i.number_input("Diện tích đất (sqft)", 0, 100000, 2500, 500)
        c3i,c4i = st.columns(2)
        inp_age  = c3i.number_input("Tuổi công trình (năm)", 0, 200, 50)
        inp_units= c4i.number_input("Tổng số đơn vị", 1, 1000, 1)
        inp_year = st.slider("Năm bán dự kiến", 2025, 2027, 2026)
        predict_btn = st.button("🔮 Dự báo giá", use_container_width=True, type="primary")

    with col_out:
        st.markdown('<div class="section-title">📊 Kết quả dự báo</div>', unsafe_allow_html=True)
        if predict_btn:
            # Build feature row
            boro_json_key = BORO_JSON.get(inp_boro, inp_boro)
            bd = bdata.get(boro_json_key, {})

            # Encode
            neigh_med = df.groupby("neighborhood")["sale_price"].apply(lambda x: np.log1p(x.median()))
            bcat_med  = df.groupby("building_category")["sale_price"].apply(lambda x: np.log1p(x.median()))

            boro_enc  = sorted(df["borough_name"].unique()).index(inp_boro) if inp_boro in df["borough_name"].unique() else 0
            bcat_enc  = list(sorted(df["building_category"].dropna().unique())).index(inp_bcat) if inp_bcat in df["building_category"].dropna().unique() else 0
            btype_enc = list(sorted(df["building_type"].dropna().unique())).index(inp_btype) if inp_btype in df["building_type"].dropna().unique() else 0
            neigh_t   = neigh_med.get(inp_neigh, neigh_med.mean())
            bcat_t    = bcat_med.get(inp_bcat,   bcat_med.mean())

            boro_income_val = bd.get("Thu_nhập_trung_vị", 40000)
            if isinstance(boro_income_val, str):
                try: boro_income_val = float(re.sub(r'[^0-9.]','',boro_income_val))
                except: boro_income_val = 40000

            row_dict = {
                "gross_sqft": inp_sqft, "land_sqft": inp_land,
                "total_units": inp_units, "residential_units": inp_units,
                "commercial_units": 0, "building_age_calc": inp_age,
                "pop_density": bd.get("Dân_số", 50000),
                "avg_income": boro_income_val,
                "gdp_local": 6.0, "dist_center": 5.0,
                "amenity_score": 7.0,
                "borough_name_enc": boro_enc, "building_category_enc": bcat_enc,
                "building_type_enc": btype_enc,
                "neighborhood_target": neigh_t, "bcat_target": bcat_t,
                "sale_year": inp_year, "sale_quarter": 2, "sale_month": 6,
                "is_residential": 1, "is_condo": int("CONDO" in inp_bcat),
                "has_sqft": int(inp_sqft > 0), "tax_class_sale": 2,
                "sqft_x_age": inp_sqft * inp_age,
                "income_x_amenity": boro_income_val * 7.0,
                # Socioeconomic
                "crime_rate":      float(bd.get("Tỷ_lệ_tổng_tội_phạm_per_100k_dân", 5000)),
                "life_expectancy": float(bd.get("Tuổi_thọ_trung_bình_(năm)", 80)),
                "pm25":            float(bd.get("Chất_lượng_không_khí_PM2.5_(µg/m³)", 8)),
                "bachelor_pct":    float(bd.get("Tỷ_lệ_có_bằng_đại_học_%", 40)),
                "poverty_child":   float(bd.get("Tỷ_lệ_nghèo_trẻ_em_%", 20)),
                "gini":            float(bd.get("Chỉ_số_Gini", 0.5)),
                "subway_count":    float(bd.get("Số_ga_tàu_điện_ngầm_(OSM)", 100)),
                "commute_min":     float(bd.get("Thời_gian_di_chuyển_TB_(phút)", 35)),
                "boro_income":     boro_income_val,
                "school_rating":   float(bd.get("Chất_lượng_trường_học_(thang_10)", 7.0)),
                "walk_score":      float(bd.get("Điểm_thân_thiện_đi_bộ_(Walk_Score)", 70.0)),
                "property_tax":    float(bd.get("Thuế_bất_động_sản_TB_%", 0.9)),
                "mcdonalds_count": float(bd.get("Số_cửa_hàng_McDonalds", 0.0)),
                "starbucks_count": float(bd.get("Số_cửa_hàng_Starbucks", 0.0)),
                "parks_count":     float(bd.get("Số_công_viên", 0.0)),
                "supermarkets_count": float(bd.get("Số_siêu_thị", 0.0)),
                "hospitals_count":  float(bd.get("Số_bệnh_viện_phòng_khám", 0.0)),
                "ev_charging_count": float(bd.get("Số_trạm_sạc_xe_điện", 0.0)),
            }
            X_pred = pd.DataFrame([[row_dict.get(f, 0) for f in FEATS]], columns=FEATS)
            X_pred_imp = imputer.transform(X_pred)
            log_pred = model.predict(X_pred_imp)[0]
            predicted = np.expm1(log_pred)

            # Confidence range ±15%
            lo, hi = predicted*0.85, predicted*1.15

            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{COLORS[inp_boro]}18,{COLORS[inp_boro]}10);
                border:2px solid {COLORS[inp_boro]};border-radius:18px;
                padding:2rem;text-align:center;margin-bottom:1rem;box-shadow:0 4px 16px {COLORS[inp_boro]}22">
                <p style="color:{COLORS[inp_boro]};font-size:.8rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.1em;margin:0">Giá dự báo</p>
                <p style="color:#0f172a;font-size:3rem;font-weight:900;margin:.3rem 0">
                    ${predicted:,.0f}</p>
                <p style="color:{COLORS[inp_boro]};font-size:.9rem;margin:0">
                    Khoảng tin cậy: ${lo:,.0f} — ${hi:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

            # So sánh vs median của quận
            boro_med = df[df["borough_name"]==inp_boro]["sale_price"].median()
            diff_pct = (predicted - boro_med)/boro_med*100
            arrow = "▲" if diff_pct >= 0 else "▼"
            cls   = "delta-up" if diff_pct >= 0 else "delta-down"
            st.markdown(f"""<div class="kpi-card">
                <p class="label">So với trung vị {inp_boro}</p>
                <p class="val" style="font-size:1.2rem">${boro_med:,.0f}</p>
                <p class="{cls}">{arrow} {abs(diff_pct):.1f}% {'cao hơn' if diff_pct>=0 else 'thấp hơn'}</p>
            </div>""", unsafe_allow_html=True)

            if inp_sqft > 0:
                st.markdown(f"""<div class="kpi-card">
                    <p class="label">Price per sqft</p>
                    <p class="val" style="font-size:1.2rem">${predicted/inp_sqft:,.0f}/sqft</p>
                    <p class="sub">TB {inp_boro}: ${df[df['borough_name']==inp_boro]['price_per_sqft_calc'].dropna().mean():,.0f}/sqft</p>
                </div>""", unsafe_allow_html=True)

            # ── Hướng đi 2: Bộ tính toán vay mua nhà (Mortgage Calculator) ──
            st.markdown("##### 💸 Tính toán tài chính mua nhà (Mortgage)")
            
            # Interactive Mortgage Inputs
            c_calc1, c_calc2 = st.columns(2)
            with c_calc1:
                down_pct = st.slider("Tiền trả trước (% Down Payment):", 10, 50, 20, 5, key="down_pct_predict")
                int_rate = st.slider("Lãi suất năm (% Interest Rate):", 3.0, 9.0, 6.5, 0.1, key="int_rate_predict")
            with c_calc2:
                loan_term = st.selectbox("Kỳ hạn vay (năm):", [15, 30], index=1, key="loan_term_predict")
                
            # Calculations
            down_payment = predicted * (down_pct / 100)
            loan_amount = predicted - down_payment
            
            # Monthly Interest Rate
            r_monthly = (int_rate / 100) / 12
            n_months = loan_term * 12
            
            # Monthly payment formula: P * (r*(1+r)^n) / ((1+r)^n - 1)
            if r_monthly > 0:
                monthly_p = loan_amount * (r_monthly * (1 + r_monthly)**n_months) / ((1 + r_monthly)**n_months - 1)
            else:
                monthly_p = loan_amount / n_months
                
            total_interest = (monthly_p * n_months) - loan_amount
            min_income = monthly_p * 12 / 0.35 # Assuming housing is max 35% of income
            
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:1.2rem; box-shadow:0 1px 4px rgba(0,0,0,.05);">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                    <span style="color:#64748b; font-size:0.8rem;">💵 Tiền trả trước ({down_pct}%):</span>
                    <span style="font-weight:700; color:#0f172a;">${down_payment:,.0f}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                    <span style="color:#64748b; font-size:0.8rem;">🏢 Số tiền cần vay ngân hàng:</span>
                    <span style="font-weight:700; color:#0f172a;">${loan_amount:,.0f}</span>
                </div>
                <hr style="margin:0.5rem 0; border-color:#e2e8f0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                    <span style="color:#64748b; font-weight:600; font-size:0.85rem;">💳 Trả góp hàng tháng (Gốc + Lãi):</span>
                    <span style="font-weight:800; color:#4f46e5; font-size:1.1rem;">${monthly_p:,.0f}/tháng</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                    <span style="color:#64748b; font-size:0.8rem;">📈 Tổng lãi phải trả:</span>
                    <span style="font-weight:700; color:#dc2626;">${total_interest:,.0f}</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#64748b; font-size:0.8rem;">💼 Thu nhập năm tối thiểu yêu cầu:</span>
                    <span style="font-weight:700; color:#16a34a;">${min_income:,.0f}/năm</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("👈 Điền thông tin bên trái và nhấn **Dự báo giá**")

# ══════════════════════════════════════════════════════
# PAGE 4: ĐÁNH GIÁ CHẤT LƯỢNG SỐNG
# ══════════════════════════════════════════════════════
elif page == "🏙️ Đánh giá Chất lượng Sống":
    st.markdown("# 🏙️ Đánh giá Chất lượng Sống & Tiện ích")
    st.markdown("So sánh trực diện các quận về hạ tầng y tế, giáo dục, không khí, công viên và an ninh để chọn nơi định cư tốt nhất cho gia đình.")

    # Radar chart
    st.markdown('<div class="section-title">🕸️ Radar — Đa chiều</div>', unsafe_allow_html=True)
    sel_boro_radar = st.multiselect("Chọn quận:", BOROUGHS, default=BOROUGHS, key="radar_sel")

    def abs_score(col, best, worst, bd):
        v = bd.get(col, np.nan)
        try: v = float(v)
        except: return 50
        return round(max(0,min(100,(v-worst)/(best-worst)*100)),1)

    categories = ["An toàn","Sức khỏe","Kinh tế","Giáo dục","Môi trường","Nhà ở","Kết nối"]
    fig = go.Figure()
    for b in sel_boro_radar:
        bd = bdata.get(BORO_JSON[b],{})
        med_p = df[df["borough_name"]==b]["sale_price"].median()
        vals = [
            abs_score("Tỷ_lệ_tổng_tội_phạm_per_100k_dân",0,15000,bd),
            abs_score("Tuổi_thọ_trung_bình_(năm)",90,60,bd),
            abs_score("Thu_nhập_trung_vị",150000,0,bd),
            abs_score("Tỷ_lệ_có_bằng_đại_học_%",100,0,bd),
            abs_score("Chất_lượng_không_khí_PM2.5_(µg/m³)",0,25,bd),
            round(max(0,min(100,(1-med_p/df["sale_price"].max())*100)),1),  # affordability
            abs_score("Số_ga_tàu_điện_ngầm_(OSM)",300,0,bd),
        ]
        fig.add_trace(go.Scatterpolar(
            r=vals+[vals[0]], theta=categories+[categories[0]],
            fill="toself", fillcolor=hex_rgba(COLORS[b],.18),
            line=dict(color=COLORS[b],width=2.5),
            marker=dict(size=7,color=COLORS[b],line=dict(color="white",width=1.5)),
            name=f"{b} ({LSCORE[b]:.0f}đ)",
        ))
    fig.update_layout(
        polar=dict(bgcolor="#f8f9fc",
            radialaxis=dict(visible=True,range=[0,100],
                gridcolor="#e2e8f0",tickcolor="#94a3b8",
                tickfont=dict(color="#64748b",size=9),linecolor="#e2e8f0"),
            angularaxis=dict(gridcolor="#e2e8f0",linecolor="#e2e8f0",
                tickfont=dict(color="#1e293b",size=12))),
        paper_bgcolor="#ffffff",
        font=dict(color="#334155",family="Inter"),
        legend=dict(bgcolor="#ffffff",bordercolor="#e2e8f0",borderwidth=1),
        height=480, margin=dict(t=20,b=20,l=20,r=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Bảng so sánh đầy đủ
    st.markdown('<div class="section-title">📋 Bảng tổng hợp đầy đủ</div>', unsafe_allow_html=True)
    table_rows = []
    for b in BOROUGHS:
        bd = bdata.get(BORO_JSON[b],{})
        re_sub = df[df["borough_name"]==b]
        table_rows.append({
            "Quận": b,
            "Invest Score": f"{INVEST_SCORE[b]:.0f}",
            "Livability": f"{LSCORE[b]:.0f}/100",
            "Giá trung vị": f"${re_sub['sale_price'].median()/1e3:.0f}K",
            "$/sqft TB": f"${re_sub['price_per_sqft_calc'].dropna().mean():,.0f}" if re_sub['price_per_sqft_calc'].dropna().shape[0]>0 else "N/A",
            "Trường học (10)": f"{bd.get('Chất_lượng_trường_học_(thang_10)','N/A')}/10",
            "Walk Score": f"{bd.get('Điểm_thân_thiện_đi_bộ_(Walk_Score)','N/A')}/100",
            "Thuế BĐS": f"{bd.get('Thuế_bất_động_sản_TB_%', 0.9):.2f}%",
            "Crime/100k": f"{bd.get('Tỷ_lệ_tổng_tội_phạm_per_100k_dân','N/A')}",
            "Tuổi thọ": f"{bd.get('Tuổi_thọ_trung_bình_(năm)','N/A')} năm",
            "Bằng ĐH": f"{bd.get('Tỷ_lệ_có_bằng_đại_học_%','N/A')}%",
            "Ga Metro": f"{bd.get('Số_ga_tàu_điện_ngầm_(OSM)','N/A')}",
            "Commute": f"{bd.get('Thời_gian_di_chuyển_TB_(phút)','N/A')} phút",
            "PM2.5": f"{bd.get('Chất_lượng_không_khí_PM2.5_(µg/m³)','N/A')} µg",
            "Giao dịch 25-26": f"{re_sub.shape[0]:,}",
        })
    st.dataframe(pd.DataFrame(table_rows).set_index("Quận"),
                 use_container_width=True, height=220)

    # ── Hướng đi 1: Động lực Kinh tế Đô thị (Urban Economics) ──
    st.markdown('<div class="section-title">📊 1. Phân tích Động lực Kinh tế Đô thị & Gentrification</div>', unsafe_allow_html=True)
    st.markdown("Giả thuyết: *Sự phát triển của chuỗi dịch vụ cao cấp (Starbucks), trạm sạc EV và tiện ích công cộng (Công viên) tỷ lệ thuận với giá trị nhà ở và thu nhập khu vực.*")

    scatter_data = pd.DataFrame({
        "Borough": BOROUGHS,
        "Starbucks": [float(bdata.get(BORO_JSON[b], {}).get("Số_cửa_hàng_Starbucks", 0)) for b in BOROUGHS],
        "EV_Chargers": [float(bdata.get(BORO_JSON[b], {}).get("Số_trạm_sạc_xe_điện", 0)) for b in BOROUGHS],
        "MedPrice": [float(df[df["borough_name"]==b]["sale_price"].median()/1e3) for b in BOROUGHS],
    })

    c1, c2 = st.columns(2)
    with c1:
        # Starbucks vs Median Price
        fig_sb = go.Figure()
        # Scatter points
        fig_sb.add_trace(go.Scatter(
            x=scatter_data["Starbucks"], y=scatter_data["MedPrice"],
            mode="markers+text", text=scatter_data["Borough"],
            textposition="top center",
            marker=dict(size=14, color="#4f46e5", line=dict(width=1.5, color="white")),
            name="Quận",
            hovertemplate="<b>%{text}</b><br>Starbucks: %{x}<br>Giá trung vị: $%{y:.0f}K<extra></extra>"
        ))
        # Manual OLS Line Fit
        x = scatter_data["Starbucks"].values
        y = scatter_data["MedPrice"].values
        slope, intercept = np.polyfit(x, y, 1)
        x_line = np.linspace(x.min()*0.8, x.max()*1.2, 100)
        y_line = slope * x_line + intercept
        fig_sb.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            line=dict(color="#818cf8", width=2, dash="dash"),
            name="Đường xu hướng (OLS)",
            hoverinfo="skip"
        ))
        fig_layout(fig_sb, title="Tương quan tiệm Starbucks vs Giá nhà trung vị",
                   xaxis=dict(title="Số lượng cửa hàng Starbucks", gridcolor="#e2e8f0"),
                   yaxis=dict(title="Giá trung vị (nghìn $)", gridcolor="#e2e8f0", tickprefix="$", ticksuffix="K"),
                   showlegend=False, height=330)
        st.plotly_chart(fig_sb, use_container_width=True)

    with c2:
        # EV Chargers vs Median Price
        fig_ev = go.Figure()
        fig_ev.add_trace(go.Scatter(
            x=scatter_data["EV_Chargers"], y=scatter_data["MedPrice"],
            mode="markers+text", text=scatter_data["Borough"],
            textposition="top center",
            marker=dict(size=14, color="#0891b2", line=dict(width=1.5, color="white")),
            name="Quận",
            hovertemplate="<b>%{text}</b><br>Trạm sạc EV: %{x}<br>Giá trung vị: $%{y:.0f}K<extra></extra>"
        ))
        # Manual OLS Line Fit
        x_ev = scatter_data["EV_Chargers"].values
        slope_ev, intercept_ev = np.polyfit(x_ev, y, 1)
        x_line_ev = np.linspace(x_ev.min()*0.8, x_ev.max()*1.2, 100)
        y_line_ev = slope_ev * x_line_ev + intercept_ev
        fig_ev.add_trace(go.Scatter(
            x=x_line_ev, y=y_line_ev, mode="lines",
            line=dict(color="#67e8f9", width=2, dash="dash"),
            name="Đường xu hướng (OLS)",
            hoverinfo="skip"
        ))
        fig_layout(fig_ev, title="Tương quan Trạm sạc EV vs Giá nhà trung vị",
                   xaxis=dict(title="Số lượng trạm sạc xe điện", gridcolor="#e2e8f0"),
                   yaxis=dict(title="Giá trung vị (nghìn $)", gridcolor="#e2e8f0", tickprefix="$", ticksuffix="K"),
                   showlegend=False, height=330)
        st.plotly_chart(fig_ev, use_container_width=True)

# ══════════════════════════════════════════════════════
# PAGE 5: CƠ HỘI & TĂNG TRƯỞNG
# ══════════════════════════════════════════════════════
elif page == "📈 Cơ hội & Tăng trưởng":
    st.markdown("# 📈 Cơ hội Thị trường & Xu hướng BĐS")

    # Monthly price trend
    st.markdown('<div class="section-title">📅 Giá trung vị theo tháng</div>', unsafe_allow_html=True)
    dff["ym"] = dff["sale_date_parsed"].dt.to_period("M").astype(str)
    monthly = dff.groupby(["ym","borough_name"])["sale_price"].median().reset_index()
    monthly = monthly[monthly["borough_name"].isin(sel_boros)]

    fig = go.Figure()
    for b in sel_boros:
        sub = monthly[monthly["borough_name"]==b].sort_values("ym")
        fig.add_trace(go.Scatter(
            x=sub["ym"], y=sub["sale_price"]/1e3,
            mode="lines+markers", name=b,
            line=dict(color=COLORS[b],width=2.5),
            marker=dict(size=6,color=COLORS[b]),
            hovertemplate=f"<b>{b}</b><br>%{{x}}<br>${{%{{y:.0f}}}}K<extra></extra>"
        ))
    fig_layout(fig, yaxis=dict(gridcolor="#e2e8f0",tickprefix="$",ticksuffix="K"),
               xaxis=dict(gridcolor="#e2e8f0"),
               height=360, legend=dict(bgcolor="#ffffff",bordercolor="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-title">📦 Volume giao dịch theo tháng</div>', unsafe_allow_html=True)
        vol_m = dff.groupby(["ym","borough_name"]).size().reset_index(name="count")
        vol_m = vol_m[vol_m["borough_name"].isin(sel_boros)]
        fig2 = go.Figure()
        for b in sel_boros:
            sub = vol_m[vol_m["borough_name"]==b].sort_values("ym")
            fig2.add_trace(go.Bar(x=sub["ym"], y=sub["count"], name=b,
                                  marker_color=COLORS[b], opacity=0.8))
        fig_layout(fig2, barmode="stack", height=320,
                   yaxis=dict(gridcolor="#e2e8f0"),
                   xaxis=dict(gridcolor="#e2e8f0"),
                   legend=dict(bgcolor="#ffffff",bordercolor="#e2e8f0"))
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">🏗️ Xu hướng theo loại công trình</div>', unsafe_allow_html=True)
        top_cats = dff["building_category"].value_counts().head(5).index
        cat_trend = dff[dff["building_category"].isin(top_cats)]\
            .groupby(["sale_year","building_category"])["sale_price"].median().reset_index()
        fig3 = go.Figure()
        colors_cat = px.colors.qualitative.Safe
        for i, cat in enumerate(top_cats):
            sub = cat_trend[cat_trend["building_category"]==cat]
            fig3.add_trace(go.Bar(
                x=sub["sale_year"].astype(str), y=sub["sale_price"]/1e3,
                name=cat, marker_color=colors_cat[i%len(colors_cat)], opacity=.85
            ))
        fig_layout(fig3, barmode="group", height=320,
                   yaxis=dict(gridcolor="#e2e8f0",tickprefix="$",ticksuffix="K"),
                   xaxis=dict(gridcolor="#e2e8f0"),
                   legend=dict(bgcolor="#ffffff",bordercolor="#e2e8f0",font=dict(size=9)))
        st.plotly_chart(fig3, use_container_width=True)

    # ── Hướng đi 4: Giám sát thị trường & Dự báo xu hướng (Market Monitoring & BI) ──
    st.markdown('<div class="section-title">📊 4. Giám sát & Dự báo xu hướng thị trường tương lai</div>', unsafe_allow_html=True)
    st.markdown("Phân tích động thái thời gian, tốc độ tăng trưởng hàng năm (YoY) và dự báo xu hướng các quý tiếp theo:")

    # 4.1. YoY Price Appreciation by Borough (Bar chart)
    st.markdown("##### 📈 Tăng trưởng giá trị tài sản trung vị theo năm (YoY Price Appreciation)")
    yoy_rows = []
    for b in sel_boros:
        df_b = dff[dff["borough_name"]==b]
        p25 = df_b[df_b["sale_year"]==2025]["sale_price"].median()
        p26 = df_b[df_b["sale_year"]==2026]["sale_price"].median()
        if p25 > 0 and p26 > 0:
            yoy_val = (p26 - p25) / p25 * 100
            yoy_rows.append({"Quận": b, "YoY Tăng trưởng (%)": round(yoy_val, 2), "Giá 2025": p25, "Giá 2026": p26})
            
    if yoy_rows:
        yoy_df = pd.DataFrame(yoy_rows)
        fig_yoy = go.Figure(go.Bar(
            x=yoy_df["Quận"], y=yoy_df["YoY Tăng trưởng (%)"],
            marker_color=[COLORS[b] for b in yoy_df["Quận"]],
            text=[f"{v:+.1f}%" for v in yoy_df["YoY Tăng trưởng (%)"]],
            textposition="outside",
            textfont=dict(color="#334155", size=11)
        ))
        fig_layout(fig_yoy, yaxis=dict(title="Mức tăng trưởng YoY (%)", gridcolor="#e2e8f0"),
                   xaxis=dict(gridcolor="rgba(0,0,0,0)"),
                   height=280, showlegend=False)
        st.plotly_chart(fig_yoy, use_container_width=True)
    else:
        st.info("Không đủ dữ liệu giao dịch để so sánh YoY cho các quận đã chọn.")

    # 4.2. Future Projections (OLS line chart and table)
    st.markdown("##### 🔮 Dự báo chỉ số giá BĐS trung vị qua các Quý (Q2/2026 - Q1/2027)")
    st.markdown("*(Mô hình dự báo xu hướng tuyến tính dựa trên dữ liệu giao dịch thực tế 4 quý gần nhất)*")
    
    col_proj_chart, col_proj_table = st.columns([3, 2])
    
    # Calculate historical and projected values
    proj_rows = []
    fig_proj = go.Figure()
    
    # Quarters mappings
    q_labels_hist = ["Q2/2025", "Q3/2025", "Q4/2025", "Q1/2026"]
    q_labels_proj = ["Q2/2026", "Q3/2026", "Q4/2026", "Q1/2027"]
    
    for b in sel_boros:
        df_b = dff[dff["borough_name"]==b]
        
        # Calculate median price for each historical quarter
        hist_prices = []
        for yr, qtr in [(2025, 2), (2025, 3), (2025, 4), (2026, 1)]:
            q_price = df_b[(df_b["sale_year"]==yr) & (df_b["sale_quarter"]==qtr)]["sale_price"].median()
            hist_prices.append(q_price if not np.isnan(q_price) and q_price > 0 else None)
            
        # If we have at least 3 valid quarters, we can project
        valid_indices = [i for i, p in enumerate(hist_prices) if p is not None]
        if len(valid_indices) >= 3:
            # fill missing if any
            clean_x = np.array(valid_indices) + 1
            clean_y = np.array([hist_prices[i] for i in valid_indices])
            
            slope, intercept = np.polyfit(clean_x, clean_y, 1)
            
            # Predict for historical (to show trendline) and future
            x_all = np.arange(1, 9) # 1 to 8
            pred_all = slope * x_all + intercept
            
            # Historical actual line
            fig_proj.add_trace(go.Scatter(
                x=q_labels_hist, y=[p/1e3 if p is not None else None for p in hist_prices],
                mode="lines+markers", name=f"{b} (Thực tế)",
                line=dict(color=COLORS[b], width=3),
                marker=dict(size=6)
            ))
            
            # Projection line (dotted)
            fig_proj.add_trace(go.Scatter(
                x=[q_labels_hist[-1]] + q_labels_proj, 
                y=[hist_prices[-1]/1e3] + list(pred_all[4:]/1e3),
                mode="lines+markers", name=f"{b} (Dự báo)",
                line=dict(color=COLORS[b], width=2.5, dash="dot"),
                marker=dict(size=6, symbol="open-circle")
            ))
            
            # Add to table rows
            for idx, label in enumerate(q_labels_proj):
                proj_rows.append({
                    "Quận": b,
                    "Quý": label,
                    "Giá dự báo": f"${pred_all[4+idx]/1e3:.0f}K",
                    "Thay đổi Q/Q": f"{((pred_all[4+idx] - pred_all[3+idx]) / pred_all[3+idx] * 100):+.1f}%"
                })
        else:
            # fallback to actual historical plot only
            actual_prices = [p/1e3 if p is not None else None for p in hist_prices]
            if any(actual_prices):
                fig_proj.add_trace(go.Scatter(
                    x=q_labels_hist, y=actual_prices,
                    mode="lines+markers", name=f"{b} (Thực tế)",
                    line=dict(color=COLORS[b], width=3)
                ))
                
    with col_proj_chart:
        fig_layout(fig_proj, yaxis=dict(title="Giá nhà trung vị (nghìn $)", gridcolor="#e2e8f0", tickprefix="$", ticksuffix="K"),
                   xaxis=dict(gridcolor="#e2e8f0"),
                   height=380, legend=dict(bgcolor="#ffffff", bordercolor="#e2e8f0", borderwidth=1))
        st.plotly_chart(fig_proj, use_container_width=True)
        
    with col_proj_table:
        if proj_rows:
            proj_df = pd.DataFrame(proj_rows)
            st.dataframe(proj_df.set_index(["Quận", "Quý"]), use_container_width=True, height=330)
        else:
            st.warning("Không đủ dữ liệu để thực hiện dự báo xu hướng cho các quận này.")

# ══════════════════════════════════════════════════════
# PAGE 6: ML ANALYSIS
# ══════════════════════════════════════════════════════
elif page == "🤖 Phân tích ML":
    st.markdown("# 🤖 Phân tích Mô hình Học máy Chuyên sâu (AI/ML)")
    st.markdown("**Đánh giá độ tin cậy · Giải mã tiện ích ảnh hưởng đến giá trị bất động sản NYC**")

    with st.spinner("Đang khởi tạo mô hình AI (lần đầu tiên có thể mất ~30 giây)..."):
        model, imputer, FEATS, r2_val, mae_val, imp_df = train_model(df)

    # ── Sơ đồ luồng hoạt động AI ────────────────────────
    st.markdown("""
    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.2rem; margin-bottom: 1.2rem; box-shadow: 0 1px 6px rgba(0,0,0,.06);">
        <h4 style="margin-top:0; color:#1e293b; font-size:1.05rem; font-weight:700; display:flex; align-items:center;">💡 Luồng hoạt động của Trí tuệ Nhân tạo (AI) trong dự án</h4>
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-top: 0.8rem;">
            <div style="flex: 1; min-width: 180px; background: #f1f5f9; border-radius: 10px; padding: 0.8rem; text-align: center; border: 1px solid #e2e8f0; margin: 0.4rem;">
                <span style="font-size: 1.6rem;">🏠</span>
                <h5 style="margin: 0.3rem 0 0.1rem 0; color:#0f172a; font-weight:700; font-size:0.85rem;">1. Dữ liệu BĐS</h5>
                <p style="margin: 0; font-size: 0.72rem; color:#64748b;">42,017 giao dịch thực tế (Diện tích, vị trí, tuổi nhà...)</p>
            </div>
            <div style="font-size: 1.2rem; color: #4f46e5; margin: 0.4rem; font-weight:bold;">➡️</div>
            <div style="flex: 1; min-width: 180px; background: #eff6ff; border-radius: 10px; padding: 0.8rem; text-align: center; border: 1px solid #bfdbfe; margin: 0.4rem;">
                <span style="font-size: 1.6rem;">📊</span>
                <h5 style="margin: 0.3rem 0 0.1rem 0; color:#1e40af; font-weight:700; font-size:0.85rem;">2. 40+ Tiện ích</h5>
                <p style="margin: 0; font-size: 0.72rem; color:#60a5fa;">Mới tích hợp: Starbucks, trạm sạc EV, công viên, siêu thị...</p>
            </div>
            <div style="font-size: 1.2rem; color: #4f46e5; margin: 0.4rem; font-weight:bold;">➡️</div>
            <div style="flex: 1; min-width: 180px; background: #faf5ff; border-radius: 10px; padding: 0.8rem; text-align: center; border: 1px solid #e9d5ff; margin: 0.4rem;">
                <span style="font-size: 1.6rem;">🧠</span>
                <h5 style="margin: 0.3rem 0 0.1rem 0; color:#6b21a8; font-weight:700; font-size:0.85rem;">3. Học máy (XGBoost)</h5>
                <p style="margin: 0; font-size: 0.72rem; color:#a855f7;">Học hỏi quy luật liên hệ phức tạp giữa tiện ích và giá cả</p>
            </div>
            <div style="font-size: 1.2rem; color: #4f46e5; margin: 0.4rem; font-weight:bold;">➡️</div>
            <div style="flex: 1; min-width: 180px; background: #f0fdf4; border-radius: 10px; padding: 0.8rem; text-align: center; border: 1px solid #bbf7d0; margin: 0.4rem;">
                <span style="font-size: 1.6rem;">🎯</span>
                <h5 style="margin: 0.3rem 0 0.1rem 0; color:#166534; font-weight:700; font-size:0.85rem;">4. Giải thích (SHAP)</h5>
                <p style="margin: 0; font-size: 0.72rem; color:#22c55e;">Dự báo giá cực nhanh & Bóc tách % tác động của tiện ích</p>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    for col, label, val, sub in [
        (c1, "Độ nhạy bén AI (R²)",    f"{r2_val:.4f}", f"Giải thích {r2_val*100:.1f}% thị trường"),
        (c2, "Độ lệch giá TB (MAE)",   f"${mae_val:,.0f}", "Mức chênh lệch khi đoán mẫu"),
        (c3, "Thuật toán chính",       "XGBoost", "500 cây quyết định, độ sâu = 7"),
        (c4, "Số chỉ số phân tích",    str(len(FEATS)), "Bao gồm dữ liệu tiện ích đô thị"),
    ]:
        col.markdown(f"""<div class="kpi-card">
            <p class="label">{label}</p>
            <p class="val" style="font-size:1.3rem">{val}</p>
            <p class="sub">{sub}</p>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── 6 New Utilities Section (40+ Indicators style) ──
    st.markdown('<div class="section-title">💡 PHÂN TÍCH DỄ HIỂU: TÁC ĐỘNG THỰC TẾ CỦA 6 TIỆN ÍCH MỚI CRAWL</div>', unsafe_allow_html=True)
    st.markdown("Dưới đây là kết quả **bóc tách từ mô hình học máy (SHAP)** thể hiện mức độ tác động của 6 tiện ích mới được crawl lên giá trị bất động sản. Mỗi con số thể hiện tỷ lệ % thay đổi giá trị căn hộ trung bình khi khu vực có thêm **1 đơn vị tiện ích** tương ứng:")

    # Calculate SHAP values dynamically (1000 samples for high speed)
    with st.spinner("Đang bóc tách phân tích SHAP (mất ~2 giây)..."):
        import shap
        # Prepare X data for SHAP
        dft_shap = df.copy()
        for col_enc in ["borough_name","building_category","building_type","neighborhood"]:
            if col_enc in dft_shap.columns:
                le_sh = LabelEncoder()
                dft_shap[col_enc+"_enc"] = le_sh.fit_transform(dft_shap[col_enc].fillna("UNKNOWN").astype(str))
        
        dft_shap["log_price"] = np.log1p(dft_shap["sale_price"])
        neigh_med = dft_shap.groupby("neighborhood")["log_price"].median()
        dft_shap["neighborhood_target"] = dft_shap["neighborhood"].map(neigh_med)
        bcat_med  = dft_shap.groupby("building_category")["log_price"].median()
        dft_shap["bcat_target"] = dft_shap["building_category"].map(bcat_med)
        dft_shap["sale_quarter"] = pd.to_datetime(dft_shap["sale_date_clean"], errors="coerce").dt.quarter
        dft_shap["is_condo"]  = dft_shap["building_category"].str.contains("CONDO", na=False).astype(int)
        dft_shap["sqft_x_age"] = dft_shap["gross_sqft"].fillna(0) * dft_shap["building_age_calc"].fillna(70)
        dft_shap["income_x_amenity"] = dft_shap["avg_income"] * dft_shap["amenity_score"]
        
        X_all_shap = dft_shap[[f for f in FEATS if f in dft_shap.columns]].copy()
        for f in FEATS:
            if f not in X_all_shap: X_all_shap[f] = 0
        X_all_shap = X_all_shap[FEATS]
        X_all_imp = imputer.transform(X_all_shap)
        
        # sample
        rng_idx = np.random.choice(len(X_all_imp), min(1000, len(X_all_imp)), replace=False)
        X_sample = X_all_imp[rng_idx]
        X_sample_df = pd.DataFrame(X_sample, columns=FEATS)
        
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_sample_df)

        def compute_marginal_impact(f_name):
            try:
                feat_idx = FEATS.index(f_name)
                x_vals = X_sample_df[f_name].values
                s_vals = shap_vals[:, feat_idx]
                if np.std(x_vals) == 0:
                    return 0.0
                slope, intercept = np.polyfit(x_vals, s_vals, 1)
                pct_change = (np.exp(slope) - 1) * 100
                return pct_change
            except:
                return 0.0

        impacts = {
            "starbucks_count": compute_marginal_impact("starbucks_count"),
            "ev_charging_count": compute_marginal_impact("ev_charging_count"),
            "parks_count": compute_marginal_impact("parks_count"),
            "supermarkets_count": compute_marginal_impact("supermarkets_count"),
            "hospitals_count": compute_marginal_impact("hospitals_count"),
            "mcdonalds_count": compute_marginal_impact("mcdonalds_count")
        }

    # Render 6 cards
    c_card1, c_card2, c_card3 = st.columns(3)

    # Card 1: Starbucks
    val_sb = impacts["starbucks_count"]
    c_card1.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #4f46e5; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">☕</span>
            <span style="background:#4f46e518; color:#4f46e5; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_sb:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Cửa hàng Starbucks</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Hiệu ứng Gentrification:</b> Starbucks đại diện cho tệp khách hàng thu nhập cao và năng động. Sự hiện diện của thương hiệu này là tín hiệu cho sự hiện đại hóa và nâng tầm giá trị BĐS khu vực.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 2: EV Chargers
    val_ev = impacts["ev_charging_count"]
    c_card2.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #0891b2; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">⚡</span>
            <span style="background:#0891b218; color:#0891b2; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_ev:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Trạm sạc xe điện (EV)</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Chỉ số Sống Xanh & Quy hoạch:</b> Liên hệ chặt chẽ với hạ tầng công nghệ và nhóm cư dân sở hữu ô tô điện thông minh. Càng nhiều trạm sạc EV càng định vị phân khúc BĐS cao cấp hơn.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 3: Parks
    val_pk = impacts["parks_count"]
    c_card3.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #16a34a; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">🌳</span>
            <span style="background:#16a34a18; color:#16a34a; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_pk:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Không gian xanh (Công viên)</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Chỉ số Môi trường Sức khỏe:</b> Công viên mang lại giá trị vô giá cho việc nghỉ ngơi và tập luyện. Khu vực nhiều cây xanh luôn có sức hút định cư cao và giữ giá căn hộ bền vững.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("") # spacing

    c_card4, c_card5, c_card6 = st.columns(3)

    # Card 4: Supermarkets
    val_sm = impacts["supermarkets_count"]
    c_card4.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #d97706; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">🛒</span>
            <span style="background:#d9770618; color:#d97706; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_sm:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Siêu thị sinh hoạt</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Tiện ích Đời sống thiết yếu:</b> Phục vụ trực tiếp cho nhu cầu ăn uống, mua sắm hàng ngày của hộ gia đình. Đây là hạ tầng nền tảng giúp nâng cao tính thanh khoản cho căn nhà.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 5: Hospitals
    val_hp = impacts["hospitals_count"]
    c_card5.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #e11d48; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">🏥</span>
            <span style="background:#e11d4818; color:#e11d48; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_hp:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Bệnh viện & Phòng khám</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Hạ tầng An sinh Xã hội:</b> Đáp ứng nhu cầu bảo vệ sức khỏe và cứu hộ khẩn cấp. Mặc dù tác động định giá vừa phải, đây là tiêu chí an sinh cực kỳ quan trọng khi định cư dài hạn.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 6: McDonalds
    val_mc = impacts["mcdonalds_count"]
    c_card6.markdown(f"""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-left:6px solid #475569; border-radius:12px; padding:1rem; min-height:175px; box-shadow: 0 1px 4px rgba(0,0,0,.05);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:1.8rem;">🍔</span>
            <span style="background:#47556918; color:#475569; font-weight:800; font-size:1.1rem; padding:0.2rem 0.5rem; border-radius:6px;">{val_mc:+.2f}%</span>
        </div>
        <h5 style="margin:0.4rem 0 0.15rem; color:#0f172a; font-weight:700; font-size:0.85rem;">Cửa hàng McDonald's</h5>
        <p style="margin:0; font-size:0.72rem; color:#64748b; line-height:1.35;">
            <b>Chỉ số Mật độ Phổ thông:</b> McDonalds hướng tới ăn uống nhanh bình dân. Mật độ cửa hàng quá cao thường tương quan với khu vực đông đúc, ồn ào và thiếu không gian tĩnh lặng sang trọng.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.write("") # spacing

    # Plotly horizontal bar chart for the 6 new utilities impact %
    fig_imp = go.Figure(go.Bar(
        y=["Cửa hàng Starbucks", "Trạm sạc xe điện", "Công viên xanh", "Siêu thị", "Bệnh viện", "McDonald's"][::-1],
        x=[val_sb, val_ev, val_pk, val_sm, val_hp, val_mc][::-1],
        orientation="h",
        marker=dict(
            color=[val_sb, val_ev, val_pk, val_sm, val_hp, val_mc][::-1],
            colorscale=[[0,"#dc2626"],[0.5,"#cbd5e1"],[1,"#16a34a"]],
            cmin=-1.5, cmax=3.0,
            showscale=False
        ),
        text=[f"{v:+.2f}%" for v in [val_sb, val_ev, val_pk, val_sm, val_hp, val_mc][::-1]],
        textposition="outside",
        textfont=dict(color="#334155", size=10, family="Inter")
    ))
    fig_imp.update_layout(
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8f9fc",
        font=dict(color="#334155", family="Inter"),
        margin=dict(t=15,b=15,l=10,r=10),
        xaxis=dict(title="Tác động lên giá nhà trung bình (%)", gridcolor="#e2e8f0"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        height=240,
        showlegend=False
    )
    st.plotly_chart(fig_imp, use_container_width=True)

    st.markdown("---")

    c1, c2 = st.columns([3,2])
    with c1:
        st.markdown('<div class="section-title">🎯 Feature Importance</div>', unsafe_allow_html=True)
        
        with st.expander("❓ Giải thích dễ hiểu về Độ quan trọng của các Chỉ số (Feature Importance)"):
            st.markdown("""
            * **Khái niệm đơn giản:** Cho biết AI ưu tiên sử dụng đặc điểm nào nhiều nhất để định giá nhà. Cột càng dài nghĩa là đặc điểm đó quyết định càng nhiều đến giá trị căn hộ.
            * **Ý nghĩa thực tế:** Giúp chúng ta kiểm tra xem AI học có đúng thực tế không. Ví dụ: diện tích xây dựng (gross_sqft) và khu vực (neighborhood) đứng hàng đầu là hoàn toàn phù hợp với thực tiễn mua bán nhà.
            """)

        top15 = imp_df.head(15)
        fig = go.Figure(go.Bar(
            y=top15["Feature"][::-1],
            x=top15["Importance"][::-1],
            orientation="h",
            marker=dict(
                color=top15["Importance"][::-1],
                colorscale=[[0,"#eff6ff"],[0.5,"#6366f1"],[1,"#0891b2"]],
            ),
            text=[f"{v:.3f}" for v in top15["Importance"][::-1]],
            textposition="outside",
            textfont=dict(color="#334155",size=10),
        ))
        fig_layout(fig, xaxis=dict(gridcolor="#e2e8f0",showticklabels=False),
                   yaxis=dict(gridcolor="rgba(0,0,0,0)"),
                   height=420, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">📊 Timeline cải thiện</div>', unsafe_allow_html=True)
        
        with st.expander("❓ Giải thích dễ hiểu về Hành trình cải thiện mô hình"):
            st.markdown("""
            * **Khái niệm đơn giản:** Nhật ký theo dõi điểm số R² (độ nhạy bén) và MAE (sai lệch giá) của AI qua từng giai đoạn nâng cấp dữ liệu.
            * **Ý nghĩa thực tế:** Minh chứng khoa học cho thấy khi tích hợp thêm **40+ chỉ số kinh tế - xã hội mới crawl**, độ lệch sai số của AI giảm mạnh và khả năng giải thích giá nhà tăng lên đáng kể.
            """)

        timeline = pd.DataFrame([
            {"Phiên bản":"v1 — Data gốc","R2":0.479,"MAE":393795,"Note":"RF baseline"},
            {"Phiên bản":"v2 — Data sạch","R2":0.517,"MAE":282570,"Note":"+ clean data"},
            {"Phiên bản":"v3 — Tuning","R2":0.522,"MAE":281643,"Note":"+ XGB + Stacking"},
            {"Phiên bản":"v4 — + Socio","R2":r2_val,"MAE":mae_val,"Note":"+ 12 socio features"},
        ])
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=timeline["Phiên bản"], y=timeline["R2"],
            mode="lines+markers+text",
            line=dict(color="#6366f1",width=3),
            marker=dict(size=12,color="#6366f1",line=dict(color="white",width=2)),
            text=[f"R²={v:.3f}" for v in timeline["R2"]],
            textposition="top center",
            textfont=dict(color="#334155",size=10),
            name="R²",
        ))
        fig_layout(fig2, yaxis=dict(range=[0.4,0.7],gridcolor="#e2e8f0",title="R²"),
                   xaxis=dict(gridcolor="#e2e8f0"),
                   height=230, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = go.Figure(go.Bar(
            x=timeline["Phiên bản"], y=timeline["MAE"]/1e3,
            marker_color=["#fecaca","#fde68a","#bbf7d0","#6366f1"],
            text=[f"${v/1e3:.0f}K" for v in timeline["MAE"]],
            textposition="outside",
            textfont=dict(color="#334155",size=10),
        ))
        fig_layout(fig3, yaxis=dict(gridcolor="#e2e8f0",tickprefix="$",ticksuffix="K"),
                   xaxis=dict(gridcolor="#e2e8f0"),
                   height=230, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # Residual analysis
    st.markdown('<div class="section-title">🔬 Phân tích sai số theo quận</div>', unsafe_allow_html=True)
    
    with st.expander("❓ Giải thích dễ hiểu về Biểu đồ Sai số theo từng Quận"):
        st.markdown("""
        * **Khái niệm đơn giản:** Thống kê xem trung bình AI đoán lệch bao nhiêu phần trăm (%) tại mỗi quận của NYC.
        * **Ý nghĩa thực tế:** Giúp người mua biết được mức độ tin cậy của AI ở từng khu vực. Thanh sai số (đường dọc) càng ngắn thể hiện mức độ biến động giá ở quận đó càng ổn định, AI đoán càng vững.
        """)

    # Quick prediction on test set per borough
    dft = df.copy()
    dft["log_price"] = np.log1p(dft["sale_price"])
    for col2 in ["borough_name","building_category","building_type","neighborhood"]:
        le2 = LabelEncoder()
        dft[col2+"_enc"] = le2.fit_transform(dft[col2].fillna("UNKNOWN").astype(str))
    dft["neighborhood_target"] = dft.groupby("neighborhood")["log_price"].transform("median")
    dft["bcat_target"] = dft.groupby("building_category")["log_price"].transform("median")
    dft["sale_quarter"] = pd.to_datetime(dft["sale_date_clean"],errors="coerce").dt.quarter
    dft["is_condo"] = dft["building_category"].str.contains("CONDO",na=False).astype(int)
    dft["sqft_x_age"] = dft["gross_sqft"].fillna(0)*dft["building_age_calc"].fillna(70)
    dft["income_x_amenity"] = dft["avg_income"]*dft["amenity_score"]

    Xall  = dft[[f for f in FEATS if f in dft.columns]].copy()
    # add missing
    for f in FEATS:
        if f not in Xall: Xall[f] = 0
    Xall  = Xall[FEATS]
    Xiall = imputer.transform(Xall)
    pred_all = np.expm1(model.predict(Xiall))
    dft["pred"] = pred_all
    dft["error_pct"] = (dft["pred"]-dft["sale_price"])/dft["sale_price"]*100

    err_boro = dft.groupby("borough_name")["error_pct"].agg(["mean","std"]).reset_index()
    fig4 = go.Figure()
    for _, row in err_boro.iterrows():
        b = row["borough_name"]
        if b not in COLORS: continue
        fig4.add_trace(go.Bar(
            x=[b], y=[row["mean"]],
            error_y=dict(type="data", array=[row["std"]], visible=True, color="#8b9fd4"),
            marker_color=COLORS[b], name=b,
            text=[f"{row['mean']:.1f}%"],
            textposition="outside",
            textfont=dict(color="#334155"),
        ))
    fig4.add_hline(y=0, line_color="#cbd5e1", line_dash="dash")
    fig_layout(fig4, yaxis=dict(gridcolor="#e2e8f0",title="Sai số TB (%)"),
               height=280, showlegend=False,
               xaxis=dict(gridcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig4, use_container_width=True)
