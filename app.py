import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
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

# Urutan kolom resmi
COLUMNS_ORDER = [
    'Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'PR No', 'PR Item', 
    'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 
    'Delivery Date', 'DDP', 'Supplier', 'Status', 
    'Last Update', 'Delivery Note'
]

# Kolom Personal Dashboard
PERSONAL_COLS = [
    'Dept.', 'Fleet', 'Unit no', 
    'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 
    'Delivery Date', 'DDP', 'Supplier', 'Status', 'Last Update', 'Delivery Note'
]

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=COLUMNS_ORDER)
    data.columns = [str(c).strip() for c in data.columns]
    for col in COLUMNS_ORDER:
        if col not in data.columns: data[col] = ""
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    data = data[COLUMNS_ORDER]
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.replace(r'^nan$', '', regex=True).str.replace(r'\.0$', '', regex=True)
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- MODAL POP-UP ---
@st.dialog("Notification")
def show_success_modal(message):
    st.success(message)
    if st.button("Done update"):
        st.rerun()

def save_final_changes(df_to_save):
    try:
        df_clean = df_to_save.drop(columns=['Pilih'], errors='ignore')
        conn.update(data=df_clean)
        st.cache_data.clear()
        st.session_state.df_master = df_clean
        return True
    except Exception as e:
        st.error(f"Gagal simpan ke Cloud: {e}")
        return False

# --- 3. SIDEBAR ---
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
        st.success("Admin Active ✅")
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state.daily_key += 1
            st.session_state.bulk_key += 1
            st.rerun()
    
    st.markdown("---")
    ex_buf = io.BytesIO()
    with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr: 
        st.session_state.df_master.to_excel(wr, index=False)
    st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")

# --- 4. CSS CUSTOM ---
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
    [data-testid="stTableColumnHeaderCell"] div {{ font-size: 40px !important; font-weight: 900 !important; color: #1f4e79 !important; }}
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; }}
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"""<div class="custom-header"><div style="background:white;padding:10px;border-radius:10px;display:inline-block;"><img src="data:image/jpeg;base64,{logo_img}" style="height:100px;"></div><br><h1 class="giant-title">Purchase Order Monitoring</h1><div class="header-sub">NHM SUPPLY CHAIN & LOGISTICS</div></div>""", unsafe_allow_html=True)

