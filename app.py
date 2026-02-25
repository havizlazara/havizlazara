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
if 'bulk_df' not in st.session_state:
    st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": "", "Status": "", "Delivery Note": ""}] * 5)

# Urutan kolom resmi
COLUMNS_ORDER = ['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 'Delivery date', 'DDP', 'Supplier', 'Status', 'Delivery Note']

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
    
    if 'Deliv. Date' in data.columns:
        data = data.drop(columns=['Deliv. Date'])
    if 'Delivery date' not in data.columns:
        data['Delivery date'] = None
        
    # MEMBERSIHKAN DATA & FIX TYPE COMPATIBILITY
    for col in data.columns:
        if 'date' in col.lower() or 'Date' in col:
            # Ubah string ke datetime, lalu ke date object agar kompatibel dengan DateColumn
            data[col] = pd.to_datetime(data[col], errors='coerce').dt.date
        else:
            data[col] = data[col].fillna("").astype(str).str.replace(r'^nan$', '', regex=True).str.replace(r'\.0$', '', regex=True)
            
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

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
            new_row = pd.DataFrame([row])
            st.session_state.daily_df = pd.concat([st.session_state.daily_df, new_row], ignore_index=True)

# --- 3. SIDEBAR (LOGIN) ---
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

# --- 5. LOGIKA FILTER (SINKRON) ---
st.markdown("### 🔍 Filter Monitoring")
df_master_cur = st.session_state.df_master.copy()

def get_options(col_name):
    unique_vals = df_master_cur[col_name].dropna().unique()
    return sorted([str(x) for x in unique_vals if str(x).strip() != "" and str(x).lower() != 'nan'])

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

search_q = st.text_input("Global Search:", placeholder="Ketik untuk mencari...", key="global_search")
if search_q:
    df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

# --- 6. TABS LOGIC ---
if st.session_state['authenticated']:
    tab_monitor, tab_bulk, tab_daily = st.tabs(["📊 DASHBOARD", "🛠️ BULK STATUS", "📅 DAILY UPDATE"])
    
    with tab_monitor:
        # Metrics & Charts
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
                              color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'})
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
        
        # PERBAIKAN TYPE COMPATIBILITY: Pastikan kolom tanggal adalah Date Object sebelum masuk editor
        df_ed = df_f.copy()
        for col in ['Delivery date', 'Doc Date']:
            if col in df_ed.columns:
                df_ed[col] = pd.to_datetime(df_ed[col], errors='coerce').dt.date

        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        edited_table = st.data_editor(
            df_ed, 
            use_container_width=True, 
            hide_index=True, 
            height=calc_h, 
            key="main_editor",
            column_config={
                "Delivery date": st.column_config.DateColumn("Delivery date", format="YYYY-MM-DD"),
                "Doc Date": st.column_config.DateColumn("Doc Date", format="YYYY-MM-DD")
            }
        )
        
        if st.button("💾 SAVE ALL TO GSHEET", type="primary"):
            final_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            # Kembalikan format tanggal ke string sebelum kirim ke GSheets
            for col in ['Delivery date', 'Doc Date']:
                final_save[col] = final_save[col].astype(str).replace("NaT", "").replace("None", "")
            
            conn.update(data=final_save)
            st.cache_data.clear()
            st.success("✅ Berhasil Simpan Permanen!")
            st.rerun()

    with tab_bulk:
        st.markdown("### 🛠️ Bulk Update Status")
        input_bulk = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True, key="bulk_editor", on_change=update_bulk_state)
        b1, b2, b3, b4 = st.columns(4)
        
        def run_bulk(stat=None, dn=None, manual=False):
            updated = 0
            for _, r in st.session_state.bulk_df.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(r['PO No']).strip()) & (st.session_state.df_master['PO Item'] == str(r['PO Item']).strip())
                if mask.any() and str(r['PO No']).strip() != "":
                    st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [stat, dn]
                    updated += 1
            st.success(f"✅ Diperbarui {updated} baris di Memori.")

        if b1.button("🔴 Set Outstanding"): run_bulk("Outstanding", "")
        if b2.button("🟢 Set Bitung"): run_bulk("Complete", "Receive at Bitung")
        if b3.button("🟢 Set Site"): run_bulk("Complete", "Receive at Site")
        if b4.button("📝 Manual Input", type="primary"): run_bulk(manual=True)

    with tab_daily:
        st.markdown("### 📅 Daily Update (Insert Data Baru)")
        st.info("Paste baris baru di sini. Kolom 'Status' otomatis terisi 'Outstanding'.")
        
        # Inisialisasi daily_df di editor sebagai Date Object agar tidak error saat diedit
        df_daily_ready = st.session_state.daily_df.copy()
        for col in ['Delivery date', 'Doc Date']:
            df_daily_ready[col] = pd.to_datetime(df_daily_ready[col], errors='coerce').dt.date

        daily_input = st.data_editor(
            df_daily_ready, 
            num_rows="dynamic", 
            use_container_width=True, 
            key="daily_editor", 
            on_change=update_daily_state,
            column_config={
                "Delivery date": st.column_config.DateColumn("Delivery date", format="YYYY-MM-DD"),
                "Doc Date": st.column_config.DateColumn("Doc Date", format="YYYY-MM-DD")
            }
        )
        
        if st.button("🚀 INSERT NEW DATA TO DASHBOARD", type="primary"):
            clean_new_data = st.session_state.daily_df[st.session_state.daily_df['PO No'].astype(str).str.strip() != ""].copy()
            if not clean_new_data.empty:
                clean_new_data['Status'] = "Outstanding"
                # Konversi kolom tanggal ke string agar seragam dengan database master
                for col in clean_new_data.columns:
                    if 'date' in col.lower() or 'Date' in col:
                        clean_new_data[col] = pd.to_datetime(clean_new_data[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna("")
                    else:
                        clean_new_data[col] = clean_new_data[col].fillna("").astype(str).replace("nan", "")
                
                st.session_state.df_master = pd.concat([st.session_state.df_master, clean_new_data], ignore_index=True)
                st.success(f"✅ Berhasil menambahkan {len(clean_new_data)} baris baru!")
                st.session_state.daily_df = pd.DataFrame(columns=COLUMNS_ORDER)
                st.rerun()

else:
    # --- VIEWER MODE ---
    st.markdown("---")
    st.markdown("### 📋 Database Monitoring (View Only)")
    st.dataframe(df_f, use_container_width=True, hide_index=True, height=600)

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
