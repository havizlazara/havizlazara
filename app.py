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
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'PO Item', 'Deliv. Date', 'DDP', 'Supplier', 'Status', 'Delivery Note'])
    
    # Cleaning Nama Kolom
    data.columns = [str(c).strip() for c in data.columns]
    
    # Hapus kolom duplikat secara permanen (terutama PO Item di akhir)
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    # Pastikan Kolom Wajib Status & Delivery Note ada di akhir
    if 'Status' not in data.columns: data['Status'] = "Outstanding"
    if 'Delivery Note' not in data.columns: data['Delivery Note'] = ""
    
    # Format Teks agar tidak muncul .0
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
    .chart-box {{ background-color: white; border: 2px solid #e2e8f0; border-radius: 15px; padding: 10px; }}
    </style>
    <div class="custom-header">
        <div class="logo-container"><img src="data:image/jpeg;base64,{logo_img}" style="height:90px;"></div>
        <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
        <h2 style="color:white; letter-spacing:5px; text-shadow: 2px 2px 4px black;">NHM SUPPLY CHAIN & LOGISTICS</h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. TABS ---
tab_monitor, tab_update = st.tabs(["📊 Dashboard Monitoring", "🛠️ Bulk Update Status"])

# --- TAB MONITORING ---
with tab_monitor:
    st.markdown("### 🔍 Filter & Search")
    search_q = st.text_input("🔎 Search All Columns:", placeholder="Cari Dept, Fleet, PO, dll...")
    
    # PERBAIKAN FILTER: Mengganti PIC menjadi Fleet
    c1, c2, c3, c4 = st.columns(4)
    df_f = st.session_state.df_master.copy()
    
    f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
    if f_dept: df_f = df_f[df_f['Dept.'].isin(f_dept)]
    
    f_fleet = c2.multiselect("Fleet", options=sorted(df_f['Fleet'].unique())) # Sekarang Filter Fleet
    if f_fleet: df_f = df_f[df_f['Fleet'].isin(f_fleet)]
    
    f_unit = c3.multiselect("Unit no", options=sorted(df_f['Unit no'].unique()))
    if f_unit: df_f = df_f[df_f['Unit no'].isin(f_unit)]
    
    f_stat = c4.multiselect("Status", options=sorted(df_f['Status'].unique()))
    if f_stat: df_f = df_f[df_f['Status'].isin(f_stat)]

    if search_q:
        df_f = df_f[df_f.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.markdown(f'<div class="metric-card"><b>TOTAL ITEMS</b><h2>{len(df_f)}</h2></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card" style="border-bottom-color:#ef4444;"><b>OUTSTANDING</b><h2>{len(df_f[df_f["Status"]=="Outstanding"])}</h2></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card" style="border-bottom-color:#22c55e;"><b>COMPLETE</b><h2>{len(df_f[df_f["Status"]=="Complete"])}</h2></div>', unsafe_allow_html=True)

    # Charts Permanen
    if not df_f.empty:
        st.write("")
        g1, g2, g3 = st.columns(3)
        f_white = dict(family="Arial Black", size=14, color="white")
        
        with g1:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            fig1 = px.pie(df_f, names='PIC', hole=.4, height=250, title="Monitoring by PIC")
            fig1.update_traces(textposition='inside', textinfo='percent+label', textfont=f_white)
            fig1.update_layout(showlegend=False, margin=dict(t=35,b=5,l=5,r=5))
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with g2:
            st.markdown('<div class="chart-box">', unsafe_allow_html=True)
            fig2 = px.pie(df_f, names='Status', hole=.4, height=250, title="Monitoring by Status",
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

    # Database
    st.markdown("### 📋 Database Monitoring")
    calc_h = min(max((len(df_f) + 1) * 35 + 45, 250), 800)
    
    if st.session_state['authenticated']:
        df_ed = df_f.copy()
        if 'Pilih' not in df_ed.columns: df_ed.insert(0, 'Pilih', False)
        
        def highlight_row(row):
            c_full = 'background-color: #ff5252; color: white; font-weight: bold;'
            c_po = 'background-color: #b71c1c; color: white; border: 1px solid white;'
            return [c_po if col == 'PO No' else c_full for col in row.index] if row['Pilih'] else [''] * len(row)

        res_ed = st.data_editor(df_ed.style.apply(highlight_row, axis=1), use_container_width=True, hide_index=True, height=calc_h, key="editor_vFixed")
        
        # Action Buttons
        sel_idx = res_ed[res_ed['Pilih'] == True].index
        st.write("🔧 **Quick Actions (Baris Terpilih):**")
        a1, a2, a3, a4 = st.columns([1,1,1,2])
        if a1.button("🔴 Set Outstanding") and not sel_idx.empty:
            st.session_state.df_master.loc[sel_idx, ['Status', 'Delivery Note']] = ["Outstanding", ""]
            st.rerun()
        if a2.button("🟡 Set Partial") and not sel_idx.empty:
            st.session_state.df_master.loc[sel_idx, ['Status', 'Delivery Note']] = ["Partial", "Partial Delivery"]
            st.rerun()
        if a3.button("🟢 Set Complete") and not sel_idx.empty:
            st.session_state.show_complete_options = True
            st.session_state.targets = sel_idx
            st.rerun()
        if a4.button("💾 SAVE TO GSHEET", type="primary"):
            save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_df)
            st.success("Sinkronisasi Berhasil!")

        if st.session_state.show_complete_options:
            st.info("📍 Pilih lokasi untuk status Complete:")
            cb1, cb2 = st.columns(2)
            if cb1.button("Receive on Bitung"):
                st.session_state.df_master.loc[st.session_state.targets, ['Status', 'Delivery Note']] = ["Complete", "Receive on Bitung"]
                st.session_state.show_complete_options = False
                st.rerun()
            if cb2.button("Receive on Site"):
                st.session_state.df_master.loc[st.session_state.targets, ['Status', 'Delivery Note']] = ["Complete", "Receive on Site"]
                st.session_state.show_complete_options = False
                st.rerun()
    else:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=calc_h)

# --- TAB UPDATE ---
with tab_update:
    if st.session_state['authenticated']:
        st.markdown("### 🛠️ Bulk Update via PO No & Item")
        if 'bulk_df' not in st.session_state: st.session_state.bulk_df = pd.DataFrame([{"PO No": "", "PO Item": ""}] * 5)
        bulk_input = st.data_editor(st.session_state.bulk_df, num_rows="dynamic", use_container_width=True)
        
        b1, b2, b3 = st.columns(3)
        clean_in = bulk_input[(bulk_input['PO No'] != "") & (bulk_input['PO Item'] != "")]
        
        def process_bulk(stat, dn):
            for _, r in clean_in.iterrows():
                mask = (st.session_state.df_master['PO No'] == str(r['PO No'])) & (st.session_state.df_master['PO Item'] == str(r['PO Item']))
                st.session_state.df_master.loc[mask, ['Status', 'Delivery Note']] = [stat, dn]
            st.success("Update Selesai! Cek Dashboard & Simpan.")

        if b1.button("Set Outstanding"): process_bulk("Outstanding", "")
        if b2.button("Set Complete (Bitung)"): process_bulk("Complete", "Receive on Bitung")
        if b3.button("Set Complete (Site)"): process_bulk("Complete", "Receive on Site")
    else: st.warning("Silakan Login Admin di Sidebar.")

# --- EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    st.session_state.df_master.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD DATABASE EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")
