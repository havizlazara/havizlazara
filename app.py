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

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note', 'PO No', 'PO Item'])
    
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    if 'Delivery Note' not in data.columns: data['Delivery Note'] = ""
    if 'PO Item' not in data.columns: data['PO Item'] = ""
    
    text_cols = ['Resv', 'Material', 'PO No', 'PO Item', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note']
    for col in text_cols:
        if col in data.columns:
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
    .logo-container {{ background-color: white; padding: 10px; border-radius: 10px; display: inline-block; }}
    .logo-img {{ height: 90px; width: auto; }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 45px; font-weight: 900; color: #ffffff !important; 
        background: rgba(31, 78, 121, 0.8); padding: 10px 30px; border-radius: 10px; display: inline-block;
    }}
    </style>
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" class="logo-img"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
        <h2 style="color:white; letter-spacing:5px;">NHM SUPPLY CHAIN & LOGISTICS</h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. TABS ---
if st.session_state['authenticated']:
    tab_monitor, tab_update = st.tabs(["📊 Monitoring Dashboard", "🛠️ Bulk Update Status"])
else:
    tab_monitor = st.container()
    tab_update = None

# --- TAB MONITORING ---
with tab_monitor:
    st.markdown("### 🔍 Filter Monitoring")
    search_q = st.text_input("🔎 Global Search:", placeholder="Cari data...")

    # Filter Logic
    c1, c2, c3, c4 = st.columns(4)
    df_f = st.session_state.df_master.copy()
    f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
    if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
    f_stat = c4.multiselect("Status", options=sorted(df_f['Status'].unique()))
    if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]
    
    if search_q:
        df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL ITEMS", len(df_f))
    m2.metric("OUTSTANDING", len(df_f[df_f['Status'] == 'Outstanding']))
    m3.metric("COMPLETE", len(df_f[df_f['Status'] == 'Complete']))

    # Database
    calc_h = min(max((len(df_f) + 1) * 35 + 40, 250), 800)
    
    if st.session_state['authenticated']:
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        def apply_style(row):
            c_f = 'background-color: #ff5252; color: white;'
            c_p = 'background-color: #b71c1c; color: white; font-weight: bold;'
            return [c_p if col == 'PO No' else c_f for col in row.index] if row['Pilih'] else [''] * len(row)

        res_ed = st.data_editor(df_ed.style.apply(apply_style, axis=1), use_container_width=True, hide_index=True, height=calc_h, key="main_editor")
        
        if st.button("💾 SIMPAN SEMUA PERUBAHAN", type="primary"):
            save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_df)
            st.success("Tersimpan!")
    else:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=calc_h)

# --- TAB UPDATE (FITUR BARU) ---
if tab_update:
    with tab_update:
        st.markdown("### 🛠️ Bulk Update Berdasarkan PO & Item")
        st.info("Petunjuk: Masukkan daftar PO No dan PO Item di tabel bawah ini untuk merubah Status secara massal.")
        
        # Buat dataframe kosong untuk input admin
        if 'bulk_input' not in st.session_state:
            st.session_state.bulk_input = pd.DataFrame([{"PO No": "", "PO Item": ""}] * 10)
        
        input_data = st.data_editor(
            st.session_state.bulk_input, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="bulk_editor"
        )
        
        st.markdown("---")
        st.write("📍 **Pilih Aksi untuk data di atas:**")
        b1, b2, b3, b4 = st.columns(4)
        
        # Bersihkan input yang kosong
        clean_input = input_data[(input_data['PO No'] != "") & (input_data['PO Item'] != "")]
        
        def bulk_process(new_status, new_dn):
            count = 0
            for idx, row in clean_input.iterrows():
                target = (st.session_state.df_master['PO No'] == str(row['PO No'])) & \
                         (st.session_state.df_master['PO Item'] == str(row['PO Item']))
                if target.any():
                    st.session_state.df_master.loc[target, 'Status'] = new_status
                    st.session_state.df_master.loc[target, 'Delivery Note'] = new_dn
                    count += 1
            if count > 0:
                st.success(f"Berhasil mengupdate {count} baris data!")
                st.balloons()
            else:
                st.warning("Tidak ada data yang cocok ditemukan di Database.")

        if b1.button("🔴 Set Outstanding", use_container_width=True):
            bulk_process("Outstanding", "")
            
        if b2.button("🟡 Set Partial", use_container_width=True):
            bulk_process("Partial", "Partial Delivery")
            
        if b3.button("🟢 Set Complete (Site)", use_container_width=True):
            bulk_process("Complete", "Receive on Site")
            
        if b4.button("🟢 Set Complete (Bitung)", use_container_width=True):
            bulk_process("Complete", "Receive on Bitung")

# --- 9. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
