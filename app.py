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
if 'bulk_df' not in st.session_state:
    st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": "", "Status": "", "Delivery Note": ""}] * 5)

# Urutan kolom resmi untuk Daily Update
COLUMNS_ORDER = ['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 'Deliv. Date', 'DDP', 'Supplier', 'Status', 'Delivery Note']

if 'daily_df' not in st.session_state:
    st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=COLUMNS_ORDER)
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- FUNGSI UPDATE STATE ---
def update_bulk_state():
    if "bulk_editor" in st.session_state:
        edits = st.session_state["bulk_editor"]
        for row_idx, values in edits.get("edited_rows", {}).items():
            for key, val in values.items():
                st.session_state.bulk_df.at[int(row_idx), key] = val

def update_daily_state():
    if "daily_editor" in st.session_state:
        edits = st.session_state["daily_editor"]
        for row_idx, values in edits.get("edited_rows", {}).items():
            for key, val in values.items():
                st.session_state.daily_df.at[int(row_idx), key] = val
        for row in edits.get("added_rows", []):
            st.session_state.daily_df = pd.concat([st.session_state.daily_df, pd.DataFrame([row])], ignore_index=True)

# --- 3. SIDEBAR (LOGIN WITH ENTER) ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        with st.form("login_form"):
            admin_pw = st.text_input("Password Admin:", type="password")
            submit_login = st.form_submit_button("Login")
            if submit_login:
                if admin_pw == "nhm123":
                    st.session_state['authenticated'] = True
                    st.session_state.df_master = load_data()
                    st.rerun()
                else: st.error("Password Salah")
    else:
        st.success("Mode Admin Aktif")
        if st.button("🔄 Sync & Refresh"):
            st.cache_data.clear()
            st.session_state.df_master = load_data()
            st.rerun()
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

# --- 4. CSS CUSTOM (FONT RAKSASA) ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg = get_base64_image("BG2.jpg")
logo_img = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    .custom-header {{
        position: relative; width: 100%; min-height: 280px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg}");
        background-size: cover; background-position: center; border: 3px solid #1f4e79;
    }}
    .logo-container {{ background-color: white; padding: 10px; border-radius: 10px; display: inline-block; }}
    .giant-title {{ font-size: 50px; font-weight: 900; color: white !important; background: rgba(31, 78, 121, 0.8); padding: 10px 40px; border-radius: 15px; }}
    .header-sub {{ color: white; font-size: 40px !important; font-weight: 800; letter-spacing: 5px; text-shadow: 3px 3px 6px black; margin-top: 15px; }}
    button[data-baseweb="tab"] div p {{ font-size: 32px !important; font-weight: bold !important; }}
    .stSelectbox label p, .stMultiSelect label p, .stTextInput label p {{ font-size: 30px !important; font-weight: bold !important; color: #1f4e79 !important; }}
    [data-testid="stTableColumnHeaderCell"] div {{ font-size: 40px !important; font-weight: 900 !important; color: #1f4e79 !important; padding: 15px 0px !important; }}
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; }}
    .stApp {{ background-color: #f1f5f9; }}
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"""
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" style="height:100px;"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1>
        <div class="header-sub">NHM SUPPLY CHAIN & LOGISTICS</div>
    </div>
    """, unsafe_allow_html=True)

# --- 5. TABS LOGIC ---
if st.session_state['authenticated']:
    tab_monitor, tab_bulk, tab_daily = st.tabs(["📊 DASHBOARD", "🛠️ BULK STATUS", "📅 DAILY UPDATE"])
    
    # --- TAB 1: MONITORING ---
    with tab_monitor:
        st.markdown("### 🔍 Filter Monitoring")
        df_f = st.session_state.df_master.copy()
        c1, c2, c3, c4 = st.columns(4)
        f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
        if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
        f_fleet = c2.multiselect("Fleet", options=sorted(df_f['Fleet'].unique()))
        if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
        f_unit = c3.multiselect("Unit", options=sorted(df_f['Unit no'].unique()))
        if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
        f_stat = c4.multiselect("Status", options=sorted(df_f['Status'].unique()))
        if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

        st.markdown("---")
        calc_h = min(max((len(df_f) + 1) * 35 + 100, 250), 800)
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        edited_table = st.data_editor(df_ed, use_container_width=True, hide_index=True, height=calc_h, key="main_editor")
        
        if st.button("💾 SAVE ALL TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("✅ Berhasil Simpan Permanen!")
            st.rerun()

    # --- TAB 2: BULK STATUS ---
    with tab_bulk:
        st.markdown("### 🛠️ Bulk Update by PO No & Item")
        input_bulk = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key="bulk_editor", on_change=update_bulk_state)
        b1, b2, b3 = st.columns(3)
        
        def run_bulk(stat, dn):
            updated = 0
            for _, r in st.session_state.bulk_df.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(r['PO No']).strip()) & (st.session_state.df_master['PO Item'] == str(r['PO Item']).strip())
                if mask.any() and str(r['PO No']).strip() != "":
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [stat, dn]
                    updated += 1
            st.success(f"✅ Diperbarui {updated} baris di Memori. Klik Save di Dashboard untuk simpan.")

        if b1.button("🔴 Set Outstanding"): run_bulk("Outstanding", "")
        if b2.button("🟢 Set Bitung"): run_bulk("Complete", "Receive at Bitung")
        if b3.button("🟢 Set Site"): run_sync("Complete", "Receive at Site")

    # --- TAB 3: DAILY UPDATE (NEW) ---
    with tab_daily:
        st.markdown("### 📅 Daily Update (Full Row Copy-Paste)")
        st.info("Gunakan format kolom yang sama dengan Dashboard utama.")
        
        daily_input = st.data_editor(
            st.session_state.daily_df, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="daily_editor", 
            on_change=update_daily_state
        )
        
        if st.button("🚀 UPDATE TO MAIN DASHBOARD", type="primary"):
            updated_count = 0
            # Proses setiap baris di daily_df
            for idx, row in st.session_state.daily_df.iterrows():
                p_no = str(row['PO No']).strip()
                p_item = str(row['PO Item']).strip()
                
                if p_no != "" and p_item != "":
                    mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == p_item)
                    if mask.any():
                        # Update seluruh kolom kecuali PO No dan PO Item (opsional bisa semua)
                        for col in COLUMNS_ORDER:
                            st.session_state.df_master.loc[mask, col] = str(row[col])
                        updated_count += 1
            
            if updated_count > 0:
                st.success(f"✅ Berhasil memperbarui {updated_count} baris di Dashboard Utama!")
                # Reset tabel daily setelah berhasil
                st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)
                st.rerun()
            else:
                st.warning("⚠️ Tidak ada data yang cocok ditemukan (Cek PO No & Item).")

else:
    # VIEWER MODE
    st.markdown("### 🔍 Filter Monitoring (Viewer)")
    df_v = st.session_state.df_master.copy()
    # ... Filter viewer logic
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=600)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
