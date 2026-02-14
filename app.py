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

# --- 3. CUSTOM CSS (WHITE HEADER FONT) ---
st.markdown(f"""
    <style>
    .stApp {{ 
        background-color: {bg_color}; 
    }}
    .main .block-container {{
        background-color: {card_color}; 
        padding: 2rem 3rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }}
    
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Libre+Baskerville:wght@700&display=swap');

    /* HEADER DENGAN BACKGROUND 100% OPACITY */
    .custom-header {{
        position: relative;
        width: 100%;
        padding: 60px 20px;
        border-radius: 15px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 30px;
        background-image: url("data:image/jpg;base64,{header_bg_base64}");
        background-size: cover;
        background-position: center;
        border: 2px solid #C11B17;
    }}

    /* Overlay gelap tipis agar teks putih lebih 'pop' */
    .custom-header::after {{
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.3); 
        z-index: 1;
    }}

    .header-content {{
        position: relative;
        z-index: 2;
    }}

    /* Perubahan warna font menjadi PUTIH */
    .giant-title {{ 
        font-family: 'Libre Baskerville', serif;
        font-size: 55px; 
        font-weight: 900; 
        color: #ffffff; 
        margin: 0; 
        line-height: 1.1; 
        letter-spacing: -1px;
        text-transform: uppercase;
        text-shadow: 3px 3px 10px rgba(0,0,0,0.7);
    }}
    
    .giant-sub {{ 
        font-family: 'Bebas Neue', cursive; 
        font-size: 28px; 
        color: #ffffff; 
        margin: 10px 0 0 0; 
        font-weight: 400; 
        letter-spacing: 4px;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.8);
    }}
    
    .logo-img-header {{ 
        height: 110px; 
        width: auto; 
        margin-bottom: 20px;
        filter: drop-shadow(0px 0px 15px rgba(0,0,0,0.5));
    }}

    .metric-card {{
        background: {card_color};
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        text-align: center;
        border-bottom: 5px solid #C11B17;
    }}

    .chart-box {{
        background-color: {card_color};
        border: 2px solid #e2e8f0;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        cols = ['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'Supplier', 'Status', 'Update Status']
        return pd.DataFrame(columns=cols)
    
    cols_to_fix = ['Material', 'PO No', 'Resv']
    for col in cols_to_fix:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str).replace('0', '')
    
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    
    str_cols = ['Dept.', 'Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status', 'Update Status']
    for col in str_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
    return data

try:
    df_master = load_data()
except Exception as e:
    st.error(f"Koneksi Gagal: {e}")
    st.stop()

# --- 5. RENDER HEADER (WHITE TEXT) ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" class="logo-img-header">
            <h1 class="giant-title">Purchase Order Monitoring</h1>
            <h2 class="giant-sub">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    <div style="border-bottom: 3px solid #C11B17; margin-bottom: 25px;"></div>
    """, unsafe_allow_html=True)

# --- 6. FILTER (CASCADING) ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c0, c1, c2, c3 = st.columns(4)
    
    filtered_for_opts = df_master.copy()
    def get_dynamic_opts(df, col):
        return sorted([x for x in df[col].unique() if x and str(x) != "nan"])

    f_dept = c0.multiselect("Filter Dept.", options=get_dynamic_opts(df_master, "Dept."))
    if f_dept: filtered_for_opts = filtered_for_opts[filtered_for_opts["Dept."].isin(f_dept)]

    f_fleet = c1.multiselect("Filter Fleet", options=get_dynamic_opts(filtered_for_opts, "Fleet"))
    if f_fleet: filtered_for_opts = filtered_for_opts[filtered_for_opts["Fleet"].isin(f_fleet)]

    f_unit = c2.multiselect("Filter Unit", options=get_dynamic_opts(filtered_for_opts, "Unit no"))
    if f_unit: filtered_for_opts = filtered_for_opts[filtered_for_opts["Unit no"].isin(f_unit)]

    f_status = c3.multiselect("Filter Status", options=get_dynamic_opts(filtered_for_opts, "Status"))

df_display = filtered_for_opts.copy()
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 7. SUMMARY CARDS ---
total = len(df_display)
outstanding = len(df_display[df_display['Status'] == 'Outstanding'])
complete = len(df_display[df_display['Status'] == 'Complete'])

