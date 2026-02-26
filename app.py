import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
import plotly.graph_objects as go
import base64
from datetime import datetime

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'bulk_key' not in st.session_state:
    st.session_state.bulk_key = 0
if 'daily_key' not in st.session_state:
    st.session_state.daily_key = 0

# Inisialisasi DataFrame
if 'bulk_df' not in st.session_state:
    st.session_state.bulk_df = pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"])

COLUMNS_ORDER = [
    'Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'PR No', 'PR Item', 
    'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 
    'Delivery Date', 'DDP', 'Supplier', 'Status', 
    'Last Update', 'Delivery Note'
]

PERSONAL_COLS = [
    'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 
    'Delivery Date', 'DDP', 'Supplier', 'Status', 'Last Update', 'Delivery Note'
]

if 'daily_df' not in st.session_state:
    st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=COLUMNS_ORDER)
    data.columns = [str(c).strip() for c in data.columns]
    for old_col in ['Deliv. Date', 'Delivery date']:
        if old_col in data.columns: data = data.drop(columns=[old_col])
    for col in COLUMNS_ORDER:
        if col not in data.columns: data[col] = ""
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    data = data[COLUMNS_ORDER]
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.replace(r'^nan$', '', regex=True).str.replace(r'\.0$', '', regex=True)
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

def save_to_gsheets(df_to_save):
    try:
        df_clean = df_to_save.drop(columns=['Pilih'], errors='ignore')
        conn.update(data=df_clean)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal simpan ke Cloud: {e}")
        return False

# --- 3. SIDEBAR & CSS ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        with st.form("login_form"):
            admin_pw = st.text_input("Password Admin:", type="password")
            if st.form_submit_button("Login"):
                if admin_pw == "nhm123":
                    st.session_state['authenticated'] = True
                    st.rerun()
                else: st.error("Password Salah")
    else:
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
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
    .giant-title {{ font-size: 50px; font-weight: 900; color: white !important; background: rgba(31, 78, 121, 0.8); padding: 10px 40px; border-radius: 15px; }}
    .header-sub {{ color: white; font-size: 40px !important; font-weight: 800; letter-spacing: 5px; text-shadow: 3px 3px 6px black; margin-top: 15px; }}
    button[data-baseweb="tab"] div p {{ font-size: 32px !important; font-weight: bold !important; }}
    .stSelectbox label p, .stMultiSelect label p, .stTextInput label p {{ font-size: 30px !important; font-weight: bold !important; color: #1f4e79 !important; }}
    [data-testid="stTableColumnHeaderCell"] div {{ font-size: 40px !important; font-weight: 900 !important; color: #1f4e79 !important; padding: 15px 0px !important; }}
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; }}
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"""<div class="custom-header"><div style="background:white;padding:10px;border-radius:10px;display:inline-block;"><img src="data:image/jpeg;base64,{logo_img}" style="height:100px;"></div><br><h1 class="giant-title">Purchase Order Monitoring</h1><div class="header-sub">NHM SUPPLY CHAIN & LOGISTICS</div></div>""", unsafe_allow_html=True)

# --- 4. GLOBAL FILTERS (UNTUK ADMIN & VIEWER) ---
st.markdown("### 🔍 Filter Monitoring")
df_master_cur = st.session_state.df_master.copy()
def get_options(col): return sorted([str(x) for x in df_master_cur[col].dropna().unique() if str(x).strip() != "" and str(x).lower() != 'nan'])

c1, c2, c3, c4 = st.columns(4)
f_dept = c1.multiselect("Dept", get_options('Dept.'), key="global_dept")
f_fleet = c2.multiselect("Fleet", get_options('Fleet'), key="global_fleet")
f_unit = c3.multiselect("Unit", get_options('Unit no'), key="global_unit")
f_stat = c4.multiselect("Status", get_options('Status'), key="global_stat")

df_f = df_master_cur.copy()
if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]

search_q = st.text_input("Global Search:", placeholder="Cari apapun...", key="global_search")
if search_q:
    df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

