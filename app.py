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
    
    .metric-card-custom {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 12px 25px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-label-custom { font-size: 14px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .metric-value-custom { font-size: 28px; font-weight: 800; color: #1f4e79; }
    
    .stButton>button {
        width: 100%;
        background-color: #1f4e79;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        height: 3.5em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Gunakan cache_data agar aplikasi tidak lemot, tapi ttl pendek
@st.cache_data(ttl=5)
def load_data():
    return conn.read(ttl=0)

try:
    # Membaca data master utuh
    df_master = load_data()
except Exception as e:
    st.error("Gagal memuat database. Cek Secrets & Izin Editor Google Sheets.")
    st.stop()

# --- 2. HEADER ---
col_logo, col_text = st.columns([1.2, 5])
with col_logo:
    if os.path.exists("NHM.jpg"):
        st.image("NHM.jpg", use_container_width=True)

with col_text:
    st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 180px;">
            <h1 class="giant-title">Dashboard Monitoring Purchase Order NHM</h1>
            <h2 class="giant-sub">Supply Chain & Logistic Departemen</h2>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border: 1.5px solid #1f4e79; opacity: 0.15; margin-bottom: 25px;'>", unsafe_allow_html=True)

# --- 3. FILTER & SEARCH ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c1, c2, c3 = st.columns(3)
    
    def get_clean_opts(column_name):
        return sorted(df_master[column_name].dropna().astype(str).unique())
    
    f_fleet = c1.multiselect("Filter Fleet", options=get_clean_opts("Fleet"))
    f_unit = c2.multiselect("Filter Unit", options=get_clean_opts("Unit no"))
    f_status = c3.multiselect("Filter Status", options=get_clean_opts("Status"))

# LOGIKA FILTER (Untuk Tampilan Saja)
df_display = df_master.copy()
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_display = df_display[df_display["Fleet"].isin(f_fleet)]
if f_unit: df_display = df_display[df_display["Unit no"].isin(f_unit)]
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]

# --- 4. SUMMARY ---
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Total Filtered</span><span class='metric-value-custom'>{len(df_display)}</span></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Outstanding</span><span class='metric-value-custom' style='color: #ef4444;'>{len(df_display[df_display['Status'] == 'Outstanding'])}</span></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Complete</span><span class='metric-value-custom' style='color: #22c55e;'>{len(df_display[df_display['Status'] == 'Complete'])}</span></div>", unsafe_allow_html=True)

# --- 5. TABEL DATABASE ---
st.markdown("### 📋 Database Monitoring")
# Kita gunakan editor pada df_master agar data yang tidak terfilter tetap terjaga
edited_master = st.data_editor(
    df_master if not (f_fleet or f_unit or f_status or search_query) else df_display,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="realtime_vfinal_safe",
    column_config={
        "Unit no": st.column_config.TextColumn("Unit", width="small"),
        "Doc Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
    }
)

# --- 6. TOMBOL SIMPAN ---
col_save, col_export, _ = st.columns([1.5, 1.5, 4])

if col_save.button("💾 SIMPAN & SYNC KE SEMUA USER"):
    try:
        # LOGIKA PERBAIKAN:
        # Jika user mengedit saat sedang di-filter, kita gabungkan perubahan ke master
        if f_fleet or f_unit or f_status or search_query:
            # Ambil data yang tidak masuk dalam filter display saat ini
            df_not_in_filter = df_master[~df_master.index.isin(df_display.index)]
            # Gabungkan kembali data yang tidak di-filter dengan data hasil edit
            final_to_save = pd.concat([df_not_in_filter, edited_master]).reset_index(drop=True)
        else:
            final_to_save = edited_master

        # Hapus baris yang benar-benar kosong (akibat paste berlebih)
        final_to_save = final_to_save.dropna(how='all')
        
        # Kirim ke Cloud
        conn.update(data=final_to_save)
        
        # Hapus Cache dan Rerun
        st.cache_data.clear()
        st.success("Sinkronisasi Berhasil!")
        st.rerun()
    except Exception as e:
        st.error(f"Gagal Menyimpan: {e}")

# --- 7. EXPORT ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

col_export.download_button(
    label="📊 EXPORT EXCEL",
    data=to_excel(df_display),
    file_name='NHM_Monitoring_PO.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

st.markdown("<p style='text-align: center; color: #94a3b8; margin-top: 40px; font-size: 14px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</p>", unsafe_allow_html=True)