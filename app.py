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

# PERBAIKAN: Inisialisasi DataFrame kosong tanpa batasan baris (Dynamic)
if 'bulk_df' not in st.session_state:
    st.session_state.bulk_df = pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"])

# Urutan kolom resmi
COLUMNS_ORDER = [
    'Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'PR No', 'PR Item', 
    'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 
    'Delivery Date', 'DDP', 'Supplier', 'Status', 
    'Last Update', 'Delivery Note'
]

# Kolom untuk Personal Dashboard
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

# FUNGSI PERBAIKAN: Menangkap perubahan data secara dinamis (termasuk baris tambahan)
def update_bulk_state():
    key = f"bulk_editor_{st.session_state.bulk_key}"
    if key in st.session_state:
        edits = st.session_state[key]
        # Tangkap baris baru hasil paste
        if edits.get("added_rows"):
            for row in edits["added_rows"]:
                st.session_state.bulk_df = pd.concat([st.session_state.bulk_df, pd.DataFrame([row])], ignore_index=True)
        # Tangkap baris yang diedit
        if edits.get("edited_rows"):
            for row_idx, values in edits["edited_rows"].items():
                for k, v in values.items():
                    st.session_state.bulk_df.at[int(row_idx), k] = v

def update_daily_state():
    if "daily_editor" in st.session_state:
        edits = st.session_state["daily_editor"]
        for row_idx, values in edits.get("edited_rows", {}).items():
            for key, val in values.items():
                st.session_state.daily_df.at[int(row_idx), key] = val

# --- 3. SIDEBAR ---
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