# --- 5. TABS LOGIC ---
if st.session_state['authenticated']:
    tab_monitor, tab_personal, tab_bulk, tab_daily = st.tabs(["📊 DASHBOARD", "👤 PERSONAL DASHBOARD", "🛠️ BULK STATUS", "📅 DAILY UPDATE"])
    
    with tab_monitor:
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

        if not df_f.empty:
            g1, g2, g3 = st.columns(3)
            with g1:
                # FIX VALUE ERROR: Nama kolom eksplisit
                pic_data = df_f['PIC'].value_counts().reset_index()
                pic_data.columns = ['PIC_Name', 'Count']
                st.plotly_chart(px.bar(pic_data, x='PIC_Name', y='Count', color='PIC_Name', height=350, title="By PIC", text='Count'), use_container_width=True)
            with g2:
                st.plotly_chart(px.pie(df_f, names='Status', hole=.4, height=350, title="By Status", color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'}), use_container_width=True)
            with g3:
                # FIX VALUE ERROR: Nama kolom eksplisit
                unit_data = df_f['Unit no'].value_counts().nlargest(5).reset_index()
                unit_data.columns = ['Unit_No', 'Count']
                st.plotly_chart(px.bar(unit_data, x='Unit_No', y='Count', color='Unit_No', height=350, title="Top 5 Units", text='Count'), use_container_width=True)

        st.markdown("---")
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        st.data_editor(df_ed, use_container_width=True, hide_index=True, height=400, key="main_editor", column_config={"Delivery Date": st.column_config.TextColumn("Delivery Date"), "Doc Date": st.column_config.TextColumn("Doc Date"), "Last Update": st.column_config.TextColumn("Last Update", disabled=True)})
        
        if st.button("💾 SAVE ALL TO GSHEET", type="primary"):
            if save_to_gsheets(st.session_state.df_master):
                st.success("🎉 DATA BERHASIL DISIMPAN KE GOOGLE SHEETS!")
                if st.button("SAYA MENGERTI", key="btn_understand_main"): st.rerun()

    with tab_personal:
        st.markdown("### 👤 Personal Monitoring & Revision")
        df_p_master = st.session_state.df_master.copy()
        cp1, cp2 = st.columns(2)
        pic_opts = sorted([str(x) for x in df_p_master['PIC'].unique() if x and str(x).lower() != 'nan'])
        f_pic_p = cp1.selectbox("Filter PIC Name:", options=["All"] + pic_opts)
        po_opts = sorted([str(x) for x in df_p_master['PO No'].unique() if x and str(x).lower() != 'nan'])
        f_po_p = cp2.selectbox("Filter PO No:", options=["All"] + po_opts)
        
        df_p = df_p_master.copy()
        if f_pic_p != "All": df_p = df_p[df_p['PIC'] == f_pic_p]
        if f_po_p != "All": df_p = df_p[df_p['PO No'] == f_po_p]
        
        edited_p = st.data_editor(df_p[PERSONAL_COLS], use_container_width=True, hide_index=True, height=400, key="personal_editor", column_config={"Last Update": st.column_config.TextColumn("Last Update", disabled=True), "PO No": st.column_config.TextColumn("PO No", disabled=True), "PO Item": st.column_config.TextColumn("PO Item", disabled=True)})
        
        if st.button("🚀 CONFIRM REVISION & SAVE TO GSHEET", type="primary"):
            today_str = datetime.now().strftime("%d-%m-%Y")
            updated_p = 0
            for idx, row in edited_p.iterrows():
                p_no, p_item = str(row['PO No']).strip(), str(row['PO Item']).strip()
                mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == p_item)
                if mask.any():
                    if str(st.session_state.df_master.loc[mask, 'Delivery Note'].values[0]) != str(row['Delivery Note']):
                        st.session_state.df_master.loc[mask, 'Delivery Note'] = str(row['Delivery Note'])
                        st.session_state.df_master.loc[mask, 'Last Update'] = today_str
                        updated_p += 1
                    for col in PERSONAL_COLS:
                        if col not in ['Last Update', 'Delivery Note']: st.session_state.df_master.loc[mask, col] = str(row[col])
            
            if updated_p > 0 and save_to_gsheets(st.session_state.df_master):
                st.success(f"✅ Berhasil Merevisi {updated_p} Data & Simpan Cloud!")
                if st.button("SAYA MENGERTI", key="btn_understand_p"): st.rerun()

    with tab_bulk:
        st.markdown("### 🛠️ Bulk Update Status")
        # Inisialisasi state editor secara manual untuk mencegah data hilang saat copas
        input_bulk = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key=f"bulk_editor_{st.session_state.bulk_key}")
        
        def execute_bulk_update_final(status_val, note_val):
            today_str = datetime.now().strftime("%d-%m-%Y")
            updated = 0
            # Ambil data terbaru dari widget editor menggunakan session_state key
            current_bulk_data = st.session_state[f"bulk_editor_{st.session_state.bulk_key}"]["added_rows"] + [v for k,v in st.session_state[f"bulk_editor_{st.session_state.bulk_key}"]["edited_rows"].items()]
            # Gunakan input_bulk sebagai sumber data paling akurat
            for _, r in input_bulk.iterrows():
                p_no, p_item = str(r['PO No']).strip(), str(r['PO Item']).strip()
                mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == p_item)
                if mask.any() and p_no != "":
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note', 'Last Update']] = [status_val, note_val, today_str]
                    updated += 1
            if updated > 0 and save_to_gsheets(st.session_state.df_master):
                st.session_state.bulk_df = pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"])
                st.session_state.bulk_key += 1
                st.success(f"✅ {updated} Data Berhasil Update & Simpan Cloud!")
                if st.button("SAYA MENGERTI", key="btn_understand_b"): st.rerun()

        c1, c2, c3 = st.columns(3)
        if c1.button("🔴 Set Outstanding"): execute_bulk_update_final("Outstanding", "")
        if c2.button("🟢 Set Bitung Complete"): execute_bulk_update_final("Complete", "Receive at Bitung")
        if c3.button("🟢 Set Site Complete"): execute_bulk_update_final("Complete", "Receive at Site")

    with tab_daily:
        st.markdown("### 📅 Daily Update")
        daily_input = st.data_editor(st.session_state.daily_df, num_rows="dynamic", use_container_width=True, key=f"daily_editor_{st.session_state.daily_key}")
        if st.button("🚀 INSERT & AUTO SAVE"):
            clean_new = daily_input[daily_input['PO No'].astype(str).str.strip() != ""].copy()
            if not clean_new.empty:
                today_str = datetime.now().strftime("%d-%m-%Y")
                clean_new['Status'], clean_new['Last Update'] = "Outstanding", today_str
                st.session_state.df_master = pd.concat([st.session_state.df_master, clean_new], ignore_index=True)
                if save_to_gsheets(st.session_state.df_master):
                    st.success("✅ Data Baru Berhasil Masuk Cloud!")
                    st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)
                    st.session_state.daily_key += 1
                    if st.button("SAYA MENGERTI", key="btn_understand_d"): st.rerun()

else:
    # --- VIEWER MODE (DENGAN FILTER) ---
    st.markdown("---")
    st.markdown("### 📋 Database Monitoring (View Only)")
    st.dataframe(df_f, use_container_width=True, hide_index=True, height=600)

# EXPORT
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr: st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
