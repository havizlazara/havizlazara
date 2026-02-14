import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
import plotly.graph_objects as go
import base64

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- 1. SIDEBAR CUSTOMIZER ---
with st.sidebar:
    st.header("🎨 Theme Customizer")
    bg_color = st.color_picker("Pilih Warna Background Utama", "#f1f5f9")
    card_color = st.color_picker("Pilih Warna Card", "#ffffff")
    st.divider()
    st.info("Panel ini mengatur area di luar header.")

# --- 2. FUNGSI ENKODE GAMBAR KE BASE64 ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg_base64 = get_base64_image("BG2.jpg")
logo_base64 = get_base64_image("NHM.jpg")

# --- 3. CUSTOM CSS (RESPONSIVE MOBILE OPTIMIZED) ---
st.markdown(f"""
    <style>
    /* Mengatur kontainer utama agar fleksibel di mobile */
    .stApp {{ 
        background-color: {bg_color}; 
    }}
    
    .main .block-container {{
        background-color: {card_color}; 
        padding: 1rem; /* Padding lebih kecil untuk mobile */
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
    }}

    /* Judul Responsif */
    .giant-title {{ 
        font-family: 'Libre Baskerville', serif;
        font-size: clamp(24px, 8vw, 58px); /* Ukuran font fleksibel */
        font-weight: 900; 
        color: #ffffff !important; 
        line-height: 1.2; 
        background: rgba(31, 78, 121, 0.6); 
        padding: 10px 15px;
        border-radius: 10px;
        display: inline-block;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.5);
        width: 90%; /* Supaya tidak overflow di HP */
    }}
    
    .giant-sub {{ 
        font-family: 'Bebas Neue', cursive; 
        font-size: clamp(14px, 4vw, 30px);
        color: #ffffff !important; 
        margin-top: 10px;
        letter-spacing: 2px;
        background: rgba(31, 78, 121, 0.6); 
        padding: 5px 15px;
        border-radius: 8px;
        display: inline-block;
    }}

    .custom-header {{
        position: relative;
        width: 100%;
        padding: 40px 10px; /* Padding lebih kecil di mobile */
        border-radius: 15px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        background-image: url("data:image/jpeg;base64,{header_bg_base64}");
        background-size: cover;
        background-position: center;
    }}

    .custom-header::after {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(173, 216, 230, 0.4); 
        z-index: 1;
    }}

    .header-content {{ position: relative; z-index: 2; width: 100%; }}

    /* Penyesuaian Kartu Metrik untuk Mobile */
    .metric-card {{
        background: {card_color};
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        border-bottom: 5px solid #1f4e79;
        text-align: center;
    }}

    .title-box {{
        background: white; 
        padding: 8px; 
        border-radius: 5px; 
        border: 1px solid #e2e8f0; 
        text-align: center; 
        font-weight: bold; 
        color: #1f4e79;
        font-size: 14px;
    }}

    .chart-box {{
        background-color: {card_color};
        border: 1px solid #e2e8f0;
        border-radius: 15px;
        padding: 10px;
        margin-top: 5px;
    }}

    /* Sembunyikan elemen dekoratif yang terlalu lebar di mobile jika perlu */
    @media (max-width: 640px) {{
        .giant-title {{ font-size: 22px; }}
        .main .block-container {{ padding: 0.5rem; }}
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status'])
    cols_to_fix = ['Material', 'PO No', 'Resv']
    for col in cols_to_fix:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str).replace('0', '')
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    return data

df_master = load_data()

# --- 5. RENDER HEADER ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" style="height: 80px; width: auto; margin-bottom: 10px;">
            <br><h1 class="giant-title">PO Monitoring</h1><br>
            <h2 class="giant-sub">NHM SCM & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. FILTER (Otomatis menjadi tumpukan di HP) ---
search_query = st.text_input("🔎 SEARCH:", placeholder="Cari...")
c_dept, c_fleet, c_unit, c_stat = st.columns([1,1,1,1])

filtered = df_master.copy()
f_dept = c_dept.multiselect("Dept", options=sorted(df_master['Dept.'].unique()))
if f_dept: filtered = filtered[filtered['Dept.'].isin(f_dept)]

f_fleet = c_fleet.multiselect("Fleet", options=sorted(filtered['Fleet'].unique()))
if f_fleet: filtered = filtered[filtered['Fleet'].isin(f_fleet)]

f_unit = c_unit.multiselect("Unit", options=sorted(filtered['Unit no'].unique()))
if f_unit: filtered = filtered[filtered['Unit no'].isin(f_unit)]

f_status = c_stat.multiselect("Status", options=sorted(filtered['Status'].unique()))
if f_status: filtered = filtered[filtered['Status'].isin(f_status)]

if search_query:
    filtered = filtered[filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 7. METRICS & TITLES (Responsif) ---
m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f'<div class="metric-card"><b>TOTAL</b><br><h2>{len(filtered)}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">PIC</div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card" style="border-bottom-color: #ef4444;"><b>OUTSTANDING</b><br><h2>{len(filtered[filtered["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">STATUS</div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card" style="border-bottom-color: #22c55e;"><b>COMPLETE</b><br><h2>{len(filtered[filtered["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">TOP 5 UNITS</div>', unsafe_allow_html=True)

# --- 8. GRAFIK (Otomatis menyesuaikan lebar kolom) ---
g1, g2, g3 = st.columns(3)
with g1:
    pic_counts = filtered['PIC'].value_counts()
    fig1 = go.Figure(data=[go.Pie(labels=pic_counts.index, values=pic_counts.values, hole=.5)])
    fig1.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True)
with g2:
    st_counts = filtered['Status'].value_counts()
    fig2 = go.Figure(data=[go.Pie(labels=st_counts.index, values=st_counts.values, hole=.5)])
    fig2.update_layout(height=300, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)
with g3:
    unit_data = filtered['Unit no'].value_counts().nlargest(5).reset_index()
    fig3 = go.Figure(go.Bar(x=unit_data['Unit no'], y=unit_data['count']))
    fig3.update_layout(height=300, margin=dict(t=20,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig3, use_container_width=True)

# --- 9. DATA EDITOR ---
st.markdown("### 📋 Database")
st.data_editor(filtered, use_container_width=True)