# --- 4. CSS CUSTOM ---
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
    .chart-box {{ background-color: white; border: 2px solid #e2e8f0; border-radius: 15px; padding: 15px; }}
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
    tab_monitor, tab_personal, tab_bulk, tab_daily = st.tabs(["📊 DASHBOARD", "👤 PERSONAL DASHBOARD", "🛠️ BULK STATUS", "📅 DAILY UPDATE"])
    
    with tab_monitor:
        st.markdown("### 🔍 Filter Monitoring")
        df_master_cur = st.session_state.df_master.copy()
        def get_options(col): return sorted([str(x) for x in df_master_cur[col].dropna().unique() if str(x).strip() != "" and str(x).lower() != 'nan'])
        c1, c2, c3, c4 = st.columns(4)
        f_dept = c1.multiselect("Dept", options=get_options('Dept.'), key="f_dept")
        f_fleet = c2.multiselect("Fleet", options=get_options('Fleet'), key="f_fleet")
        f_unit = c3.multiselect("Unit", options=get_options('Unit no'), key="f_unit")
        f_stat = c4.multiselect("Status", options=get_options('Status'), key="f_stat")
        df_f = df_master_cur.copy()
        if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
        if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
        if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
        if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]
        search_q = st.text_input("Global Search:", placeholder="Cari...", key="gs_admin")
        if search_q: df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

        if not df_f.empty:
            st.write("")
            g1, g2, g3 = st.columns(3)
            with g1:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                pic_c = df_f['PIC'].value_counts().reset_index()
                pic_c.columns = ['PIC_Name', 'Total_Count']
                fig1 = px.bar(pic_c, x='PIC_Name', y='Total_Count', color='PIC_Name', height=380, title="Monitoring by PIC", text='Total_Count')
                st.plotly_chart(fig1, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g2:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                fig2 = px.pie(df_f, names='Status', hole=.4, height=380, title="By Status",
                              color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12', 'Partially':'#f39c12'})
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g3:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                ud = df_f['Unit no'].value_counts().nlargest(5).reset_index()
                ud.columns = ['Unit_ID', 'Unit_Count']
                fig3 = px.bar(ud, x='Unit_ID', y='Unit_Count', height=380, title="Top 5 Units", color='Unit_ID')
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        calc_h = min(max((len(df_f) + 1) * 35 + 100, 250), 800)
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        st.data_editor(df_ed, use_container_width=True, hide_index=True, height=calc_h, key="main_editor", column_config={"Delivery Date": st.column_config.TextColumn("Delivery Date"), "Doc Date": st.column_config.TextColumn("Doc Date"), "Last Update": st.column_config.TextColumn("Last Update", disabled=True)})
        
        if st.button("💾 SAVE ALL TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("✅ Berhasil Simpan Permanen ke Google Sheets!")
            st.rerun()

    with tab_personal:
        st.markdown("### 👤 Personal Monitoring & Instant Update")
        df_p_master = st.session_state.df_master.copy()
        cp1, cp2 = st.columns(2)
        pic_opts = sorted([str(x) for x in df_p_master['PIC'].unique() if x and str(x).lower() != 'nan'])
        f_pic = cp1.selectbox("Filter PIC Name:", options=["All"] + pic_opts)
        po_opts = sorted([str(x) for x in df_p_master['PO No'].unique() if x and str(x).lower() != 'nan'])
        f_po = cp2.selectbox("Filter PO No:", options=["All"] + po_opts)
        df_p = df_p_master.copy()
        if f_pic != "All": df_p = df_p[df_p['PIC'] == f_pic]
        if f_po != "All": df_p = df_p[df_p['PO No'] == f_po]
        
        edited_p = st.data_editor(df_p[PERSONAL_COLS], use_container_width=True, hide_index=True, height=500, key="personal_editor", column_config={"Last Update": st.column_config.TextColumn("Last Update", disabled=True), "PO No": st.column_config.TextColumn("PO No", disabled=True), "PO Item": st.column_config.TextColumn("PO Item", disabled=True)})
        
        if st.button("🚀 CONFIRM REVISION & SAVE TO GSHEET", type="primary"):
            updated_p = 0
            today_str = datetime.now().strftime("%d-%m-%Y")
            for idx, row in edited_p.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(row['PO No']).strip()) & (st.session_state.df_master['PO Item'] == str(row['PO Item']).strip())
                if mask.any():
                    if str(st.session_state.df_master.loc[mask, 'Delivery Note'].values[0]) != str(row['Delivery Note']):
                        st.session_state.df_master.loc[mask, 'Delivery Note'] = str(row['Delivery Note'])
                        st.session_state.df_master.loc[mask, 'Last Update'] = today_str
                        updated_p += 1
                    for col in PERSONAL_COLS:
                        if col not in ['Last Update', 'Delivery Note']: st.session_state.df_master.loc[mask, col] = str(row[col])
            if updated_p > 0:
                conn.update(data=st.session_state.df_master)
                st.cache_data.clear()
                st.success(f"✅ Berhasil Merevisi {updated_p} Data & Simpan!")
                st.rerun()

    with tab_bulk:
        st.markdown("### 🛠️ Bulk Update Status")
        # PERBAIKAN UTAMA: Mendukung Dynamic Row Addition agar copas banyak baris tidak terpotong
        input_bulk = st.data_editor(
            st.session_state.bulk_df, 
            num_rows="dynamic", 
            use_container_width=True, 
            key=f"bulk_editor_{st.session_state.bulk_key}", 
            on_change=update_bulk_state
        )
        
        def execute_bulk_update(status_val, note_val):
            updated = 0
            today_str = datetime.now().strftime("%d-%m-%Y")
            for _, r in st.session_state.bulk_df.iterrows():
                p_no = str(r['PO No']).strip()
                p_item = str(r['PO Item']).strip()
                mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == p_item)
                if mask.any() and p_no != "":
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note', 'Last Update']] = [status_val, note_val, today_str]
                    updated += 1
            if updated > 0:
                conn.update(data=st.session_state.df_master)
                st.cache_data.clear()
                st.session_state.bulk_df = pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"])
                st.session_state.bulk_key += 1
                st.success(f"✅ Berhasil Update {updated} baris & Simpan Cloud!")
                st.rerun()
            else: st.warning("⚠️ PO No tidak ditemukan.")

        c_out, c_bitung, c_site, c_man = st.columns(4)
        with c_out:
            if st.button("🔴 Set Outstanding", use_container_width=True): execute_bulk_update("Outstanding", "")
        with c_bitung:
            st.write("**🚢 Set Bitung**")
            cb1, cb2 = st.columns(2)
            if cb1.button("Partial", key="bit_p"): execute_bulk_update("Partial", "Receive at Bitung")
            if cb2.button("Complete", key="bit_c"): execute_bulk_update("Complete", "Receive at Bitung")
        with c_site:
            st.write("**⛰️ Set Site**")
            cs1, cs2 = st.columns(2)
            if cs1.button("Partial", key="site_p"): execute_bulk_update("Partial", "Receive at Site")
            if cs2.button("Complete", key="site_c"): execute_bulk_update("Complete", "Receive at Site")
        with c_man:
            if st.button("📝 Manual Input", type="primary", use_container_width=True):
                today_str = datetime.now().strftime("%d-%m-%Y")
                updated_m = 0
                for _, r in st.session_state.bulk_df.iterrows():
                    p_no = str(r['PO No']).strip()
                    mask = (st.session_state.df_master['PO No'] == p_no) & (st.session_state.df_master['PO Item'] == str(r['PO Item']).strip())
                    if mask.any() and p_no != "":
                        st.session_state.df_master.loc[mask, ['Status', 'Delivery Note', 'Last Update']] = [str(r['Status']), str(r['Delivery Note']), today_str]
                        updated_m += 1
                if updated_m > 0:
                    conn.update(data=st.session_state.df_master)
                    st.cache_data.clear()
                    st.session_state.bulk_df = pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"])
                    st.session_state.bulk_key += 1
                    st.success("✅ Manual Update Berhasil!")
                    st.rerun()

    with tab_daily:
        st.markdown("### 📅 Daily Update (Insert Data Baru)")
        daily_input = st.data_editor(st.session_state.daily_df, num_rows="dynamic", use_container_width=True, key="daily_editor", on_change=update_daily_state, column_config={"Delivery Date": st.column_config.TextColumn("Delivery Date"), "Doc Date": st.column_config.TextColumn("Doc Date"), "Last Update": st.column_config.TextColumn("Last Update", disabled=True)})
        if st.button("🚀 INSERT NEW DATA TO DASHBOARD", type="primary"):
            clean_new_data = st.session_state.daily_df[st.session_state.daily_df['PO No'].fillna("").astype(str).str.strip() != ""].copy()
            if not clean_new_data.empty:
                today_str = datetime.now().strftime("%d-%m-%Y")
                clean_new_data['Status'] = "Outstanding"
                clean_new_data['Last Update'] = today_str
                for col in clean_new_data.columns: clean_new_data[col] = clean_new_data[col].fillna("").astype(str).replace("nan", "")
                st.session_state.df_master = pd.concat([st.session_state.df_master, clean_new_data], ignore_index=True)
                st.success(f"✅ Baris Baru Berhasil Ditambahkan!")
                st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)
                st.rerun()

else:
    # --- VIEWER MODE ---
    st.markdown("### 🔍 Filter Monitoring (Viewer)")
    df_v_master = st.session_state.df_master.copy()
    cv1, cv2, cv3, cv4 = st.columns(4)
    def get_v_options(col): return sorted([str(x) for x in df_v_master[col].unique() if x])
    fv_dept = cv1.multiselect("Dept", options=get_v_options('Dept.'), key="v_dept")
    fv_fleet = cv2.multiselect("Fleet", options=get_v_options('Fleet'), key="v_fleet")
    fv_unit = cv3.multiselect("Unit", options=get_v_options('Unit no'), key="v_unit")
    fv_stat = cv4.multiselect("Status", options=get_v_options('Status'), key="v_stat")
    search_viewer = st.text_input("Global Search:", placeholder="Cari...", key="gs_v")
    df_v = df_v_master.copy()
    if fv_dept: df_v = df_v[df_v['Dept.'].isin(fv_dept)]
    if fv_fleet: df_v = df_v[df_v['Fleet'].isin(fv_fleet)]
    if fv_unit: df_v = df_v[df_v['Unit no'].isin(fv_unit)]
    if fv_stat: df_v = df_v[df_v['Status'].isin(fv_stat)]
    if search_viewer: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search_viewer, case=False).any(), axis=1)]
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=600)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
