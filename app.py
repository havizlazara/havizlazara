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

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Menggunakan ttl=0 agar selalu mengambil data paling fresh saat dipanggil
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 'Deliv. Date', 'DDP', 'Supplier', 'Status', 'Delivery Note'])
    
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    # Pastikan Kolom Krusial
    required_cols = ['PO No', 'PO Item', 'Status', 'Delivery Note']
    for col in required_cols:
        if col not in data.columns: data[col] = ""
    
    # Konversi semua ke string untuk keamanan GSheets
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    return data

# Load data ke session state jika belum ada
if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_pw = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
            if admin_pw == "nhm123":
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("Password Salah")
    else:
        st.success("Mode Admin Aktif")
        if st.button("Refresh Data"): # Tombol manual untuk tarik data ulang
            st.cache_data.clear()
            st.session_state.df_master = load_data()
            st.rerun()
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

# --- 4. CSS & HEADER ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg = get_base64_image("BG2.jpg")
logo_img = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f1f5f9; }}
    .main .block-container {{ background-color: #ffffff; padding: 2rem 3rem; border-radius: 12px; }}
    .custom-header {{
        position: relative; width: 100%; min-height: 280px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg}");
        background-size: cover; background-position: center; border: 3px solid #1f4e79;
    }}
    .logo-container {{ background-color: white; padding: 10px; border-radius: 10px; display: inline-block; margin-bottom: 10px; }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 45px; font-weight: 900; color: #ffffff !important; 
        background: rgba(31, 78, 121, 0.8); padding: 10px 30px; border-radius: 10px; display: inline-block;
    }}
    .metric-card {{
        background: white; border-radius: 10px; padding: 15px; text-align: center;
        border-bottom: 5px solid #1f4e79; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    </style>
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" style="height:90px;"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
        <h2 style="color:white; letter-spacing:5px; text-shadow: 2px 2px 4px black;">NHM SUPPLY CHAIN & LOGISTICS</h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. TABS ---
if st.session_state['authenticated']:
    tab_monitor, tab_update = st.tabs(["📊 Dashboard Monitoring", "🛠️ Bulk Update Status"])
else:
    tab_monitor = st.container()
    tab_update = None

# --- TAB MONITORING ---
with tab_monitor:
    st.markdown("### 🔍 Filter & Search")
    df_f = st.session_state.df_master.copy()
    
    c1, c2, c3, c4 = st.columns(4)
    f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
    if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
    f_fleet = c2.multiselect("Fleet", options=sorted(df_f['Fleet'].unique()))
    if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
    f_unit = c3.multiselect("Unit no", options=sorted(df_f['Unit no'].unique()))
    if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
    f_stat = c4.multiselect("Status", options=sorted(df_f['Status'].unique()))
    if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]

    search_q = st.text_input("🔎 Search All Columns:", placeholder="Cari data...")
    if search_q:
        df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

    if st.session_state['authenticated']:
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📋 Database Monitoring")
    calc_h = min(max((len(df_f) + 1) * 35 + 45, 250), 800)
    
    if st.session_state['authenticated']:
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        def highlight_row(row):
            c_full = 'background-color: #ff5252; color: white; font-weight: bold;'
            c_po = 'background-color: #b71c1c; color: white; border: 1px solid white;'
            return [c_po if col == 'PO No' else c_full for col in row.index] if row['Pilih'] else [''] * len(row)

        res_ed = st.data_editor(df_ed.style.apply(highlight_row, axis=1), use_container_width=True, hide_index=True, height=calc_h, key="editor_auth")
        
        sel_idx = res_ed[res_ed['Pilih'] == True].index
        st.write("🔧 **Admin Quick Actions:**")
        a1, a2, a3, a4 = st.columns([1,1,1,2])
        
        if a1.button("🔴 Set Outstanding") and not sel_idx.empty:
            st.session_state.df_master.loc[sel_idx, ['Status', 'Delivery Note']] = ["Outstanding", ""]
            st.rerun()
        if a4.button("💾 SAVE TO GSHEET", type="primary"):
            save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_df)
            st.cache_data.clear() # MEMBERSIHKAN CACHE
            st.success("Berhasil Disimpan ke Cloud!")
            st.rerun()
    else:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=calc_h)

# --- TAB UPDATE (PERBAIKAN VISUAL & LOGIKA) ---
if tab_update:
    with tab_update:
        st.markdown("### 🛠️ Bulk Update Status & Delivery Note")
        st.write("1. Masukkan PO No & Item. 2. Klik tombol aksi. 3. Cek Dashboard Monitoring untuk melihat hasil.")
        
        if 'bulk_df' not in st.session_state: 
            st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": "", "Status": "", "Delivery Note": ""}] * 5)
        
        bulk_input = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key="bulk_editor")
        
        b1, b2, b3, b_manual = st.columns(4)
        clean_in = bulk_input[(bulk_input['PO No'].astype(str).str.strip() != "") & (bulk_input['PO Item'].astype(str).str.strip() != "")]
        
        def process_bulk(stat=None, dn=None, use_manual=False):
            updated = 0
            for _, r in clean_in.iterrows():
                mask = (st.session_state.df_master['PO No'].astype(str) == str(r['PO No']).strip()) & \
                       (st.session_state.df_master['PO Item'].astype(str) == str(r['PO Item']).strip())
                if mask.any():
                    if use_manual:
                        st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [str(r['Status']), str(r['Delivery Note'])]
                    else:
                        st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [stat, dn]
                    updated += 1
            if updated > 0: 
                st.success(f"Berhasil memproses {updated} baris! Data sudah masuk ke Database. Silakan cek tab Dashboard.")
            else: 
                st.warning("Data tidak ditemukan di database.")

        if b1.button("🔴 Bulk Outstanding"): process_bulk("Outstanding", "")
        if b2.button("🟢 Bulk Bitung"): process_bulk("Complete", "Receive at Bitung")
        if b3.button("🟢 Bulk Site"): process_bulk("Complete", "Receive at Site")
        if b_manual.button("📝 Apply Manual Input", type="primary"): process_bulk(use_manual=True)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
