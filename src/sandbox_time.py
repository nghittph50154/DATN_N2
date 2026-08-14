# -*- coding: utf-8 -*-
"""
sandbox_time.py  —  Phòng thí nghiệm: Kể chuyện Nghịch lý Thời gian (Index 0%)
Chạy: python -m streamlit run src/sandbox_time.py --server.port 8503
"""
import os, warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import matplotlib.dates as mdates
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

st.set_page_config(page_title="🧪 Sandbox – Storytelling Paradox", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None, "Không tìm thấy DATABASE_URL"
    try:
        from sqlalchemy import create_engine
        engine = create_engine(db_url, connect_args={"options": "-c statement_timeout=0"})
        chunks = pd.read_sql_query("""
            SELECT b.borough_name, n.neighborhood_name,
                   f.sale_price, f.sale_year, f.sale_month
            FROM fact_sales f
            JOIN dim_location       l ON f.location_id    = l.location_id
            JOIN dim_neighborhood   n ON l.neighborhood_id = n.neighborhood_id
            JOIN dim_borough        b ON n.borough_id      = b.borough_id
        """, engine, chunksize=10000)
        df = pd.concat(chunks, ignore_index=True)
        engine.dispose()
    except Exception as e:
        return None, str(e)

    df["sale_price"] = pd.to_numeric(df["sale_price"], errors="coerce")
    df["sale_year"]  = pd.to_numeric(df["sale_year"],  errors="coerce").astype("Int64")
    df["sale_month"] = pd.to_numeric(df["sale_month"], errors="coerce").astype("Int64")
    df = df[df["sale_price"] > 10000].dropna(subset=["sale_price", "sale_year", "sale_month"])
    df["ym_dt"] = pd.to_datetime(
        df["sale_year"].astype(str) + "-" + df["sale_month"].astype(str).str.zfill(2),
        format="%Y-%m")
    return df, None

with st.spinner("⏳ Đang tính toán dữ liệu đa tầng..."):
    df, err = load_data()

if err:
    st.error(f"Lỗi: {err}")
    st.stop()

st.markdown("""
<div style='background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:14px;
padding:20px 28px;color:#fff;margin-bottom:24px;
box-shadow:0 8px 32px rgba(99,102,241,0.3)'>
<div style='font-size:22px;font-weight:700'>
    📉 Phân tích Lợi suất Đầu tư: Từ Vĩ mô đến Vi mô
</div>
<div style='font-size:14px;opacity:0.9;margin-top:6px;line-height:1.6'>
    Theo dõi tỷ suất sinh lời theo thời gian thực để tìm ra khu vực bùng nổ, các hố đen rủi ro, và những bến đỗ an toàn nhất.
</div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# 1. TOÀN CẢNH NYC (GIÁ TRUNG VỊ + INDEX)
# ════════════════════════════════════════════════════════════════
st.markdown("### 1️⃣ Toàn cảnh Thị trường New York")
st.markdown("<div style='font-size:14px;color:#4B5563;margin-bottom:10px'>Đường xu hướng (nét đứt) cho thấy sự ổn định đi ngang của toàn thị trường.</div>", unsafe_allow_html=True)

df_all = df.dropna(subset=['ym_dt']).copy()
mts_all = df_all.groupby('ym_dt')['sale_price'].median().reset_index().sort_values('ym_dt')
base_price_all = mts_all['sale_price'].iloc[0]
mts_all['growth_pct'] = (mts_all['sale_price'] - base_price_all) / base_price_all * 100

fig_all = go.Figure()
fig_all.add_trace(go.Scatter(
    x=mts_all['ym_dt'], y=mts_all['growth_pct'], mode='lines',
    name='Toàn NYC', line=dict(color='#2563EB', width=4),
    customdata=mts_all['sale_price'],
    hovertemplate='<b>Toàn NYC</b><br>%{x|%m/%Y}<br>Tăng trưởng: <b>%{y:+.1f}%</b><br>Giá thực tế: $%{customdata:,.0f}<extra></extra>'
))

if len(mts_all) >= 3:
    x_num = mdates.date2num(mts_all['ym_dt'])
    coef = np.polyfit(x_num, mts_all['growth_pct'].ffill().bfill().values, 1)
    trend = np.polyval(coef, x_num)
    fig_all.add_trace(go.Scatter(
        x=mts_all['ym_dt'], y=trend, mode='lines', showlegend=False,
        line=dict(color='#F59E0B', width=2.5, dash='dash'), hoverinfo='skip'))

fig_all.add_hline(y=0, line_color="#9CA3AF", line_width=1.5, line_dash="dash")
fig_all.update_layout(
    height=300, plot_bgcolor="white", paper_bgcolor="white", hovermode='x unified',
    xaxis=dict(showgrid=True, gridcolor="#F3F4F6", tickformat="%m/%Y"),
    yaxis=dict(ticksuffix='%', showgrid=True, gridcolor="#F3F4F6", title="Tỷ suất Sinh lời (%)", zeroline=False),
    margin=dict(t=20, b=20, l=10, r=10))
st.plotly_chart(fig_all, use_container_width=True)

st.divider()

# ════════════════════════════════════════════════════════════════
# 2. BẢNG BÓC TÁCH: SỰ PHÂN HÓA 5 QUẬN
# ════════════════════════════════════════════════════════════════
st.markdown("### 2️⃣ Phân hóa Tỷ suất: Cấp độ Quận (Borough)")

boro_stats = []
df_boro = df.groupby(["borough_name", "ym_dt"])["sale_price"].median().reset_index().sort_values("ym_dt")
for boro in sorted(df_boro['borough_name'].unique()):
    sub = df_boro[df_boro['borough_name']==boro]
    if len(sub) < 1: continue
    start_p = sub['sale_price'].iloc[0]
    end_p = sub['sale_price'].iloc[-1]
    pct = (end_p - start_p) / start_p * 100
    boro_stats.append({
        "Quận": boro,
        "Giá Bắt Đầu": start_p,
        "Giá Hiện Tại": end_p,
        "Lợi Suất (%)": pct
    })

df_table = pd.DataFrame(boro_stats).sort_values("Lợi Suất (%)", ascending=False)

def format_table(df_tbl):
    return df_tbl.style.format({
        "Giá Bắt Đầu": "${:,.0f}",
        "Giá Hiện Tại": "${:,.0f}",
        "Lợi Suất (%)": "{:+.1f}%"
    }).map(lambda x: f"color: {'#EF4444' if x > 0 else '#10B981' if x < 0 else 'black'}; font-weight: bold;" if isinstance(x, (int, float)) and x < 100 else "", subset=["Lợi Suất (%)"])

st.dataframe(format_table(df_table), use_container_width=True, hide_index=True)
st.markdown("<div style='font-size:13px;color:#6B7280;margin-top:-10px;margin-bottom:20px'><i>Nhận xét: Ở cấp độ vĩ mô, Bronx đang dẫn đầu thị trường trong khi Queens là quận duy nhất mang lại lợi suất âm.</i></div>", unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════════════════════
# 3. BẢNG BÓC TÁCH CẤP KHU VỰC: TOP & BOTTOM NYC
# ════════════════════════════════════════════════════════════════
st.markdown("### 3️⃣ Bảng Phong Thần: Cấp độ Khu vực (Neighborhood)")
st.markdown("<div style='font-size:14px;color:#4B5563;margin-bottom:15px'>Soi rọi toàn bộ các khu vực trên khắp 5 Quận để tìm ra các mỏ vàng và những hố đen cảnh báo.</div>", unsafe_allow_html=True)

neigh_stats = []
for boro in df["borough_name"].unique():
    b_df = df[df["borough_name"] == boro]
    for n in b_df["neighborhood_name"].unique():
        sub = b_df[b_df["neighborhood_name"] == n].groupby("ym_dt")["sale_price"].median().reset_index().sort_values("ym_dt")
        if len(sub) < 3 or len(b_df[b_df["neighborhood_name"]==n]) < 10: 
            continue
        start_p = sub["sale_price"].iloc[0]
        end_p = sub["sale_price"].iloc[-1]
        pct = (end_p - start_p) / start_p * 100
        neigh_stats.append({
            "Quận": boro, 
            "Khu Vực": n, 
            "Giá Bắt Đầu": start_p, 
            "Giá Hiện Tại": end_p, 
            "Lợi Suất (%)": pct
        })

df_neigh_all = pd.DataFrame(neigh_stats)
top_3 = df_neigh_all.sort_values("Lợi Suất (%)", ascending=False).head(3).reset_index(drop=True)
bot_3 = df_neigh_all.sort_values("Lợi Suất (%)", ascending=True).head(3).reset_index(drop=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("##### 🔥 TOP 3 TĂNG TRƯỞNG MẠNH NHẤT NYC")
    st.dataframe(format_table(top_3), use_container_width=True, hide_index=True)

with c2:
    st.markdown("##### ⚠️ TOP 3 SỤT GIẢM MẠNH NHẤT NYC")
    st.dataframe(format_table(bot_3), use_container_width=True, hide_index=True)

st.divider()

# HÀM VẼ BIỂU ĐỒ 1 KHU VỰC VS QUẬN (CÓ THÊM TRENDLINE CHO KHU VỰC)
def plot_single_neighborhood(boro_name, neigh_name, title, color_neigh):
    fig = go.Figure()
    
    # Vẽ đường trung bình Quận
    sub_b = df_boro[df_boro["borough_name"] == boro_name].copy()
    base_b = sub_b["sale_price"].iloc[0]
    sub_b['growth_pct'] = (sub_b['sale_price'] - base_b) / base_b * 100
    
    fig.add_trace(go.Scatter(
        x=sub_b['ym_dt'], y=sub_b['growth_pct'],
        mode='lines', name=f"Trung bình {boro_name}",
        line=dict(color='#9CA3AF', width=2, dash='dot'),
        customdata=sub_b['sale_price'],
        hovertemplate=f'<b>TB {boro_name}</b><br>%{{x|%m/%Y}}<br>Lợi suất: %{{y:+.1f}}%<extra></extra>'))
        
    # Vẽ đường khu vực
    df_neigh = df[(df["borough_name"] == boro_name) & (df["neighborhood_name"] == neigh_name)]
    sub_n = df_neigh.groupby("ym_dt")["sale_price"].median().reset_index().sort_values("ym_dt")
    if len(sub_n) > 0:
        base_n = sub_n["sale_price"].iloc[0]
        sub_n['growth_pct'] = (sub_n['sale_price'] - base_n) / base_n * 100
        
        fig.add_trace(go.Scatter(
            x=sub_n['ym_dt'], y=sub_n['growth_pct'],
            mode='lines', name=neigh_name,
            line=dict(color=color_neigh, width=4),
            customdata=sub_n['sale_price'],
            hovertemplate=f'<b>{neigh_name}</b><br>%{{x|%m/%Y}}<br>Lợi suất: <b>%{{y:+.1f}}%</b><br>Giá: $%{{customdata:,.0f}}<extra></extra>'))

        # Trendline cho khu vực
        if len(sub_n) >= 3:
            x_num = mdates.date2num(sub_n['ym_dt'])
            coef = np.polyfit(x_num, sub_n['growth_pct'].ffill().bfill().values, 1)
            trend = np.polyval(coef, x_num)
            fig.add_trace(go.Scatter(
                x=sub_n['ym_dt'], y=trend, mode='lines', showlegend=False,
                line=dict(color=color_neigh, width=1.5, dash='dash'), hoverinfo='skip'))

    fig.add_hline(y=0, line_color="#9CA3AF", line_width=1.5, line_dash="dash")
    fig.update_layout(
        height=320, plot_bgcolor="white", paper_bgcolor="white", hovermode='x unified',
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(showgrid=True, gridcolor="#F3F4F6", tickformat="%m/%Y"),
        yaxis=dict(ticksuffix='%', showgrid=True, gridcolor="#F3F4F6", title="", zeroline=False),
        legend=dict(orientation='h', y=1.1, x=0), margin=dict(t=50, b=20, l=10, r=10))
    
    final_pct = sub_n['growth_pct'].iloc[-1] if len(sub_n) > 0 else 0
    return fig, final_pct

# ════════════════════════════════════════════════════════════════
# 4. ZOOM VÀO BIỂU ĐỒ: NGHỊCH LÝ THỜI GIAN
# ════════════════════════════════════════════════════════════════
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 4️⃣ Kẻ dẫn đầu lại nằm ở Quận đội sổ")
    fig_queens, pct_queens = plot_single_neighborhood("Queens", "HOLLISWOOD", "🚀 Holliswood (Tăng mạnh nhất NYC)", "#EF4444")
    st.plotly_chart(fig_queens, use_container_width=True)
    st.markdown(f"""
    <div style='background:#FEF2F2;border-left:4px solid #EF4444;padding:12px;border-radius:6px;font-size:13px;color:#991B1B'>
    Queens là quận làm NĐT lỗ nặng nhất toàn thành phố. Nhưng nghịch lý thay, bên trong nó lại chứa khu vực <b>HOLLISWOOD</b> - mảnh đất màu mỡ nhất toàn NYC với lợi suất khủng khiếp <b>+{pct_queens:.1f}%</b>.
    </div>
    """, unsafe_allow_html=True)

with col_b:
    st.markdown("### 5️⃣ Hố đen tử thần nằm ở Quận dẫn đầu")
    fig_bronx, pct_bronx = plot_single_neighborhood("Bronx", "MOUNT HOPE/MOUNT EDEN", "⚠️ Mount Hope (Tệ thứ nhì NYC)", "#10B981")
    st.plotly_chart(fig_bronx, use_container_width=True)
    st.markdown(f"""
    <div style='background:#ECFDF5;border-left:4px solid #10B981;padding:12px;border-radius:6px;font-size:13px;color:#065F46'>
    Ngược lại, Bronx là "vương miện" đầu tư của cấp Quận. Nhưng nếu nhắm mắt mua bừa vào <b>MOUNT HOPE</b>, NĐT sẽ bốc hơi <b>{pct_bronx:.1f}%</b> tài sản dù thị trường chung của quận đang đi lên mạnh mẽ.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ════════════════════════════════════════════════════════════════
# 5. KHU VỰC ỔN ĐỊNH NHẤT (R2 CAO)
# ════════════════════════════════════════════════════════════════
col_c, col_d = st.columns(2)

with col_c:
    st.markdown("### 6️⃣ Xu hướng Tăng Ổn định nhất")
    fig_lic, pct_lic = plot_single_neighborhood("Queens", "LONG ISLAND CITY", "📈 Long Island City (Tăng đều đặn, Ít rủi ro)", "#F59E0B")
    st.plotly_chart(fig_lic, use_container_width=True)
    st.markdown(f"""
    <div style='background:#FFFBEB;border-left:4px solid #F59E0B;padding:12px;border-radius:6px;font-size:13px;color:#92400E'>
    Bỏ qua các cú sốc giật cục, <b>Long Island City</b> là bến đỗ an toàn nhất cho NĐT thích sự ổn định. Lợi suất tăng đều đặn bám sát đường xu hướng đạt <b>+{pct_lic:.1f}%</b>.
    </div>
    """, unsafe_allow_html=True)

with col_d:
    st.markdown("### 7️⃣ Xu hướng Giảm Ổn định nhất")
    fig_wa, pct_wa = plot_single_neighborhood("Manhattan", "WASHINGTON HEIGHTS LOWER", "📉 Washington Heights Lower (Trượt dốc đều đặn)", "#8B5CF6")
    st.plotly_chart(fig_wa, use_container_width=True)
    st.markdown(f"""
    <div style='background:#F5F3FF;border-left:4px solid #8B5CF6;padding:12px;border-radius:6px;font-size:13px;color:#5B21B6'>
    Khu vực này cho thấy sự đào thải từ từ của thị trường. Lợi suất giảm từ từ qua từng tháng, bám sát đường xu hướng đi xuống và chạm mốc <b>{pct_wa:.1f}%</b>. NĐT nên tránh xa các khu vực giảm ổn định kiểu này.
    </div>
    """, unsafe_allow_html=True)


st.markdown("""
<div style='margin-top:30px;padding-top:15px;border-top:1px dashed #D1D5DB;font-size:15px;color:#4B5563;font-style:italic;line-height:1.6'>
🎙️ <b>Kịch bản thuyết trình (Chốt sale):</b><br>
"Kính thưa Hội đồng, nghệ thuật phân tích dữ liệu bất động sản không nằm ở việc tìm ra quy luật, mà là tìm ra nghịch lý.<br><br>
Nhìn vào <b>Mục 2</b>, Bronx là quận sinh lời cao nhất, còn Queens là quận duy nhất thua lỗ. Lẽ thường, NĐT sẽ đổ xô vào Bronx và tẩy chay Queens.<br><br>
Tuy nhiên, hãy nhìn vào <b>Bảng Phong Thần (Mục 3)</b> và <b>Biểu đồ 4 & 5</b>. Đỉnh cao lợi suất +428% của toàn thành phố lại nằm lọt thỏm trong lòng Queens (Holliswood). Và ngược lại, hố đen bốc hơi -88% tài sản lại nằm trong lòng của quận dẫn đầu Bronx (Mount Hope).<br><br>
Nhưng nếu NĐT không thích sự biến động quá mạnh (rủi ro cao)? <b>Biểu đồ 6 & 7</b> sẽ chỉ ra những khu vực tăng trưởng ổn định nhất (Long Island City) và suy giảm từ từ (Washington Heights).<br><br>
Điều này khẳng định một triết lý sâu sắc: <b>Đừng bao giờ mua 'một Quận', hãy mua 'một Phường'</b>. Hệ thống phân tích này giúp NĐT gạt bỏ định kiến vĩ mô để tìm thấy mỏ vàng vi mô thực sự."
</div>
""", unsafe_allow_html=True)