# --- 5. TABS LOGIC ---
if st.session_state['authenticated']:
    tab_monitor, tab_daily, tab_personal, tab_bulk = st.tabs(["📊 DASHBOARD", "📅 DAILY UPDATE", "👤 PERSONAL DASHBOARD", "🛠️ UPDATE STATUS"])
    
    with tab_monitor:
        st.markdown("### 🔍 Filter Monitoring")
        df_master_cur = st.session_state.df_master.copy()
        def get_options(col): return sorted([str(x) for x in df_master_cur[col].dropna().unique() if str(x).strip() != "" and str(x).lower() != 'nan'])
        
        c1, c2, c3, c4 = st.columns(4)
        f_dept, f_fleet, f_unit, f_stat = c1.multiselect("Dept", get_options('Dept.')), c2.multiselect("Fleet", get_options('Fleet')), c3.multiselect("Unit", get_options('Unit no')), c4.multiselect("Status", get_options('Status'))
        
        # PERBAIKAN: Layout Filter Date Range di sebelah Global Search
        cs1, cs2 = st.columns([2, 1])
        search_q = cs1.text_input("Global Search:", placeholder="Cari...", key="gs_admin")
        
        # LOGIKA FILTER DOC DATE (RANGE)
        with cs2:
            date_range = st.date_input("Filter Doc Date Range:", value=[], placeholder="Pilih rentang tanggal")

        df_f = df_master_cur.copy()
        if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
        if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
        if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
        if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]
        if search_q: df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]
        
        # Eksekusi Filter Tanggal jika range sudah dipilih lengkap (Start & End)
        if isinstance(date_range, list) and len(date_range) == 2:
            try:
                df_f['Doc Date DT'] = pd.to_datetime(df_f['Doc Date'], errors='coerce')
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                df_f = df_f[(df_f['Doc Date DT'] >= start_date) & (df_f['Doc Date DT'] <= end_date)]
                df_f = df_f.drop(columns=['Doc Date DT'])
            except:
                pass

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"].str.contains("Outstanding", case=False)])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"].str.contains("Complete", case=False)])}</h2></div>', unsafe_allow_html=True)

        if not df_f.empty:
            g1, g2, g3 = st.columns(3)
            with g1:
                pic_data = df_f['PIC'].value_counts().reset_index()
                pic_data.columns = ['PIC_Name', 'Count']
                st.plotly_chart(px.bar(pic_data, x='PIC_Name', y='Count', color='PIC_Name', height=350, title="By PIC", text='Count'), use_container_width=True)
            with g2:
                df_pie = df_f.copy()
                def clean_status(s):
                    s = str(s).strip().capitalize()
                    if "Outstanding" in s: return "Outstanding"
                    if "Partial" in s: return "Partial"
                    if "Complete" in s: return "Complete"
                    return s
                df_pie['Clean_Status'] = df_pie['Status'].apply(clean_status)
                st.plotly_chart(px.pie(df_pie, names='Clean_Status', hole=.4, height=350, title="By Status", color='Clean_Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'}), use_container_width=True)
            with g3:
                unit_data = df_f['Unit no'].value_counts().nlargest(5).reset_index()
                unit_data.columns = ['Unit_No', 'Count']
                st.plotly_chart(px.bar(unit_data, x='Unit_No', y='Count', color='Unit_No', height=350, title="Top 5 Units", text='Count'), use_container_width=True)

        st.markdown("---")
        dynamic_height = min(max((len(df_f) + 1) * 35 + 50, 200), 800)
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=dynamic_height)

    with tab_daily:
        st.markdown("### 📅 Daily Update")
        daily_input = st.data_editor(pd.DataFrame(columns=COLUMNS_ORDER), num_rows="dynamic", use_container_width=True, key=f"daily_editor_admin_{st.session_state.daily_key}")
        if st.button("🚀 INSERT & AUTO SAVE"):
            clean_new = daily_input[daily_input['PO No'].astype(str).str.strip() != ""].copy()
            if not clean_new.empty:
                today_str = datetime.now().strftime("%d-%m-%Y")
                clean_new['Status'], clean_new['Last Update'] = "Outstanding", today_str
                new_master = pd.concat([st.session_state.df_master, clean_new], ignore_index=True)
                if save_final_changes(new_master):
                    st.session_state.daily_key += 1
                    show_success_modal("Data Baru Berhasil Masuk Cloud!")

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
        p_height = min(max((len(df_p) + 1) * 35 + 50, 200), 600)
        
        edited_p_df = st.data_editor(df_p[PERSONAL_COLS], use_container_width=True, hide_index=True, height=p_height, key=f"personal_editor_admin", num_rows="fixed", 
            column_config={
                "Dept.": st.column_config.TextColumn("Dept.", disabled=False),
                "Fleet": st.column_config.TextColumn("Fleet", disabled=False),
                "Unit no": st.column_config.TextColumn("Unit no", disabled=False),
                "Last Update": st.column_config.TextColumn("Last Update", disabled=True), 
                "PO No": st.column_config.TextColumn("PO No", disabled=True), 
                "PO Item": st.column_config.TextColumn("PO Item", disabled=True)
            }
        )
        
        if st.button("🚀 CONFIRM REVISION & SAVE TO GSHEET", type="primary"):
            today_str = datetime.now().strftime("%d-%m-%Y")
            master_final = st.session_state.df_master.copy()
            updated_count = 0
            for _, row in edited_p_df.iterrows():
                po_num, po_itm = str(row['PO No']).strip(), str(row['PO Item']).strip()
                mask = (master_final['PO No'] == po_num) & (master_final['PO Item'] == po_itm)
                if mask.any():
                    old_note = str(master_final.loc[mask, 'Delivery Note'].values[0]).strip()
                    new_note = str(row['Delivery Note']).strip()
                    if old_note != new_note:
                        master_final.loc[mask, 'Last Update'] = today_str
                        updated_count += 1
                    for col in PERSONAL_COLS:
                        if col != 'Last Update': master_final.loc[mask, col] = str(row[col])
            if save_final_changes(master_final):
                show_success_modal(f"Berhasil Merevisi {updated_count} baris!")

    with tab_bulk:
        st.markdown("### 🛠️ Update Status")
        input_bulk = st.data_editor(pd.DataFrame(columns=["PO No", "PO Item", "Status", "Delivery Note"]), num_rows="dynamic", use_container_width=True, key=f"bulk_editor_admin_{st.session_state.bulk_key}")
        def execute_bulk_update_final(status_val, note_val):
            today_str = datetime.now().strftime("%d-%m-%Y")
            master_b_update = st.session_state.df_master.copy()
            updated = 0
            for _, r in input_bulk.iterrows():
                p_no, p_item = str(r['PO No']).strip(), str(r['PO Item']).strip()
                mask = (master_b_update['PO No'] == p_no) & (master_b_update['PO Item'] == p_item)
                if mask.any() and p_no != "":
                    master_b_update.loc[mask, ['Status', 'Delivery Note', 'Last Update']] = [status_val, note_val, today_str]
                    updated += 1
            if updated > 0 and save_final_changes(master_b_update):
                st.session_state.bulk_key += 1
                show_success_modal(f"{updated} Data Berhasil Update & Simpan Cloud!")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**🔴 Reset Status**")
            if st.button("Set Outstanding", use_container_width=True): execute_bulk_update_final("Outstanding", "")
        with c2:
            st.write("**🚢 Set Bitung**")
            cb1, cb2 = st.columns(2)
            if cb1.button("Partial", key="bit_p"): execute_bulk_update_final("Partial", "Receive at Bitung")
            if cb2.button("Complete", key="bit_c"): execute_bulk_update_final("Complete", "Receive at Bitung")
        with c3:
            st.write("**⛰️ Set Site**")
            cs1, cs2 = st.columns(2)
            if cs1.button("Partial", key="site_p"): execute_bulk_update_final("Partial", "Receive at Site")
            if cs2.button("Complete", key="site_c"): execute_bulk_update_final("Complete", "Receive at Site")

