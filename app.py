import streamlit as st
import pandas as pd
import io
import os

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- CUSTOM CSS: HEADER SEJAJAR & OPTIMASI TABEL ---
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    
    /* Memaksimalkan lebar layar agar Fit */
    .main .block-container {
        background-color: #ffffff;
        padding: 1.5rem 2rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    
    /* Ukuran Font Judul Raksasa */
    .giant-title { 
        font-size: 70px; 
        font-weight: 900; 
        color: #1f4e79; 
        margin: 0; 
        line-height: 1.1; 
        letter-spacing: -2px; 
    }
    .giant-sub { 
        font-size: 35px; 
        color: #4a5568; 
        margin: 0; 
        font-weight: 600; 
    }
    
    /* Card Summary Ramping */
    .metric-card-custom {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 10px 20px;
        border-radius: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label-custom { font-size: 14px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .metric-value-custom { font-size: 28px; font-weight: 800; color: #1f4e79; }
    
    /* Tombol */
    .stButton>button {
        width: 100%;
        background-color: #1f4e79;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. HEADER SEJAJAR (LOGO & JUDUL) ---
col_logo, col_text = st.columns([1.2, 5])
with col_logo:
    if os.path.exists("NHM.jpg"):
        st.image("NHM.jpg", use_container_width=True)
    else:
        st.write("### [LOGO NHM]")

with col_text:
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; min-height: 180px;">
            <h1 class="giant-title">Dashboard Monitoring Purchase Order NHM</h1>
            <h2 class="giant-sub">Supply Chain & Logistic Departemen</h2>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border: 1.5px solid #1f4e79; opacity: 0.15; margin-bottom: 25px;'>", unsafe_allow_html=True)

# --- 2. SETUP DATA ---
if 'master_data' not in st.session_state:
    data = {
        "Fleet": ["Rebuild", "Truck", "Wheel Loader", "Truck", "Bogger"],
        "Unit no": ["Rebuild", "DT028", "LD023", "DT029", "LD005"],
        "Resv": ["443934", "509182", "498222", "510000", "509182"],
        "Material": ["9243689", "9048009", "9037281", "9055555", "9048009"],
        "Short Text": ["SEAL", "HOSE,NONMTL", "DEHYDRATOR", "FILTER", "HOSE,TRUCK"],
        "Qty": [1, 2, 5, 10, 3],
        "Doc Date": ["2024-09-17", "2025-05-21", "2025-04-02", "2025-06-10", "2025-05-25"],
        "PO No": ["4500043216", "4500046850", "4500046009", "4500047000", "4500046850"],
        "Supplier": ["PT HEXINDO", "PT HEXINDO", "PT UNITED TRACTORS", "PT HEXINDO", "PT HEXINDO"],
        "Status": ["Complete", "Outstanding", "On Process", "Outstanding", "Outstanding"],
        "Update Status": ["Avl", "BO Produksi", "Ready At Enlog", "On Shipment", "Stock Jakarta"]
    }
    df = pd.DataFrame(data)
    df["Doc Date"] = pd.to_datetime(df["Doc Date"]).dt.date
    st.session_state.master_data = df

# --- 3. FILTER & SEARCH ---
with st.container():
    search_query = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
    c1, c2, c3 = st.columns(3)
    
    def get_opts(column_name):
        return sorted(st.session_state.master_data[column_name].fillna("(blank)").astype(str).unique())
    
    f_fleet = c1.multiselect("Filter Fleet", options=get_opts("Fleet"))
    f_unit = c2.multiselect("Filter Unit", options=get_opts("Unit no"))
    f_status = c3.multiselect("Filter Status", options=get_opts("Status"))

# LOGIKA FILTER
df_filtered = st.session_state.master_data.copy()
if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_filtered = df_filtered[df_filtered["Fleet"].isin(f_fleet)]
if f_unit: df_filtered = df_filtered[df_filtered["Unit no"].isin(f_unit)]
if f_status: df_filtered = df_filtered[df_filtered["Status"].isin(f_status)]

# --- 4. SUMMARY (DYNAMIC BASED ON FILTER) ---
st.write("### 📊 Summary Filtered Data")
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Total Items</span><span class='metric-value-custom'>{len(df_filtered)}</span></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Outstanding</span><span class='metric-value-custom' style='color: #ef4444;'>{len(df_filtered[df_filtered['Status'] == 'Outstanding'])}</span></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Complete</span><span class='metric-value-custom' style='color: #22c55e;'>{len(df_filtered[df_filtered['Status'] == 'Complete'])}</span></div>", unsafe_allow_html=True)

st.write("")

# --- 5. TABEL DATABASE (FIT TO SCREEN) ---
st.markdown("### 📋 Monitoring Database")
edited_df = st.data_editor(
    df_filtered,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="editor_nhm_final",
    column_config={
        "Fleet": st.column_config.TextColumn(width="small"),
        "Unit no": st.column_config.TextColumn("Unit", width="small"),
        "Resv": st.column_config.TextColumn(width="small"),
        "Material": st.column_config.TextColumn(width="medium"),
        "Short Text": st.column_config.TextColumn("Description", width="large"),
        "Qty": st.column_config.NumberColumn(width="small", format="%d"),
        "Doc Date": st.column_config.DateColumn("Date", width="small", format="DD/MM/YYYY"),
        "PO No": st.column_config.TextColumn(width="medium"),
        "Supplier": st.column_config.TextColumn(width="medium"),
        "Status": st.column_config.SelectboxColumn(width="small", options=["Complete", "Outstanding", "On Process"]),
        "Update Status": st.column_config.TextColumn("Remark", width="medium"),
    }
)

# --- 6. BUTTONS SIMPAN & EXCEL ---
col_save, col_export, _ = st.columns([1.5, 1.5, 4])

if col_save.button("💾 SIMPAN DATA"):
    # Update data utama dengan hasil editan
    st.session_state.master_data = edited_df.copy()
    st.success("Data Berhasil Diperbarui!")
    st.rerun()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='PO_Summary')
    return output.getvalue()

excel_data = to_excel(df_filtered)

col_export.download_button(
    label="📊 EXPORT EXCEL",
    data=excel_data,
    file_name='Monitoring_PO_NHM.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

st.markdown("<p style='text-align: center; color: #94a3b8; margin-top: 40px; font-size: 14px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</p>", unsafe_allow_html=True)