m1, m2, m3 = st.columns(3)
m1.markdown(f'<div class="metric-card"><p style="font-size:14px; font-weight:bold; margin:0;">TOTAL ITEMS</p><p style="font-size:36px; font-weight:800; color:#1f4e79; margin:0;">{total}</p></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="metric-card" style="border-bottom-color: #ef4444;"><p style="font-size:14px; font-weight:bold; margin:0;">OUTSTANDING</p><p style="font-size:36px; font-weight:800; color:#ef4444; margin:0;">{outstanding}</p></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="metric-card" style="border-bottom-color: #22c55e;"><p style="font-size:14px; font-weight:bold; margin:0;">COMPLETE</p><p style="font-size:36px; font-weight:800; color:#22c55e; margin:0;">{complete}</p></div>', unsafe_allow_html=True)

# --- 8. GRAFIK ---
if not df_display.empty:
    st.write("") 
    g1, g2, g3 = st.columns(3)

    with g1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        pic_counts = df_display['PIC'].value_counts()
        fig1 = go.Figure(data=[go.Pie(labels=pic_counts.index, values=pic_counts.values, hole=.5, marker=dict(colors=px.colors.qualitative.Bold, line=dict(color='#FFFFFF', width=2)))])
        fig1.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color='white', size=14, family="Arial Black"))
        fig1.update_layout(title_text="Workload by PIC", title_x=0.5, height=450, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st_counts = df_display['Status'].value_counts()
        color_map = {'Complete': '#2ecc71', 'Outstanding': '#ff69b4', 'On Process': '#3b82f6'}
        fig2 = go.Figure(data=[go.Pie(labels=st_counts.index, values=st_counts.values, hole=.5, marker=dict(colors=[color_map.get(s, '#94a3b8') for s in st_counts.index], line=dict(color='#FFFFFF', width=2)))])
        fig2.update_traces(textinfo='label+percent', textposition='inside', textfont=dict(color='white', size=14, family="Arial Black"))
        fig2.update_layout(title_text="Status Distribution", title_x=0.5, height=450, showlegend=False, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with g3:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        unit_data = df_display['Unit no'].value_counts().nlargest(5).reset_index()
        fig3 = go.Figure(go.Bar(x=unit_data['Unit no'], y=unit_data['count'], marker=dict(color=px.colors.qualitative.Vivid[:len(unit_data)], line=dict(color='#FFFFFF', width=2)), text=unit_data['count'], textposition='inside', textfont=dict(color='white', family="Arial Black", size=16)))
        fig3.update_layout(title_text="Top 5 Units", title_x=0.5, height=450, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(tickfont=dict(family="Arial Black", size=14, color="#1f4e79")))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 9. DATA EDITOR ---
st.markdown("### 📋 Database Monitoring")
df_to_edit = df_display.copy()
df_to_edit.index = range(1, len(df_to_edit) + 1)
edited_data = st.data_editor(df_to_edit, use_container_width=True, height=500, key="editor_final_white_font",
    column_config={
        "Dept.": st.column_config.TextColumn("Dept.", width=100, pinned=True),
        "Doc Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"), 
        "Status": st.column_config.SelectboxColumn("Status", options=["Complete", "Outstanding", "On Process"])
    })

# --- 10. ACTIONS ---
c_save, c_exp, _ = st.columns([1.5, 1.5, 4])
if c_save.button("💾 SIMPAN & SYNC CLOUD"):
    try:
        final_df = pd.concat([df_master[~df_master.index.isin(df_display.index)], edited_data.reset_index(drop=True)]).reset_index(drop=True)
        if 'Doc Date' in final_df.columns: final_df['Doc Date'] = pd.to_datetime(final_df['Doc Date']).dt.strftime('%Y-%m-%d')
        conn.update(data=final_df)
        st.cache_data.clear()
        st.success("Sinkronisasi Berhasil!")
        st.rerun()
    except Exception as e: st.error(f"Gagal: {e}")

excel_data = io.BytesIO()
with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer: df_display.to_excel(writer, index=False)
c_exp.download_button("📊 EXPORT EXCEL", data=excel_data.getvalue(), file_name='NHM_Database.xlsx')

st.markdown("<div style='text-align: center; color: #94a3b8; margin-top: 40px; font-size: 14px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</div>", unsafe_allow_html=True)