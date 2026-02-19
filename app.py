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
    
    # Bersihkan kolom teks
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

# --- 4. CSS CUSTOM (Highlight Merah) ---
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    .custom-header {
        background-color: #1f4e79; padding: 40px; border-radius: 15px;
        text-align: center; color: white; margin-bottom: 20px;
    }
    .giant-title { font-size: 40px; font-weight: 900; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. HEADER ---
st.markdown("""
    <div class="custom-header">
        <h1 class="giant-title">Purchase Order Monitoring</h1>
        <h3 style="letter-spacing:3px;">NHM SUPPLY CHAIN & LOGISTICS</h3>
    </div>
    """, unsafe_allow_html=True)

# --- 6. FILTER ---
search_q = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
df_filtered = st.session_state.df_master.copy()

c1, c2, c3 = st.columns(3)
f_dept = c1.multiselect("Dept", options=sorted(df_filtered['Dept.'].unique()))
if f_dept: df_filtered = df_filtered[df_filtered['Dept.'].isin(f_dept)]
f_unit = c2.multiselect("Unit", options=sorted(df_filtered['Unit no'].unique()))
if f_unit: df_filtered = df_filtered[df_filtered['Unit no'].isin(f_unit)]
f_stat = c3.multiselect("Status", options=sorted(df_filtered['Status'].unique()))
if f_stat: df_filtered = df_filtered[df_filtered['Status'].isin(f_stat)]

if search_q:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

# --- 7. CHARTS ---
if not df_filtered.empty:
    g1, g2 = st.columns(2)
    with g1:
        fig1 = px.pie(df_filtered, names='Status', hole=.4, title="Status Distribution")
        st.plotly_chart(fig1, use_container_width=True)
    with g2:
        ud = df_filtered['Unit no'].value_counts().nlargest(5).reset_index()
        fig2 = px.bar(ud, x='Unit no', y='count', title="Top 5 Units")
        st.plotly_chart(fig2, use_container_width=True)

# --- 8. DATABASE DENGAN HIGHLIGHT MERAH ---
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    # Tambah kolom Pilih di awal
    df_editor = df_filtered.copy()
    if 'Pilih' not in df_editor.columns:
        df_editor.insert(0, 'Pilih', False)

    # FUNGSI HIGHLIGHT: Mewarnai 1 baris full jika kolom 'Pilih' dicentang
    def style_row(row):
        return ['background-color: #ffcdd2; color: #b71c1c; font-weight: bold' if row['Pilih'] else '' for _ in row]

    # Menggunakan editor dengan styling yang kompatibel
    edited_df = st.data_editor(
        df_editor.style.apply(style_row, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False),
        },
        key="main_editor_v1"
    )

    # Identifikasi baris terpilih
    selected_indices = edited_df[edited_df['Pilih'] == True].index

    # ACTION BUTTONS
    st.write("🔧 **Actions:**")
    a1, a2, a3, a4 = st.columns([1,1,1,2])
    
    if a1.button("🔴 Outstanding"):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = ""
            st.rerun()

    if a2.button("🟡 Partial"):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = "Partial Delivery"
            st.rerun()

    if a3.button("🟢 Complete"):
        if not selected_indices.empty:
            st.session_state.show_complete_options = True
            st.session_state.target_indices = selected_indices
            st.rerun()

    if a4.button("💾 SAVE TO GSHEET", type="primary"):
        save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
        conn.update(data=save_df)
        st.success("Tersimpan!")

    if st.session_state.show_complete_options:
        st.warning("Pilih lokasi untuk status Complete:")
        c1, c2 = st.columns(2)
        if c1.button("Bitung"):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Bitung"
            st.session_state.show_complete_options = False
            st.rerun()
        if c2.button("Site"):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Site"
            st.session_state.show_complete_options = False
            st.rerun()
else:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)