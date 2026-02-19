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
if 'selected_rows_indices' not in st.session_state:
    st.session_state['selected_rows_indices'] = []

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Update status', 'PO No'])
    
    # Pastikan kolom Update status tersedia di dataframe
    if 'Update status' not in data.columns:
        data['Update status'] = ""
        
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Update status']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce').dt.date
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_password = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
            if admin_password == "nhm123":
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

# --- 4. CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    .main .block-container {{ background-color: {card_color}; padding: 2rem 3rem; border-radius: 12px; }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 50px; font-weight: 900; color: #1f4e79; text-align: center;
    }}
    .metric-card {{
        background: {card_color}; border-radius: 10px; padding: 15px; text-align: center;
        border-bottom: 5px solid #1f4e79; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="giant-title">Purchase Order Monitoring NHM</h1>', unsafe_allow_html=True)

# --- 5. FILTER ---
search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
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

if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

# --- 6. DATABASE & LOGIKA TOMBOL ACTION ---
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    df_editor = df_filtered.copy()
    if 'Pilih' not in df_editor.columns:
        df_editor.insert(0, 'Pilih', False)

    edited_df = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        column_config={"Pilih": st.column_config.CheckboxColumn("Pilih", default=False)},
        key="editor_pro"
    )

    # Menangkap Index yang dicentang
    selected_indices = edited_df[edited_df['Pilih'] == True].index

    st.write("🔧 **Admin Actions:**")
    a1, a2, a3, a4 = st.columns([1, 1, 1, 3])
    
    # Tombol 1: Outstanding
    if a1.button("🔴 Outstanding", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.session_state.df_master.loc[selected_indices, 'Update status'] = "" # Kosongkan jika belum complete
            st.session_state.show_complete_options = False
            st.rerun()

    # Tombol 2: Partial
    if a2.button("🟡 Partial", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.session_state.df_master.loc[selected_indices, 'Update status'] = "Partial Delivery"
            st.session_state.show_complete_options = False
            st.rerun()

    # Tombol 3: Complete
    if a3.button("🟢 Complete", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.show_complete_options = True
            st.session_state.selected_rows_indices = selected_indices
            st.rerun()

    # Tombol 4: Simpan ke Cloud
    if a4.button("💾 SIMPAN SEMUA KE GOOGLE SHEETS", type="primary", use_container_width=True):
        try:
            save_data = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_data)
            st.cache_data.clear()
            st.success("Data Berhasil Disinkronkan!")
        except Exception as e: st.error(f"Gagal: {e}")

    # --- PILIHAN SETELAH KLIK COMPLETE ---
    if st.session_state.show_complete_options:
        st.info(f"📍 Pilih Lokasi Penerimaan untuk {len(st.session_state.selected_rows_indices)} baris:")
        sub1, sub2, sub3 = st.columns([1.5, 1.5, 4])
        
        if sub1.button("📦 Receive on Bitung", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Update status'] = "Receive on Bitung"
            st.session_state.show_complete_options = False
            st.rerun()
            
        if sub2.button("🚜 Receive on Site", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.selected_rows_indices, 'Update status'] = "Receive on Site"
            st.session_state.show_complete_options = False
            st.rerun()
            
        if sub3.button("❌ Batal", use_container_width=True):
            st.session_state.show_complete_options = False
            st.rerun()

else:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# --- 7. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    df_filtered.to_excel(wr, index=False)
st.download_button("📊 EXPORT EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring.xlsx")