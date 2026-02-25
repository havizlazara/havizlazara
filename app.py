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

# Fungsi Sinkronisasi Bulk Update
def update_bulk_state():
    if "bulk_editor_sync" in st.session_state:
        edits = st.session_state["bulk_editor_sync"]
        for row_idx, values in edits.get("edited_rows", {}).items():
            for key, val in values.items():
                st.session_state.bulk_df.at[int(row_idx), key] = val

# --- 3. SIDEBAR (LOGIN) ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_pw = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
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

# --- 4. CSS CUSTOM (FONT RAKSASA & HEADER) ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg = get_base64_image("BG2.jpg")
logo_img = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    /* Header Background */
    .custom-header {{
        position: relative; width: 100%; min-height: 280px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg}");
        background-size: cover; background-position: center; border: 3px solid #1f4e79;
    }}
    .logo-container {{ background-color: white; padding: 10px; border-radius: 10px; display: inline-block; }}
    .giant-title {{ font-size: 50px; font-weight: 900; color: white !important; background: rgba(31, 78, 121, 0.8); padding: 10px 40px; border-radius: 15px; }}

    /* Judul Tab - Raksasa */
    button[data-baseweb="tab"] div p {{ font-size: 32px !important; font-weight: bold !important; }}
    
    /* Label Filter - Raksasa */
    .stSelectbox label p, .stMultiSelect label p, .stTextInput label p {{
        font-size: 30px !important; font-weight: bold !important; color: #1f4e79 !important;
    }}

    /* JUDUL KOLOM TABEL - RAKSASA (2x Lebih Besar) */
    [data-testid="stTableColumnHeaderCell"] div {{
        font-size: 32px !important; /* Ukuran font judul kolom ditingkatkan signifikan */
        font-weight: 900 !important;
        color: #1f4e79 !important;
        padding: 10px 0px !important;
    }}
    
    .metric-card {{ background: white; border-radius: 10px; padding: 15px; text-align: center; border-bottom: 5px solid #1f4e79; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    .chart-box {{ background-color: white; border: 2px solid #e2e8f0; border-radius: 15px; padding: 10px; }}
    .stApp {{ background-color: #f1f5f9; }}
    </style>
    """, unsafe_allow_html=True)

# Render Header
st.markdown(f"""
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" style="height:100px;"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
        <h2 style="color:white; font-size: 25px; letter-spacing:5px; text-shadow: 2px 2px 4px black;">NHM SUPPLY CHAIN & LOGISTICS</h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. TABS ---
if st.session_state['authenticated']:
    tab_monitor, tab_update = st.tabs(["📊 DASHBOARD MONITORING", "🛠️ BULK UPDATE STATUS"])
    
    # --- TAB MONITORING (LOGIN ONLY) ---
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

        search_q = st.text_input("Global Search:", placeholder="Ketik di sini...")
        if search_q:
            df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

        # METRICS & CHARTS (Dimasukkan ke dalam blok Login)
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

        if not df_f.empty:
            st.write("")
            g1, g2, g3 = st.columns(3)
            f_white = dict(family="Arial Black", size=14, color="white")
            with g1:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                fig1 = px.pie(df_f, names='PIC', hole=.4, height=250, title="By PIC")
                fig1.update_traces(textposition='inside', textinfo='percent+label', textfont=f_white)
                fig1.update_layout(showlegend=False, margin=dict(t=35,b=5,l=5,r=5))
                st.plotly_chart(fig1, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g2:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                fig2 = px.pie(df_f, names='Status', hole=.4, height=250, title="By Status",
                              color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'})
                fig2.update_traces(textposition='inside', textinfo='percent+label', textfont=f_white)
                fig2.update_layout(showlegend=False, margin=dict(t=35,b=5,l=5,r=5))
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with g3:
                st.markdown('<div class="chart-box">', unsafe_allow_html=True)
                ud = df_f['Unit no'].value_counts().nlargest(5).reset_index()
                fig3 = px.bar(ud, x='Unit no', y='count', height=250, title="Top 5 Units", color='Unit no')
                fig3.update_traces(texttemplate='%{y}', textfont=f_white, textposition='inside')
                fig3.update_layout(showlegend=False, yaxis_visible=False, margin=dict(t=35,b=5,l=5,r=5))
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Database Monitoring")
        calc_h = min(max((len(df_f) + 1) * 35 + 100, 250), 800)
        
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        def apply_style(row):
            c_f = 'background-color: #ff5252; color: white; font-weight: bold;'
            c_p = 'background-color: #b71c1c; color: white; border: 1px solid white;'
            return [c_p if col == 'PO No' else c_f for col in row.index] if row['Pilih'] else [''] * len(row)

        edited_table = st.data_editor(df_ed.style.apply(apply_style, axis=1), use_container_width=True, hide_index=True, height=calc_h, key="main_editor_vFinal")
        
        if st.button("💾 SAVE TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=final_save)
            st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": "", "Status": "", "Delivery Note": ""}] * 5)
            st.cache_data.clear()
            st.success("✅ Berhasil Simpan & Reset!")
            st.rerun()

    # --- TAB UPDATE (LOGIN ONLY) ---
    with tab_update:
        st.markdown("### 🛠️ Bulk Update Status")
        input_bulk = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key="bulk_editor_sync", on_change=update_bulk_state)
        
        b1, b2, b3, b_manual = st.columns(4)
        clean_in = st.session_state.bulk_df[(st.session_state.bulk_df['PO No'].str.strip() != "") & (st.session_state.bulk_df['PO Item'].str.strip() != "")]
        
        def run_sync(stat=None, dn=None, manual=False):
            updated = 0
            new_view = st.session_state.bulk_df.copy()
            for idx, r in clean_in.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(r['PO No']).strip()) & (st.session_state.df_master['PO Item'] == str(r['PO Item']).strip())
                if mask.any():
                    t_stat = str(r['Status']) if manual else stat
                    t_dn = str(r['Delivery Note']) if manual else dn
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [t_stat, t_dn]
                    new_view.loc[idx, ['Status', 'Delivery Note']] = [t_stat, t_dn]
                    updated += 1
            st.session_state.bulk_df = new_view
            if updated > 0: st.success(f"✅ Berhasil update {updated} baris!")
            st.rerun()

        if b1.button("🔴 Bulk Outstanding"): run_sync("Outstanding", "")
        if b2.button("🟢 Bulk Bitung"): run_sync("Complete", "Receive at Bitung")
        if b3.button("🟢 Bulk Site"): run_sync("Complete", "Receive at Site")
        if b_manual.button("📝 Apply Manual Input", type="primary"): run_sync(manual=True)

else:
    # Tampilan Viewer (Hanya Tabel)
    st.markdown("### 🔍 Database Monitoring (View Only)")
    st.dataframe(st.session_state.df_master, use_container_width=True, hide_index=True, height=600)

# --- 9. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
