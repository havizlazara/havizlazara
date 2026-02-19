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
        admin_password = st.text_input("Masukkan Password Admin:", type="password")
        if st.button("Login"):
            if admin_password == "nhm123":
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Password Salah")
    else:
        st.success("Mode Admin: Aktif")
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()
    st.divider()
    st.header("🎨 Tampilan")
    bg_color = st.color_picker("Warna Background", "#f1f5f9")
    card_color = st.color_picker("Warna Card", "#ffffff")

# --- 2. FUNGSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Resv', 'Material', 'PO No'])
    
    # Pastikan tipe data konsisten
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
    return data

# Muat data awal ke session state agar bisa dimanipulasi tombol
if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. CUSTOM CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{ background-color: {card_color}; padding: 2rem; border-radius: 12px; }}
    .giant-title {{ font-family: 'serif'; font-size: 40px; font-weight: bold; color: #1f4e79; text-align: center; }}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="giant-title">Purchase Order Monitoring NHM</h1>', unsafe_allow_html=True)

# --- 4. FILTER ---
search_query = st.text_input("🔎 Cari Data:", placeholder="Ketik nomor PO atau PIC...")
df_filtered = st.session_state.df_master.copy()

if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 5. DATABASE DENGAN SELECTION ---
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    st.info("💡 Centang baris di sebelah kiri, lalu klik tombol aksi untuk merubah status.")
    
    # Gunakan dataframe dengan mode seleksi baris
    selection = st.dataframe(
        df_filtered,
        use_container_width=True,
        hide_index=False,
        on_select="rerun",
        selection_mode="multi_row"
    )

    # Ambil indeks baris yang dicentang
    selected_rows = selection.selection.rows
    
    # Tombol Action
    btn_out, btn_part, btn_comp, _ = st.columns([1, 1, 1, 3])
    
    if selected_rows:
        if btn_out.button("🔴 Outstanding", use_container_width=True):
            for row_idx in selected_rows:
                # Ambil nilai asli (karena index di filtered bisa berbeda dengan master)
                actual_idx = df_filtered.index[row_idx]
                st.session_state.df_master.at[actual_idx, 'Status'] = "Outstanding"
            st.success(f"{len(selected_rows)} baris diubah ke Outstanding")
            st.rerun()

        if btn_part.button("🟡 Partial", use_container_width=True):
            for row_idx in selected_rows:
                actual_idx = df_filtered.index[row_idx]
                st.session_state.df_master.at[actual_idx, 'Status'] = "Partial"
            st.success(f"{len(selected_rows)} baris diubah ke Partial")
            st.rerun()

        if btn_comp.button("🟢 Complete", use_container_width=True):
            for row_idx in selected_rows:
                actual_idx = df_filtered.index[row_idx]
                st.session_state.df_master.at[actual_idx, 'Status'] = "Complete"
            st.success(f"{len(selected_rows)} baris diubah ke Complete")
            st.rerun()

    # Tombol Sync ke Google Sheets
    st.divider()
    if st.button("💾 SIMPAN SEMUA PERUBAHAN KE CLOUD", type="primary"):
        try:
            conn.update(data=st.session_state.df_master)
            st.cache_data.clear()
            st.success("Data di Google Sheets Berhasil Diperbarui!")
        except Exception as e:
            st.error(f"Gagal Simpan: {e}")
else:
    # Tampilan untuk Viewer
    st.dataframe(df_filtered, use_container_width=True)

# --- 6. EXPORT ---
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as wr:
    df_filtered.to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=excel_buf.getvalue(), file_name="Monitoring_PO.xlsx")