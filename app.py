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
        st.success("Mode Admin Aktif")
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

# Inisialisasi Master Data
if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. FILTER ---
st.markdown("### 🔍 Filter Monitoring")
search_query = st.text_input("Cari Global:", placeholder="Ketik sesuatu...")

# Buat dataframe sementara untuk difilter
df_filtered = st.session_state.df_master.copy()
if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 4. DATABASE MONITORING ---
st.markdown("---")
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    st.info("💡 Centang kolom **'Pilih'**, lalu klik tombol status di bawah untuk update massal.")
    
    # Tambahkan kolom checkbox 'Pilih' secara dinamis
    if 'Pilih' not in df_filtered.columns:
        df_filtered.insert(0, 'Pilih', False)

    # Tampilkan Data Editor
    edited_df = st.data_editor(
        df_filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False),
            "Status": st.column_config.SelectboxColumn("Status", options=["Outstanding", "Partial", "Complete"])
        },
        key="editor_nhm"
    )

    # --- TOMBOL ACTION STATUS ---
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    
    # Identifikasi baris mana yang dicentang
    selected_indices = edited_df[edited_df['Pilih'] == True].index

    if c1.button("🔴 Outstanding", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.success(f"Berhasil mengubah {len(selected_indices)} baris")
            st.rerun()
        else: st.warning("Pilih baris dulu!")

    if c2.button("🟡 Partial", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.success(f"Berhasil mengubah {len(selected_indices)} baris")
            st.rerun()
        else: st.warning("Pilih baris dulu!")

    if c3.button("🟢 Complete", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Complete"
            st.success(f"Berhasil mengubah {len(selected_indices)} baris")
            st.rerun()
        else: st.warning("Pilih baris dulu!")

    # Tombol Simpan Final
    if c4.button("💾 SIMPAN KE GOOGLE SHEETS", type="primary", use_container_width=True):
        try:
            # Hapus kolom 'Pilih' sebelum dikirim ke Google Sheets
            data_to_save = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=data_to_save)
            st.cache_data.clear()
            st.success("Sinkronisasi Berhasil!")
        except Exception as e: st.error(f"Gagal: {e}")

else:
    # Tampilan Viewer Tanpa Checkbox
    st.dataframe(df_filtered.drop(columns=['Pilih'], errors='ignore'), use_container_width=True)
    st.warning("Gunakan sidebar untuk Login.")

# --- 5. EXPORT ---
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as wr:
    df_filtered.drop(columns=['Pilih'], errors='ignore').to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=excel_buf.getvalue(), file_name="PO_Monitoring.xlsx")