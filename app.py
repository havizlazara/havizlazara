import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
import plotly.graph_objects as go
import base64

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- 1. SISTEM LOGIN & LOGOUT ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_password = st.text_input("Password:", type="password")
        if st.button("Login"):
            if admin_password == "nhm123":
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("Salah")
    else:
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Resv', 'Material', 'PO No'])
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
    return data

# Inisialisasi Master Data di Session State
if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. FILTER ---
st.markdown("### 🔍 Filter Monitoring")
search_query = st.text_input("Cari Global:", placeholder="Ketik sesuatu...")
df_filtered = st.session_state.df_master.copy()

if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 4. DATABASE MONITORING ---
st.markdown("---")
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    st.info("💡 Klik kolom 'Status' untuk mengubah secara manual, atau gunakan tombol di bawah.")
    
    # MENGGUNAKAN DATA EDITOR (Lebih Kompatibel)
    # Kita tambahkan kolom checkbox buatan (Pilih)
    if 'temp_df' not in st.session_state or st.sidebar.button("Reset Pilihan"):
        df_filtered['Pilih'] = False
        st.session_state.temp_df = df_filtered

    # Tampilkan Editor
    edited_df = st.data_editor(
        st.session_state.temp_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False),
            "Status": st.column_config.SelectboxColumn("Status", options=["Outstanding", "Partial", "Complete"])
        },
        key="main_editor"
    )

    # Tombol Aksi Massal
    c1, c2, c3, _ = st.columns([1,1,1,3])
    
    # Cek baris mana yang dicentang di kolom 'Pilih'
    rows_to_update = edited_df[edited_df['Pilih'] == True].index

    if not rows_to_update.empty:
        if c1.button("🔴 Outstanding All"):
            st.session_state.df_master.loc[rows_to_update, 'Status'] = "Outstanding"
            st.cache_data.clear()
            st.rerun()
        if c2.button("🟡 Partial All"):
            st.session_state.df_master.loc[rows_to_update, 'Status'] = "Partial"
            st.cache_data.clear()
            st.rerun()
        if c3.button("🟢 Complete All"):
            st.session_state.df_master.loc[rows_to_update, 'Status'] = "Complete"
            st.cache_data.clear()
            st.rerun()

    # Simpan Cloud
    st.divider()
    if st.button("💾 SIMPAN SEMUA KE GOOGLE SHEETS", type="primary"):
        try:
            # Hapus kolom 'Pilih' sebelum simpan
            data_to_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=data_to_save)
            st.success("Tersimpan di Cloud!")
            st.cache_data.clear()
        except Exception as e: st.error(f"Gagal: {e}")
else:
    st.dataframe(df_filtered.drop(columns=['Pilih'], errors='ignore'), use_container_width=True)

# --- 5. EXPORT ---
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as wr:
    df_filtered.drop(columns=['Pilih'], errors='ignore').to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=excel_buf.getvalue(), file_name="PO_Monitoring.xlsx")