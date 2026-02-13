import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    .main .block-container {
        background-color: #ffffff;
        padding: 2rem 3rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    .giant-title { font-size: 60px; font-weight: 900; color: #1f4e79; margin: 0; line-height: 1.1; letter-spacing: -2px; }
    .giant-sub { font-size: 30px; color: #4a5568; margin: 0; font-weight: 600; }
    .stButton>button { width: 100%; background-color: #1f4e79; color: white; border-radius: 8px; font-weight: bold; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    
    if data is None or data.empty:
        # Tambahkan PIC di awal daftar kolom
        cols = ['PIC', 'Fleet', 'Unit no', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'Supplier', 'Status', 'Update Status']
        return pd.DataFrame(columns=cols)
    
    # PEMBERSIHAN TIPE DATA
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    
    if 'Qty' in data.columns:
        data['Qty'] = pd.to_numeric(data['Qty'], errors='coerce').fillna(0).astype(int)
    
    # Pastikan semua kolom teks (termasuk PIC) konsisten sebagai string
    str_cols = ['PIC', 'Fleet', 'Unit no', 'Resv', 'Material', 'Short Text', 'PO No', 'Supplier', 'Status', 'Update Status']
    for col in str_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
            
    return data

try:
    df_master = load_data()
except Exception as e:
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# --- 2. HEADER ---
col_logo, col_text = st.columns([1.2, 5])
with col_logo:
    if os.path.exists("NHM.jpg"): st.image("NHM.jpg", use_container_width=True)

with col_text:
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 150px;">
            <h1 class="giant-title">Dashboard Monitoring Purchase Order NHM</h1>
            <h2 class="giant-sub">Supply Chain & Logistic Departemen</h2>
        </div>
    """, unsafe_allow_html=True)

# --- 3. FILTER & SEARCH ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c1, c2, c3 = st.columns(3)
    
    def get_clean_opts(column_name):
        if column_name in df_master.columns:
            return sorted([x for x in df_master[column_name].unique() if x and x != "nan" and x != ""])
        return []
    
    f_fleet = c1.multiselect("Filter Fleet", options=get_clean_opts("Fleet"))
    f_unit = c2.multiselect("Filter Unit", options=get_clean_opts("Unit no"))
    f_status = c3.multiselect("Filter Status", options=get_clean_opts("Status"))

# Logika Filter
df_display = df_master.copy()
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_display = df_display[df_display["Fleet"].isin(f_fleet)]
if f_unit: df_display = df_display[df_display["Unit no"].isin(f_unit)]
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]

# --- 4. SUMMARY ---
st.markdown(f"""
<div style="display: flex; gap: 10px; margin-bottom: 20px;">
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">TOTAL ITEMS</div>
        <div style="font-size:24px; font-weight:bold; color:#1f4e79;">{len(df_display)}</div>
    </div>
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">OUTSTANDING</div>
        <div style="font-size:24px; font-weight:bold; color:#ef4444;">{len(df_display[df_display['Status'] == 'Outstanding'])}</div>
    </div>
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">COMPLETE</div>
        <div style="font-size:24px; font-weight:bold; color:#22c55e;">{len(df_display[df_display['Status'] == 'Complete'])}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 5. TABEL DATABASE (DENGAN KOLOM PIC) ---
st.markdown("### 📋 Database Monitoring")

edited_data = st.data_editor(
    df_display if (f_fleet or f_unit or f_status or search_query) else df_master,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="editor_pic_v1",
    column_config={
        "PIC": st.column_config.TextColumn("PIC", width="medium"),
        "Unit no": st.column_config.TextColumn("Unit", width="small"),
        "Qty": st.column_config.NumberColumn(width="small", format="%d"),
        "Doc Date": st.column_config.DateColumn("Date", width="medium", format="DD/MM/YYYY"),
        "Status": st.column_config.SelectboxColumn(options=["Complete", "Outstanding", "On Process"], width="medium"),
    }
)

# --- 6. TOMBOL SIMPAN ---
col_save, col_export, _ = st.columns([1.5, 1.5, 4])

if col_save.button("💾 SIMPAN & SYNC KE SEMUA USER"):
    try:
        if f_fleet or f_unit or f_status or search_query:
            df_hidden = df_master[~df_master.index.isin(df_display.index)]
            final_df = pd.concat([df_hidden, edited_data]).reset_index(drop=True)
        else:
            final_df = edited_data

        final_df = final_df.dropna(how='all')
        
        # Simpan ke Google Sheets
        conn.update(data=final_df)
        
        st.cache_data.clear()
        st.success("Data Sinkron dengan Kolom PIC!")
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Menyimpan: {e}")

# --- 7. EXPORT ---
excel_data = io.BytesIO()
with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
    df_display.to_excel(writer, index=False)
col_export.download_button("📊 EXPORT EXCEL", data=excel_data.getvalue(), file_name='NHM_Database.xlsx')