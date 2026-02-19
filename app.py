import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
import plotly.graph_objects as go
import base64

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'show_complete_options' not in st.session_state:
    st.session_state['show_complete_options'] = False
if 'selected_rows_indices' not in st.session_state:
    st.session_state['selected_rows_indices'] = []

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Update status', 'PO No'])
    
    # Pastikan kolom Update status ada
    if 'Update status' not in data.columns:
        data['Update status'] = ""
        
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Update status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. SIDEBAR (LOGIN & THEME) ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_password = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
            if admin_password == "nhm123":
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("Password Salah")
    else:
        st.success("Mode Admin Aktif")
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()
    
    st.divider()
    bg_color = st.color_picker("Warna Background", "#f1f5f9")
    card_color = st.color_picker("Warna Card", "#ffffff")

# --- 4. FUNGSI GAMBAR & CSS ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg_base64 = get_base64_image("BG2.jpg")
logo_base64 = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{ background-color: {card_color}; padding: 2rem 3rem; border-radius: 12px; }}
    .custom-header {{
        position: relative; width: 100%; min-height: 250px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg_base64}");
        background-size: cover; background-position: center; border: 2px solid #1f4e79;
    }}
    .custom-header::after {{ content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.1); z-index: 1; }}
    .header-content {{ position: relative; z-index: 2; }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 50px; font-weight: 900; color: #ffffff !important; 
        background: rgba(31, 78, 121, 0.7); padding: 10px 30px; border-radius: 10px; display: inline-block;
    }}
    .metric-card {{
        background: {card_color}; border-radius: 10px; padding: 15px; text-align: center;
        border-bottom: 5px solid #1f4e79; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    .chart-box {{ background-color: {card_color}; border: 2px solid #e2e8f0; border-radius: 15px; padding: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. RENDER HEADER ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" style="height:100px; mix-blend-mode:multiply;">
            <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
            <h2 style="color:white; letter-spacing:5px;">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. FILTER ---
search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
c1, c2, c3, c4 = st.columns(4)

df_filtered = st.session_state.df_master.copy()
f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
if f_dept: df_filtered = df_filtered[df_filtered['Dept.'].isin(f_dept)]
f_fleet = c2.multiselect("Fleet", options=sorted(df_filtered['Fleet'].unique()))
if f_fleet: df_filtered = df_filtered[df_filtered['Fleet'].isin(f_fleet)]
f_unit = c3.multiselect("Unit", options=sorted(df_filtered['Unit no'].unique()))
if f_unit: df_filtered = df_filtered[df_filtered['Unit no'].isin(f_unit)]
f_stat = c4.multiselect("Status", options=sorted(df_filtered['Status'].unique()))
if f_stat: df_filtered = df_filtered[df_filtered['Status'].isin(f_stat)]

if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 7. SUMMARY CARDS & 8. CHART (DISEMBUNYIKAN AGAR RINGKAS) ---
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_filtered)}</h2></div>', unsafe_allow_html=True)
with m2: st.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_filtered[df_filtered["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
with m3: st.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_filtered[df_filtered["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

# --- 9. DATABASE & LOGIKA TOMBOL ACTION ---
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    df_editor = df_filtered.copy()
    if 'Pilih' not in df_editor.columns:
        df_editor.insert(0, 'Pilih', False)

    edited_df = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
        key="editor_pro"
    )

    # Menangkap Index yang dicentang
    selected_indices = edited_df[edited_df['Pilih'] == True].index

    st.write("🔧 **Admin Actions:**")
    a1, a2, a3, a4 = st.columns([1, 1, 1, 3])
    
    # Tombol 1: Outstanding
    if a1.button("🔴 Outstanding", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.session_state.df_master.loc[selected_indices, 'Update status'] = ""
            st.session_state.show_complete_options = False
            st.rerun()

    # Tombol 2: Partial
    if a2.button("🟡 Partial", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.session_state.show_complete_options = False
            st.rerun()

    # Tombol 3: Complete (Memicu Pilihan Tambahan)
    if a3.button("🟢 Complete", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.show_complete_options = True
            st.session_state.selected_rows_indices = selected_indices
            st.rerun()

    # Tombol 4: Simpan ke GSheets
    if a4.button("💾 SIMPAN SEMUA KE GOOGLE SHEETS", type="primary", use_container_width=True):
        try:
            save_data = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_data)
            st.cache_data.clear()
            st.success("Sinkronisasi Berhasil!")
        except Exception as e: st.error(f"Gagal: {e}")

    # --- LOGIKA SUB-TOMBOL COMPLETE ---
    if st.session_state.show_complete_options:
        st.info(f"📍 Menunggu lokasi penerimaan untuk {len(st.session_state.selected_rows_indices)} baris terpilih:")
        sub1, sub2, sub3 = st.columns([1.5, 1.5, 4])
        
        if sub1.button("📦 Receive on Bitung", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Update status'] = "Receive on Bitung"
            st.session_state.show_complete_options = False # Sembunyikan lagi setelah klik
            st.rerun()
            
        if sub2.button("🚜 Receive on Site", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Update status'] = "Receive on Site"
            st.session_state.show_complete_options = False
            st.rerun()
            
        if sub3.button("❌ Batal", use_container_width=True):
            st.session_state.show_complete_options = False
            st.rerun()

else:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    st.warning("Login di sidebar untuk mengaktifkan Tombol Action.")

# --- 10. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    df_filtered.to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring.xlsx")