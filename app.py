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

# --- 1. CUSTOM CSS (STRANGER THINGS STYLE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Libre+Baskerville:wght@700&display=swap');

    .stApp { background-color: #f1f5f9; }
    .main .block-container {
        background-color: #ffffff;
        padding: 2rem 3rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    
    .giant-title { 
        font-family: 'Libre Baskerville', serif;
        font-size: 55px; 
        font-weight: 900; 
        color: #C11B17; 
        margin: 0; 
        line-height: 1.1; 
        letter-spacing: -1px;
        text-transform: uppercase;
        text-shadow: 3px 3px 5px rgba(0,0,0,0.3);
    }
    
    .giant-sub { 
        font-family: 'Bebas Neue', cursive; 
        font-size: 28px; 
        color: #1f4e79; 
        margin: 0; 
        font-weight: 400; 
        letter-spacing: 4px;
    }
    
    .header-container {
        display: flex;
        align-items: center;
        gap: 30px;
        margin-bottom: 25px;
        padding: 10px;
        border-bottom: 3px solid #C11B17;
    }
    
    .logo-img { height: 120px; width: auto; mix-blend-mode: multiply; }

    .metric-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        border-bottom: 5px solid #C11B17;
    }

    .chart-box {
        background-color: #ffffff;
        border: 2px solid #e2e8f0;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }

    .stButton>button { 
        width: 100%; background-color: #C11B17; color: white; border-radius: 8px; font-weight: bold; height: 3.5em; border: none;
    }
    .stButton>button:hover { background-color: #931613; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    data = conn.read(ttl=0) 
    if data is None or data.empty:
        cols = ['Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'Supplier', 'Status', 'Update Status']
        return pd.DataFrame(columns=cols)
    
    cols_to_fix = ['Material', 'PO No', 'Resv']
    for col in cols_to_fix:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str)
            data[col] = data[col].replace('0', '')
    
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce')
    
    str_cols = ['Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status', 'Update Status']
    for col in str_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
    return data

try:
    df_master = load_data()
except Exception as e:
    st.error(f"Koneksi Gagal: {e}")
    st.stop()

# --- 3. HEADER ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

logo_base64 = get_base64_image("NHM.jpg")

st.markdown(f"""
    <div class="header-container">
        <img src="data:image/jpeg;base64,{logo_base64}" class="logo-img">
        <div>
            <h1 class="giant-title">Purchase Order Monitoring</h1>
            <h2 class="giant-sub">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. FILTER ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c1, c2, c3 = st.columns(3)
    def get_opts(col):
        return sorted([x for x in df_master[col].unique() if x and str(x) != "nan"]) if col in df_master.columns else []
    
    f_fleet = c1.multiselect("Filter Fleet", options=get_opts("Fleet"))
    f_unit = c2.multiselect("Filter Unit", options=get_opts("Unit no"))
    f_status = c3.multiselect("Filter Status", options=get_opts("Status"))

df_display = df_master.copy()
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_display = df_display[df_display["Fleet"].isin(f_fleet)]
if f_unit: df_display = df_display[df_display["Unit no"].isin(f_unit)]
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]

# --- 5. SUMMARY CARDS ---
total = len(df_display)
outstanding = len(df_display[df_display['Status'] == 'Outstanding'])
complete = len(df_display[df_display['Status'] == 'Complete'])

m1, m2, m3 = st.columns(3)
m1.markdown(f"""<div class="metric-card"><p style="color:#64748b; font-size:12px; font-weight:bold; margin:0;">TOTAL ITEMS</p><p style="font-size:32px; font-weight:800; color:#1f4e79; margin:0;">{total}</p></div>""", unsafe_allow_html=True)
m2.markdown(f"""<div class="metric-card" style="border-bottom-color: #ef4444;"><p style="color:#64748b; font-size:12px; font-weight:bold; margin:0;">OUTSTANDING</p><p style="font-size:32px; font-weight:800; color:#ef4444; margin:0;">{outstanding}</p></div>""", unsafe_allow_html=True)
m3.markdown(f"""<div class="metric-card" style="border-bottom-color: #22c55e;"><p style="color:#64748b; font-size:12px; font-weight:bold; margin:0;">COMPLETE</p><p style="font-size:32px; font-weight:800; color:#22c55e; margin:0;">{complete}</p></div>""", unsafe_allow_html=True)

# --- 6. GRAFIK (GLOSSY REVISION) ---
if not df_display.empty:
    st.write("") 
    g1, g2, g3 = st.columns(3)

    # 1. PIE CHART PIC (Warna-warni Glossy)
    with g1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        pic_counts = df_display['PIC'].value_counts()
        fig = go.Figure(data=[go.Pie(
            labels=pic_counts.index, 
            values=pic_counts.values, 
            hole=.5,
            marker=dict(colors=px.colors.qualitative.Bold, line=dict(color='#FFFFFF', width=2))
        )])
        fig.update_traces(textinfo='label+percent', pull=[0.05]*len(pic_counts))
        fig.update_layout(title_text="Workload by PIC", title_x=0.5, height=300, showlegend=False, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 2. PIE CHART STATUS (Hijau & Pink Glossy)
    with g2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st_counts = df_display['Status'].value_counts()
        # Mendefinisikan warna spesifik: Hijau Glossy untuk Complete, Pink untuk Outstanding
        color_map = {'Complete': '#2ecc71', 'Outstanding': '#ff69b4', 'On Process': '#3b82f6'}
        colors = [color_map.get(s, '#94a3b8') for s in st_counts.index]
        
        fig = go.Figure(data=[go.Pie(
            labels=st_counts.index, 
            values=st_counts.values, 
            hole=.5,
            marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2))
        )])
        fig.update_traces(textinfo='label+percent', pull=[0.1 if s == 'Outstanding' else 0 for s in st_counts.index])
        fig.update_layout(title_text="Status Distribution", title_x=0.5, height=300, showlegend=False, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 3. BAR CHART UNITS (Biru Glossy Berbeda-beda)
    with g3:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        unit_data = df_display['Unit no'].value_counts().nlargest(5).reset_index()
        
        # Menggunakan palet biru yang berbeda untuk setiap batang
        blue_glossy_palette = ['#1E90FF', '#00BFFF', '#0000FF', '#4169E1', '#4682B4']
        
        fig = go.Figure(go.Bar(
            x=unit_data['Unit no'], 
            y=unit_data['count'],
            marker=dict(
                color=blue_glossy_palette[:len(unit_data)], 
                line=dict(color='#FFFFFF', width=2)
            ),
            text=unit_data['count'], 
            textposition='auto',
        ))
        
        fig.update_layout(
            title_text="Top 5 Units", 
            title_x=0.5, 
            height=300, 
            margin=dict(t=40,b=10,l=10,r=10), 
            yaxis_visible=False,
            bargap=0.3,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 7. DATA EDITOR ---
st.markdown("### 📋 Database Monitoring")
df_to_edit = df_display if (f_fleet or f_unit or f_status or search_query) else df_master
df_to_edit.index = range(1, len(df_to_edit) + 1)

edited_data = st.data_editor(
    df_to_edit, use_container_width=True, hide_index=False, num_rows="dynamic", height=450,
    key="editor_stranger_vFinal_Glossy",
    column_config={
        "Fleet": st.column_config.TextColumn("Fleet", width=120, pinned=True),
        "Unit no": st.column_config.TextColumn("Unit", width=100, pinned=True),
        "Status": st.column_config.SelectboxColumn("Status", options=["Complete", "Outstanding", "On Process"], width=130),
        "Update Status": st.column_config.TextColumn("Update Status", width=400)
    }
)

# --- 8. ACTIONS ---
c_save, c_exp, _ = st.columns([1.5, 1.5, 4])
if c_save.button("💾 SIMPAN & SYNC CLOUD"):
    try:
        final_df = pd.concat([df_master[~df_master.index.isin(df_display.index)], edited_data.reset_index(drop=True)]).reset_index(drop=True)
        if 'Doc Date' in final_df.columns:
            final_df['Doc Date'] = pd.to_datetime(final_df['Doc Date']).dt.strftime('%Y-%m-%d').replace('NaT', '')
        conn.update(data=final_df)
        st.cache_data.clear()
        st.success("Sinkronisasi Berhasil!")
        st.rerun()
    except Exception as e: st.error(f"Gagal: {e}")

excel_data = io.BytesIO()
with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
    df_display.to_excel(writer, index=False)
c_exp.download_button("📊 EXPORT EXCEL", data=excel_data.getvalue(), file_name='NHM_Database.xlsx')

st.markdown("<p style='text-align: center; color: #94a3b8; margin-top: 40px; font-size: 14px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</p>", unsafe_allow_html=True)