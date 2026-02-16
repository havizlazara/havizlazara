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

# --- 1. LOGIN SYSTEM DI SIDEBAR ---
with st.sidebar:
    st.header("🔐 Admin Access")
    # Anda bisa mengganti 'nhm123' dengan password pilihan Anda
    admin_password = st.text_input("Masukkan Password Admin untuk Edit:", type="password")
    is_admin = admin_password == "nhm123" # Password default
    
    if is_admin:
        st.success("Mode Admin Aktif: Anda bisa mengedit data.")
    else:
        st.info("Mode Viewer: Masukkan password untuk mengedit.")
    
    st.divider()
    st.header("🎨 Theme Customizer")
    bg_color = st.color_picker("Pilih Warna Background Utama", "#f1f5f9")
    card_color = st.color_picker("Pilih Warna Card", "#ffffff")

# --- 2. FUNGSI ENKODE GAMBAR ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg_base64 = get_base64_image("BG2.jpg")
logo_base64 = get_base64_image("NHM.jpg")

# --- 3. CUSTOM CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{
        background-color: {card_color}; padding: 2rem 3rem; max-width: 98%;
        margin: auto; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }}
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Libre+Baskerville:wght@700&display=swap');
    .custom-header {{
        position: relative; width: 100%; min-height: 250px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg_base64}");
        background-size: cover; background-position: center; border: 2px solid #1f4e79;
    }}
    .custom-header::after {{
        content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 0, 0.1); z-index: 1;
    }}
    .header-content {{ position: relative; z-index: 2; }}
    .giant-title {{ 
        font-family: 'Libre Baskerville', serif; font-size: 58px; font-weight: 900; 
        color: #ffffff !important; margin: 0; line-height: 1.2; 
        background: rgba(31, 78, 121, 0.7); padding: 10px 30px; border-radius: 10px; 
        display: inline-block; text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
    }}
    .giant-sub {{ 
        font-family: 'Bebas Neue', cursive; font-size: 30px; color: #ffffff !important; 
        margin: 15px 0 0 0; font-weight: 400; letter-spacing: 5px;
        background: rgba(31, 78, 121, 0.7); padding: 5px 20px; border-radius: 8px; display: inline-block;
    }}
    .logo-img-header {{ height: 110px; width: auto; margin-bottom: 20px; mix-blend-mode: multiply; }}
    .metric-card {{
        background: {card_color}; border-radius: 10px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;
        text-align: center; border-bottom: 5px solid #1f4e79; margin-bottom: 10px;
    }}
    .title-box {{
        background: white; padding: 10px; border-radius: 5px; border: 1px solid #e2e8f0; 
        text-align: center; font-weight: bold; color: #1f4e79; margin-bottom: 15px;
    }}
    .chart-box {{
        background-color: {card_color}; border: 2px solid #e2e8f0; border-radius: 15px; 
        padding: 15px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.05);
    }}
    @media (max-width: 768px) {{ .giant-title {{ font-size: 28px; }} .giant-sub {{ font-size: 16px; }} }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Resv', 'Material', 'PO No'])
    
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    return data

df_master = load_data()

# --- 5. RENDER HEADER ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" class="logo-img-header">
            <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
            <h2 class="giant-sub">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    <div style="border-bottom: 4px solid #1f4e79; margin-bottom: 30px;"></div>
    """, unsafe_allow_html=True)

# --- 6. FILTER ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c_dept, c_fleet, c_unit, c_stat_filter = st.columns(4)
    
    filtered_for_opts = df_master.copy()
    def get_dynamic_opts(df, col):
        return sorted([x for x in df[col].unique() if x and str(x) != "nan"])

    f_dept = c_dept.multiselect("Filter Dept.", options=get_dynamic_opts(df_master, "Dept."))
    if f_dept: filtered_for_opts = filtered_for_opts[filtered_for_opts["Dept."].isin(f_dept)]

    f_fleet = c_fleet.multiselect("Filter Fleet", options=get_dynamic_opts(filtered_for_opts, "Fleet"))
    if f_fleet: filtered_for_opts = filtered_for_opts[filtered_for_opts["Fleet"].isin(f_fleet)]

    f_unit = c_unit.multiselect("Filter Unit", options=get_dynamic_opts(filtered_for_opts, "Unit no"))
    if f_unit: filtered_for_opts = filtered_for_opts[filtered_for_opts["Unit no"].isin(f_unit)]

    f_status = c_stat_filter.multiselect("Filter Status", options=get_dynamic_opts(filtered_for_opts, "Status"))

df_display = filtered_for_opts.copy()
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 7. SUMMARY CARDS ---
total = len(df_display)
outstanding = len(df_display[df_display['Status'] == 'Outstanding'])
complete = len(df_display[df_display['Status'] == 'Complete'])

m1, m2, m3 = st.columns(3)
with m1:
    st.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{total}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">PIC</div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card" style="border-bottom-color: #ef4444;"><b>OUTSTANDING</b><h2>{outstanding}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">STATUS</div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card" style="border-bottom-color: #22c55e;"><b>COMPLETE</b><h2>{complete}</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="title-box">TOP 5 UNITS</div>', unsafe_allow_html=True)

# --- 8. GRAFIK ---
if not df_display.empty:
    g1, g2, g3 = st.columns(3)
    chart_h = 225 
    f_style = dict(size=12, family="Arial Black", color="white")
    with g1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        pic_c = df_display['PIC'].value_counts()
        fig1 = go.Figure(data=[go.Pie(labels=pic_c.index, values=pic_c.values, hole=.5)])
        fig1.update_traces(textinfo='label+percent', textposition='inside', textfont=f_style)
        fig1.update_layout(height=chart_h, showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st_c = df_display['Status'].value_counts()
        colors = ['#ef4444' if s == 'Outstanding' else '#22c55e' for s in st_c.index]
        fig2 = go.Figure(data=[go.Pie(labels=st_c.index, values=st_c.values, hole=.5, marker=dict(colors=colors))])
        fig2.update_traces(textinfo='label+percent', textposition='inside', textfont=f_style)
        fig2.update_layout(height=chart_h, showlegend=False, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        unit_d = df_display['Unit no'].value_counts().nlargest(5).reset_index()
        fig3 = px.bar(unit_d, x='Unit no', y='count', color='Unit no', text='count', color_discrete_sequence=px.colors.qualitative.Bold)
        fig3.update_traces(textposition='inside', textfont=f_style) 
        fig3.update_layout(height=chart_h, showlegend=False, yaxis_visible=False, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=20,b=0,l=0,r=0))
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 9. DATABASE MONITORING (Hanya Edit jika Admin) ---
st.markdown("### 📋 Database Monitoring")
df_to_edit = df_display.copy()
df_to_edit.index = range(1, len(df_to_edit) + 1)

if is_admin:
    # Mode Admin: Bisa Edit & Tambah Baris
    edited_display = st.data_editor(df_to_edit, use_container_width=True, height=500, num_rows="dynamic")
    
    # --- 10. ACTIONS (Simpan & Export) ---
    col_save, col_export, _ = st.columns([1.5, 1.5, 4])
    if col_save.button("💾 SIMPAN & SYNC CLOUD"):
        try:
            not_visible = df_master[~df_master.index.isin(df_display.index)]
            new_edited = edited_display.reset_index(drop=True)
            final_save = pd.concat([not_visible, new_edited], ignore_index=True)
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("Sinkronisasi Berhasil!")
            st.rerun()
        except Exception as e: st.error(f"Gagal: {e}")
else:
    # Mode Viewer: Hanya Tampilkan Data
    st.dataframe(df_to_edit, use_container_width=True, height=500)
    _, col_export, _ = st.columns([1.5, 1.5, 4])
    st.warning("Silakan masukkan password di sidebar untuk mengaktifkan fitur edit.")

# Export tetap bisa dilakukan oleh siapa saja (Viewer)
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
    df_display.to_excel(writer, index=False)
col_export.download_button(label="📊 EXPORT EXCEL", data=excel_buf.getvalue(), file_name="PO_Monitoring.xlsx")

st.markdown("<div style='text-align: center; color: #94a3b8; margin-top: 40px;'>PT Nusa Halmahera Minerals | 2026</div>", unsafe_allow_html=True)