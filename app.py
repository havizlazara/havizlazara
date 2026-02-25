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

def update_bulk_state():
    if "bulk_editor_sync" in st.session_state:
        edits = st.session_state["bulk_editor_sync"]
        for row_idx, values in edits.get("edited_rows", {}).items():
            for key, val in values.items():
                st.session_state.bulk_df.at[int(row_idx), key] = val

# --- 3. SIDEBAR (LOGIN DENGAN FITUR ENTER) ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        # Menggunakan FORM agar bisa ENTER untuk Login
        with st.form("login_form"):
            admin_pw = st.text_input("Password Admin:", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if admin_pw == "nhm123":
                    st.session_state['authenticated'] = True
                    st.session_state.df_master = load_data()
                    st.rerun()
                else: 
                    st.error("Password Salah")
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

    [data-testid="stTableColumnHeaderCell"] div {{
        font-size: 40px !important; 
        font-weight: 900 !important;
        color: #1f4e79 !important;
        padding: 15px 0px !important;
    }}
    
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
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

# --- 5. LOGIKA TAB & FILTER (SINKRON UNTUK SEMUA) ---
if st.session_state['authenticated']:
    tab_monitor, tab_update = st.tabs(["📊 DASHBOARD MONITORING", "🛠️ BULK UPDATE STATUS"])
    
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

        search_q = st.text_input("Global Search:", placeholder="Ketik untuk mencari...")
        if search_q:
            df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

        # METRICS & CHARTS
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
                pic_counts = df_f['PIC'].value_counts().reset_index()
                pic_counts.columns = ['PIC', 'count']
                fig1 = px.bar(pic_counts, x='PIC', y='count', color='PIC', height=380, title="Monitoring by PIC", text='count')
                fig1.update_traces(textposition='auto', textfont=dict(size=14, color='white', family="Arial Black"))
                st.plotly_chart(fig1, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g2:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                fig2 = px.pie(df_f, names='Status', hole=.4, height=380, title="By Status",
                              color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'})
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g3:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                ud = df_f['Unit no'].value_counts().nlargest(5).reset_index()
                fig3 = px.bar(ud, x='Unit no', y='count', height=380, title="Top 5 Units", color='Unit no')
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        calc_h = min(max((len(df_f) + 1) * 35 + 100, 250), 800)
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        def apply_style(row):
            return ['background-color: #ff5252; color: white; font-weight: bold;'] * len(row) if row['Pilih'] else [''] * len(row)

        edited_table = st.data_editor(df_ed.style.apply(apply_style, axis=1), use_container_width=True, hide_index=True, height=calc_h, key="main_editor")
        
        if st.button("💾 SAVE TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("✅ Berhasil Simpan!")
            st.rerun()

    with tab_update:
        st.markdown("### 🛠️ Bulk Update Status")
        input_bulk = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key="bulk_editor", on_change=update_bulk_state)
        b1, b2, b3, b_manual = st.columns(4)
        
        def run_sync(stat=None, dn=None, manual=False):
            updated = 0
            clean_in = st.session_state.bulk_df[(st.session_state.bulk_df['PO No'].str.strip() != "")]
            for idx, r in clean_in.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(r['PO No']).strip())
                if mask.any():
                    t_stat = str(r['Status']) if manual else stat
                    t_dn = str(r['Delivery Note']) if manual else dn
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [t_stat, t_dn]
                    updated += 1
            if updated > 0: st.success(f"✅ Berhasil update {updated} baris!")
            st.rerun()

        if b1.button("🔴 Bulk Outstanding"): run_sync("Outstanding", "")
        if b2.button("🟢 Bulk Bitung"): run_sync("Complete", "Receive at Bitung")
        if b3.button("🟢 Bulk Site"): run_sync("Complete", "Receive at Site")
        if b_manual.button("📝 Apply Manual Input", type="primary"): run_sync(manual=True)

else:
    # --- TAMPILAN VIEWER (FILTER LENGKAP) ---
    st.markdown("### 🔍 Filter Monitoring (Viewer)")
    df_v = st.session_state.df_master.copy()
    cv1, cv2, cv3, cv4 = st.columns(4)
    
    fv_dept = cv1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()), key="v_dept")
    if fv_dept: df_v = df_v[df_v['Dept.'].isin(fv_dept)]
    
    fv_fleet = cv2.multiselect("Fleet", options=sorted(df_v['Fleet'].unique()), key="v_fleet")
    if fv_fleet: df_v = df_v[df_v['Fleet'].isin(fv_fleet)]
    
    fv_unit = cv3.multiselect("Unit", options=sorted(df_v['Unit no'].unique()), key="v_unit")
    if fv_unit: df_v = df_v[df_v['Unit no'].isin(fv_unit)]
    
    fv_stat = cv4.multiselect("Status", options=sorted(df_v['Status'].unique()), key="v_stat")
    if fv_stat: df_v = df_v[df_v['Status'].isin(fv_stat)]
    
    search_viewer = st.text_input("Search:", placeholder="Ketik untuk mencari...", key="v_search")
    if search_viewer:
        df_v = df_v[df_v.apply(lambda r: r.astype(str).str.contains(search_viewer, case=False).any(), axis=1)]
    
    st.markdown("---")
    st.markdown("### 📋 Database Monitoring (View Only)")
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=600)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
