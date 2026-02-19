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
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note', 'PO No'])
    
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    if 'Delivery Note' not in data.columns:
        data['Delivery Note'] = ""
    
    if 'Update status' in data.columns:
        data = data.drop(columns=['Update status'])
    
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note']
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
    st.divider()
    bg_color = st.color_picker("Warna Background", "#f1f5f9")
    card_color = st.color_picker("Warna Card", "#ffffff")

# --- 4. CSS & ENKODE GAMBAR HEADER ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg_base64 = get_base64_image("BG2.jpg")
logo_base64 = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{ background-color: {card_color}; padding: 2rem 3rem; border-radius: 12px; }}
    .custom-header {{
        position: relative; width: 100%; min-height: 250px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg_base64}");
        background-size: cover; background-position: center; border: 2px solid #1f4e79;
    }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 50px; font-weight: 900; color: #ffffff !important; 
        background: rgba(31, 78, 121, 0.7); padding: 10px 30px; border-radius: 10px; display: inline-block;
    }}
    .chart-box {{ background-color: {card_color}; border: 2px solid #e2e8f0; border-radius: 15px; padding: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. RENDER HEADER ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" style="height:100px; mix-blend-mode:multiply;">
            <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
            <h2 style="color:white; letter-spacing:5px;">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. FILTER SECTION ---
search_q = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
c1, c2, c3, c4 = st.columns(4)

df_filtered = st.session_state.df_master.copy()
f_dept = c1.multiselect("Dept", options=sorted(st.session_state.df_master['Dept.'].unique()))
if f_dept: df_filtered = df_filtered[df_filtered['Dept.'].isin(f_dept)]
f_fleet = c2.multiselect("Fleet", options=sorted(df_filtered['Fleet'].unique()))
if f_fleet: df_filtered = df_filtered[df_filtered['Fleet'].isin(f_fleet)]
f_unit = c3.multiselect("Unit", options=sorted(df_filtered['Unit no'].unique()))
if f_unit: df_filtered = df_filtered[df_filtered['Unit no'].isin(f_unit)]
f_stat = c4.multiselect("Status", options=sorted(df_filtered['Status'].unique()))
if f_stat: df_filtered = df_filtered[df_filtered['Status'].isin(f_stat)]

if search_q:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

# --- 7. GRAFIK (FORMAT SEBELUMNYA) ---
if not df_filtered.empty:
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        # Pie Chart PIC dengan label Nama di Dalam
        fig1 = px.pie(df_filtered, names='PIC', hole=.4, height=250, title="Monitoring by PIC")
        fig1.update_traces(textposition='inside', textinfo='percent+label')
        fig1.update_layout(margin=dict(t=35,b=5,l=5,r=5), showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        # Pie Chart Status dengan label Nama di Dalam
        fig2 = px.pie(df_filtered, names='Status', hole=.4, height=250, title="Monitoring by Status",
                      color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'})
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(margin=dict(t=35,b=5,l=5,r=5), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with g3:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        # Bar Chart Unit dengan Warna Berbeda (Color-coded by Unit)
        ud = df_filtered['Unit no'].value_counts().nlargest(5).reset_index()
        fig3 = px.bar(ud, x='Unit no', y='count', height=250, title="Top 5 Units", 
                      color='Unit no', color_discrete_sequence=px.colors.qualitative.Bold)
        fig3.update_layout(margin=dict(t=35,b=5,l=5,r=5), showlegend=False, yaxis_visible=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- 8. DATABASE DENGAN HIGHLIGHT MERAH FULL ROW ---
st.markdown("---")
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    df_editor = df_filtered.copy()
    if 'Pilih' not in df_editor.columns:
        df_editor.insert(0, 'Pilih', False)

    # FUNGSI HIGHLIGHT: Warna merah memanjang ke seluruh kolom
    def style_row_red(row):
        style = 'background-color: #ffcdd2; color: #b71c1c; font-weight: bold;'
        return [style] * len(row) if row['Pilih'] else [''] * len(row)

    edited_df = st.data_editor(
        df_editor.style.apply(style_row_red, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
        key="editor_nhm_final_fixed"
    )

    selected_indices = edited_df[edited_df['Pilih'] == True].index

    # ACTION BUTTONS
    st.write("🔧 **Admin Actions:**")
    a1, a2, a3, a4 = st.columns([1, 1, 1, 3])
    
    if a1.button("🔴 Outstanding", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = ""
            st.rerun()

    if a2.button("🟡 Partial", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = "Partial Delivery"
            st.rerun()

    if a3.button("🟢 Complete", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.show_complete_options = True
            st.session_state.target_indices = selected_indices
            st.rerun()

    if a4.button("💾 SIMPAN KE GSHEETS", type="primary", use_container_width=True):
        try:
            save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_df)
            st.cache_data.clear()
            st.success("Tersimpan!")
        except Exception as e: st.error(f"Gagal: {e}")

    # PILIHAN LOKASI
    if st.session_state.show_complete_options:
        st.warning("📍 Update Lokasi Penerimaan:")
        c_opt1, c_opt2, c_opt3 = st.columns([1, 1, 2])
        if c_opt1.button("📦 Bitung", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Bitung"
            st.session_state.show_complete_options = False
            st.rerun()
        if c_opt2.button("🚜 Site", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Site"
            st.session_state.show_complete_options = False
            st.rerun()
        if c_opt3.button("❌ Batal", use_container_width=True):
            st.session_state.show_complete_options = False
            st.rerun()
else:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# --- 9. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    df_filtered.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring_NHM.xlsx")