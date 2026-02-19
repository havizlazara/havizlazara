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
    st.header("🎨 Theme Customizer")
    bg_color = st.color_picker("Warna Background Utama", "#f1f5f9")
    card_color = st.color_picker("Warna Card", "#ffffff")

# --- 2. FUNGSI GAMBAR ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg_base64 = get_base64_image("BG2.jpg")
logo_base64 = get_base64_image("NHM.jpg")

# --- 3. CUSTOM CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{
        background-color: {card_color}; padding: 2rem; max-width: 98%;
        margin: auto; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }}
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Libre+Baskerville:wght@700&display=swap');
    .custom-header {{
        position: relative; width: 100%; min-height: 250px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg_base64}");
        background-size: cover; background-position: center; border: 2px solid #1f4e79;
    }}
    .custom-header::after {{ content: ""; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.1); z-index: 1; }}
    .header-content {{ position: relative; z-index: 2; }}
    .giant-title {{ 
        font-family: 'Libre Baskerville', serif; font-size: 58px; font-weight: 900; 
        color: #ffffff !important; background: rgba(31, 78, 121, 0.7); padding: 10px 30px; 
        border-radius: 10px; display: inline-block; text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
    }}
    .giant-sub {{ 
        font-family: 'Bebas Neue', cursive; font-size: 30px; color: #ffffff !important; 
        letter-spacing: 5px; background: rgba(31, 78, 121, 0.7); padding: 5px 20px; border-radius: 8px;
    }}
    .logo-img-header {{ height: 110px; width: auto; margin-bottom: 20px; mix-blend-mode: multiply; }}
    .metric-card {{
        background: {card_color}; border-radius: 10px; padding: 15px;
        text-align: center; border-bottom: 5px solid #1f4e79; margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    .title-box {{
        background: white; padding: 10px; border-radius: 5px; border: 1px solid #e2e8f0; 
        text-align: center; font-weight: bold; color: #1f4e79; margin-bottom: 15px;
    }}
    .chart-box {{ background-color: {card_color}; border: 2px solid #e2e8f0; border-radius: 15px; padding: 15px; margin-bottom: 20px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Resv', 'Material', 'PO No'])
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    return data

df_master = load_data()

# --- 5. RENDER HEADER ---
st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_base64}" class="logo-img-header">
            <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
            <h2 class="giant-sub">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 6. FILTER ---
search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
c1, c2, c3, c4 = st.columns(4)
filtered = df_master.copy()
f_dept = c1.multiselect("Dept", options=sorted(df_master['Dept.'].unique()))
if f_dept: filtered = filtered[filtered['Dept.'].isin(f_dept)]
f_fleet = c2.multiselect("Fleet", options=sorted(filtered['Fleet'].unique()))
if f_fleet: filtered = filtered[filtered['Fleet'].isin(f_fleet)]
f_unit = c3.multiselect("Unit", options=sorted(filtered['Unit no'].unique()))
if f_unit: filtered = filtered[filtered['Unit no'].isin(f_unit)]
f_stat = c4.multiselect("Status", options=sorted(filtered['Status'].unique()))
if f_stat: filtered = filtered[filtered['Status'].isin(f_stat)]
if search_query:
    filtered = filtered[filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 7. METRICS & 8. GRAFIK (Dihilangkan untuk fokus pada fitur Tabel) ---
# (Bagian Grafik tetap sama seperti sebelumnya)

# --- 9. DATABASE MONITORING DENGAN TOMBOL ACTION ---
st.markdown("### 📋 Database Monitoring")

# Copy data untuk tampilan dengan nomor urut 1
df_vis = filtered.copy().reset_index() # Simpan indeks asli di kolom 'index'
df_vis.index = range(1, len(df_vis) + 1)

if st.session_state['authenticated']:
    # Tombol Action Update Status
    st.write("💡 *Pilih baris pada tabel, lalu klik tombol status di bawah untuk update massal.*")
    
    # Data Editor dengan pemilihan baris
    event = st.data_editor(
        df_vis,
        use_container_width=True,
        hide_index=False,
        num_rows="dynamic",
        key="data_editor",
        on_change=None
    )

    # Logika Tombol Action
    col1, col2, col3, col4 = st.columns([1,1,1,3])
    
    # Mendapatkan baris yang diedit/dipilih
    # Karena data_editor me-return data yang sudah diedit secara manual
    
    if col1.button("🔴 Outstanding", use_container_width=True):
        st.session_state['bulk_status'] = "Outstanding"
    if col2.button("🟡 Partial", use_container_width=True):
        st.session_state['bulk_status'] = "Partial"
    if col3.button("🟢 Complete", use_container_width=True):
        st.session_state['bulk_status'] = "Complete"

    # Tombol Simpan Final
    if col4.button("💾 SIMPAN KE CLOUD", type="primary", use_container_width=True):
        try:
            # Mengambil data dari editor (yang mungkin sudah diubah manual atau dipilih)
            # Karena Streamlit data_editor return datanya langsung
            final_df_to_save = event.drop(columns=['index'], errors='ignore')
            
            # Merge dengan data master
            # Kita gunakan 'index' yang disimpan tadi untuk mereplace baris yang benar di master
            df_master_new = df_master.copy()
            for idx, row in event.iterrows():
                original_idx = row['index']
                df_master_new.iloc[original_idx] = row.drop('index')
            
            conn.update(data=df_master_new)
            st.cache_data.clear()
            st.success("Data Berhasil Disinkronkan!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.dataframe(df_vis.drop(columns=['index'], errors='ignore'), use_container_width=True)
    st.warning("Silakan Login untuk melakukan perubahan status.")

# Export Excel
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    filtered.to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring.xlsx")

st.markdown("<div style='text-align: center; color: #94a3b8; margin-top: 40px;'>PT Nusa Halmahera Minerals | 2026</div>", unsafe_allow_html=True)