else:
    # --- VIEWER MODE ---
    st.markdown("### 🔍 Filter Monitoring")
    df_v_master = st.session_state.df_master.copy()
    def get_v_options(col): return sorted([str(x) for x in df_v_master[col].unique() if x])
    
    cv1, cv2, cv3, cv4 = st.columns(4)
    fv_dept, fv_fleet, fv_unit, fv_stat = cv1.multiselect("Dept", get_v_options('Dept.')), cv2.multiselect("Fleet", get_v_options('Fleet')), cv3.multiselect("Unit", get_v_options('Unit no')), cv4.multiselect("Status", get_v_options('Status'))
    
    # Filter Date & Search untuk Viewer
    csv1, csv2 = st.columns([2, 1])
    search_viewer = csv1.text_input("Global Search:", placeholder="Cari...", key="gs_v")
    v_date_range = csv2.date_input("Filter Doc Date Range:", value=[], placeholder="Pilih rentang tanggal", key="date_v")
    
    df_v = df_v_master.copy()
    if fv_dept: df_v = df_v[df_v['Dept.'].isin(fv_dept)]
    if fv_fleet: df_v = df_v[df_v['Fleet'].isin(fv_fleet)]
    if fv_unit: df_v = df_v[df_v['Unit no'].isin(fv_unit)]
    if fv_stat: df_v = df_v[df_v['Status'].isin(fv_stat)]
    if search_viewer: df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search_viewer, case=False).any(), axis=1)]
    
    if isinstance(v_date_range, list) and len(v_date_range) == 2:
        try:
            df_v['Doc Date DT'] = pd.to_datetime(df_v['Doc Date'], errors='coerce')
            df_v = df_v[(df_v['Doc Date DT'] >= pd.to_datetime(v_date_range[0])) & (df_v['Doc Date DT'] <= pd.to_datetime(v_date_range[1]))]
            df_v = df_v.drop(columns=['Doc Date DT'])
        except: pass

    v_height = min(max((len(df_v) + 1) * 35 + 50, 200), 800)
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=v_height, key="viewer_dataframe")
