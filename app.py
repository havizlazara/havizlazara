import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- 1. CUSTOM CSS ---
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
    .giant-title { font-size: 50px; font-weight: 900; color: #1f4e79; margin: 0; line-height: 1.1; letter-spacing: -2px; }
    .giant-sub { font-size: 25px; color: #4a5568; margin: 0; font-weight: 600; }
    .stButton>button { width: 100%; background-color: #1f4e79; color: white; border-radius: 8px; font-weight: bold; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        # Urutan kolom baru: Fleet, Unit no, PIC
        cols = ['Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'Supplier', 'Status', 'Update Status']
        return pd.DataFrame(columns=cols)
    
    # Perbaikan format angka (Menghilangkan .0)
    cols_to_fix = ['Material', 'PO No', 'Resv']
    for col in cols_to_fix:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str)
            data[col] = data[col].replace('0', '')
    
    # Perbaikan format tanggal
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce')
    
    # Standarisasi kolom teks
    str_cols = ['Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status', 'Update Status']
    for col in str_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
            
    return data

try:
    df_master = load_data()
except Exception as e:
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# --- 3. HEADER ---
col_logo, col_text = st.columns([1.2, 5])
with col_logo:
    if os.path.exists("NHM.jpg"): st.image("NHM.jpg", use_container_width=True)

with col_text:
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 150px;">
            <h1 class="giant-title">Dashboard Monitoring Purchase Order NHM</h1>
            <h2 class="giant-sub">Supply Chain & Logistics Departement</h2>
        </div>
    """, unsafe_allow_html=True)

# --- 4. FILTER & SEARCH ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c1, c2, c3 = st.columns(3)
    
    def get_clean_opts(column_name):
        if column_name in df_master.columns:
            return sorted([x for x in df_master[column_name].unique() if x and str(x).lower() != "nan" and str(x).strip() != ""])
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

# --- 5. SUMMARY ---
st.markdown(f"""
<div style="display: flex; gap: 10px; margin-bottom: 20px;">
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center; background:white;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">TOTAL ITEMS</div>
        <div style="font-size:24px; font-weight:bold; color:#1f4e79;">{len(df_display)}</div>
    </div>
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center; background:white;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">OUTSTANDING</div>
        <div style="font-size:24px; font-weight:bold; color:#ef4444;">{len(df_display[df_display['Status'] == 'Outstanding'])}</div>
    </div>
    <div style="flex:1; border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center; background:white;">
        <div style="color:#64748b; font-size:12px; font-weight:bold;">COMPLETE</div>
        <div style="font-size:24px; font-weight:bold; color:#22c55e;">{len(df_display[df_display['Status'] == 'Complete'])}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- 6. TABEL DATABASE (URUTAN: Fleet, Unit no, PIC) ---
st.markdown("### 📋 Database Monitoring")

df_to_edit = df_display if (f_fleet or f_unit or f_status or search_query) else df_master
df_to_edit.index = range(1, len(df_to_edit) + 1)

edited_data = st.data_editor(
    df_to_edit,
    use_container_width=True,
    hide_index=False,
    num_rows="dynamic",
    height=550,
    key="editor_nhm_reorder_v1",
    column_config={
        "Fleet": st.column_config.TextColumn("Fleet", width=120, pinned=True),
        "Unit no": st.column_config.TextColumn("Unit", width=100, pinned=True),
        "PIC": st.column_config.TextColumn("PIC", width=120),
        "Qty": st.column_config.NumberColumn("Qty", width=80, format="%d"),
        "Doc Date": st.column_config.DateColumn("Date", width=150, format="DD/MM/YYYY"),
        "Status": st.column_config.SelectboxColumn("Status", options=["Complete", "Outstanding", "On Process"], width=150),
        "Update Status": st.column_config.TextColumn("Update Status", width=400)
    }
)

# --- 7. TOMBOL SIMPAN ---
col_save, col_export, _ = st.columns([1.5, 1.5, 4])

if col_save.button("💾 SIMPAN & UPDATE LIST"):
    try:
        to_save = edited_data.reset_index(drop=True)
        if f_fleet or f_unit or f_status or search_query:
            df_hidden = df_master[~df_master.index.isin(df_display.index)]
            final_df = pd.concat([df_hidden, to_save]).reset_index(drop=True)
        else:
            final_df = to_save

        final_df = final_df.dropna(how='all')
        
        if 'Doc Date' in final_df.columns:
             final_df['Doc Date'] = pd.to_datetime(final_df['Doc Date']).dt.strftime('%Y-%m-%d').replace('NaT', '')

        conn.update(data=final_df)
        st.cache_data.clear()
        st.success("Berhasil Sinkronisasi!")
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Menyimpan: {e}")

# --- 8. EXPORT ---
excel_data = io.BytesIO()
with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
    df_display.to_excel(writer, index=False)
col_export.download_button("📊 EXPORT EXCEL", data=excel_data.getvalue(), file_name='NHM_Database.xlsx')

st.markdown("<p style='text-align: center; color: #94a3b8; margin-top: 40px; font-size: 14px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</p>", unsafe_allow_html=True)