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

# Inisialisasi Session State agar data tidak hilang/reset
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'show_complete_options' not in st.session_state:
    st.session_state['show_complete_options'] = False
if 'bulk_df' not in st.session_state:
    st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": "", "Status": "", "Delivery Note": ""}] * 5)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 'Deliv. Date', 'DDP', 'Supplier', 'Status', 'Delivery Note'])
    
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    return data

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
        if st.button("🔄 Force Refresh GSheet"):
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
    .giant-title {{ font-size: 45px; font-weight: 900; color: white !important; background: rgba(31, 78, 121, 0.8); padding: 10px 30px; border-radius: 10px; }}
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; }}
    </style>
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" style="height:90px;"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
        <h2 style="color:white; letter-spacing:5px;">NHM SUPPLY CHAIN & LOGISTICS</h2>
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
        # Agar tidak ter-reset, kita buat salinan dari master
        df_to_edit = df_f.copy()
        if 'Pilih' not in df_to_edit.columns: df_to_edit.insert(0, 'Pilih', False)
        
        def highlight_logic(row):
            c_full = 'background-color: #ff5252; color: white; font-weight: bold;'
            c_po = 'background-color: #b71c1c; color: white; border: 1px solid white;'
            return [c_po if col == 'PO No' else c_full for col in row.index] if row['Pilih'] else [''] * len(row)

        # Menggunakan session state di data_editor untuk menjaga stabilitas data
        edited_table = st.data_editor(
            df_to_edit.style.apply(highlight_logic, axis=1), 
            use_container_width=True, 
            hide_index=True, 
            height=calc_h, 
            key="editor_main_nhm"
        )
        
        # SINKRONISASI: Update Master jika ada perubahan manual di cell Status/Delivery Note
        if not edited_table.equals(df_to_edit):
            for i, row in edited_table.iterrows():
                # Cari baris yang sama di master menggunakan index asli atau PO No + Item
                mask = (st.session_state.df_master['PO No'] == row['PO No']) & (st.session_state.df_master['PO Item'] == row['PO Item'])
                st.session_state.df_master.loc[mask, 'Status'] = row['Status']
                st.session_state.df_master.loc[mask, 'Delivery Note'] = row['Delivery Note']

        sel_idx = edited_table[edited_table['Pilih'] == True].index
        st.write("🔧 **Quick Actions:**")
        a1, a2, a3 = st.columns([1,1,3])
        if a1.button("🔴 Set Outstanding") and not sel_idx.empty:
            target_ids = edited_table.loc[sel_idx, ['PO No', 'PO Item']]
            for _, r in target_ids.iterrows():
                mask = (st.session_state.df_master['PO No'] == r['PO No']) & (st.session_state.df_master['PO Item'] == r['PO Item'])
                st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = ["Outstanding", ""]
            st.rerun()

        if a2.button("💾 SAVE TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("Tersimpan Permanen!")
            st.rerun()
    else:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=calc_h)

# --- TAB UPDATE (SINKRONISASI VISUAL TABEL INPUT) ---
if tab_update:
    with tab_update:
        st.markdown("### 🛠️ Bulk Update Status & Delivery Note")
        
        # Tampilkan tabel input yang tersimpan di session state
        input_bulk = st.data_editor(
            st.session_state.bulk_df, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="bulk_editor_view"
        )
        
        # Update session state bulk_df jika ada ketikan manual
        st.session_state.bulk_df = input_bulk

        st.write("⚙️ **Aksi Pemrosesan:**")
        b1, b2, b3, b_manual = st.columns(4)
        
        clean_in = input_bulk[(input_bulk['PO No'].str.strip() != "") & (input_bulk['PO Item'].str.strip() != "")]
        
        def run_bulk_sync(stat=None, dn=None, manual=False):
            updated_count = 0
            new_bulk_view = st.session_state.bulk_df.copy()
            
            for idx, r in clean_in.iterrows():
                p_no = str(r['PO No']).strip()
                p_item = str(r['PO Item']).strip()
                mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == p_item)
                
                if mask.any():
                    target_stat = str(r['Status']) if manual else stat
                    target_dn = str(r['Delivery Note']) if manual else dn
                    
                    # Update Database Utama
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [target_stat, target_dn]
                    # Update Visual Tabel di Tab Ini
                    new_bulk_view.loc[idx, ['Status', 'Delivery Note']] = [target_stat, target_dn]
                    updated_count += 1
            
            st.session_state.bulk_df = new_bulk_view
            if updated_count > 0:
                st.success(f"Berhasil update {updated_count} baris. Data sudah muncul di tabel atas dan Dashboard.")
                st.rerun()
            else: st.warning("PO tidak ditemukan.")

        if b1.button("🔴 Bulk Outstanding"): run_bulk_sync("Outstanding", "")
        if b2.button("🟢 Bulk Bitung"): run_bulk_sync("Complete", "Receive at Bitung")
        if b3.button("🟢 Bulk Site"): run_bulk_sync("Complete", "Receive at Site")
        if b_manual.button("📝 Apply Manual Input", type="primary"): run_bulk_sync(manual=True)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
