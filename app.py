import streamlit as st
import pandas as pd
import io
import os

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- CUSTOM CSS: OPTIMASI TABEL FIT LAYAR ---
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    .main .block-container {
        background-color: #ffffff;
        padding: 1.5rem 1.5rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
    }
    div[data-testid="stDataFrame"] td { font-size: 12px; }
    .giant-title { font-size: 55px; font-weight: 900; color: #1f4e79; margin: 0; line-height: 1.1; }
    .giant-sub { font-size: 28px; color: #4a5568; margin: 0; font-weight: 600; }
    .metric-card-custom {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 10px 15px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metric-label-custom { font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; }
    .metric-value-custom { font-size: 24px; font-weight: 800; color: #1f4e79; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. HEADER SEJAJAR ---
col_logo, col_text = st.columns([1, 6])
with col_logo:
    if os.path.exists("NHM.jpg"):
        st.image("NHM.jpg", use_container_width=True)
    else:
        st.write("### [LOGO]")

with col_text:
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%;">
            <h1 class="giant-title">Dashboard Monitoring Purchase Order NHM</h1>
            <h2 class="giant-sub">Supply Chain & Logistic Departemen</h2>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='border: 1px solid #1f4e79; opacity: 0.1; margin: 15px 0;'>", unsafe_allow_html=True)

# --- 2. DATA SETUP ---
if 'master_data' not in st.session_state:
    data = {
        "Fleet": ["Rebuild", "Truck", "W.Loader", "Truck", "Bogger"],
        "Unit": ["Rebuild", "DT028", "LD023", "DT029", "LD005"],
        "Resv": ["443934", "509182", "498222", "510000", "509182"],
        "Material": ["9243689", "9048009", "9037281", "9055555", "9048009"],
        "Description": ["SEAL", "HOSE,NONMTL", "DEHYDRATOR", "FILTER", "HOSE,TRUCK"],
        "Qty": [1, 2, 5, 10, 3],
        "Date": ["2024-09-17", "2025-05-21", "2025-04-02", "2025-06-10", "2025-05-25"],
        "PO No": ["4500043216", "4500046850", "4500046009", "4500047000", "4500046850"],
        "Supplier": ["PT HEXINDO", "PT HEXINDO", "PT UNITED TRACTORS", "PT HEXINDO", "PT HEXINDO"],
        "Status": ["Complete", "Outstanding", "On Process", "Outstanding", "Outstanding"],
        "Remark": ["Avl", "BO Prod", "Ready Enlog", "On Ship", "Stock Jkt"]
    }
    df = pd.DataFrame(data)
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    st.session_state.master_data = df

# --- 3. FILTER & SEARCH ---
c_search, c_f1, c_f2, c_f3 = st.columns([2, 1, 1, 1])
search_query = c_search.text_input("🔎 Search", placeholder="Ketik kata kunci...")
f_fleet = c_f1.multiselect("Fleet", options=sorted(st.session_state.master_data["Fleet"].unique()))
f_unit = c_f2.multiselect("Unit", options=sorted(st.session_state.master_data["Unit"].unique()))
f_status = c_f3.multiselect("Status", options=sorted(st.session_state.master_data["Status"].unique()))

df_filtered = st.session_state.master_data.copy()
if search_query:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_filtered = df_filtered[df_filtered["Fleet"].isin(f_fleet)]
if f_unit: df_filtered = df_filtered[df_filtered["Unit"].isin(f_unit)]
if f_status: df_filtered = df_filtered[df_filtered["Status"].isin(f_status)]

# --- 4. SUMMARY (DYNAMIC) ---
m1, m2, m3 = st.columns(3)
with m1: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Total Items</span><span class='metric-value-custom'>{len(df_filtered)}</span></div>", unsafe_allow_html=True)
with m2: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Outstanding</span><span class='metric-value-custom' style='color: #ef4444;'>{len(df_filtered[df_filtered['Status'] == 'Outstanding'])}</span></div>", unsafe_allow_html=True)
with m3: st.markdown(f"<div class='metric-card-custom'><span class='metric-label-custom'>Complete</span><span class='metric-value-custom' style='color: #22c55e;'>{len(df_filtered[df_filtered['Status'] == 'Complete'])}</span></div>", unsafe_allow_html=True)

# --- 5. TABEL UTAMA ---
st.markdown("### 📋 Database Monitoring")
edited_df = st.data_editor(
    df_filtered,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    key="editor_fit_screen",
    column_config={
        "Fleet": st.column_config.TextColumn(width=80),
        "Unit": st.column_config.TextColumn(width=80),
        "Resv": st.column_config.TextColumn(width=90),
        "Material": st.column_config.TextColumn(width=100),
        "Description": st.column_config.TextColumn(width=180),
        "Qty": st.column_config.NumberColumn(width=50, format="%d"),
        "Date": st.column_config.DateColumn(width=100, format="DD/MM/YY"),
        "PO No": st.column_config.TextColumn(width=110),
        "Supplier": st.column_config.TextColumn(width=130),
        "Status": st.column_config.SelectboxColumn(width=100, options=["Complete", "Outstanding", "On Process"]),
        "Remark": st.column_config.TextColumn(width=130),
    }
)

# --- 6. TOMBOL SIMPAN & EXPORT (DENGAN PERBAIKAN VARIABEL) ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='PO_Summary')
        workbook = writer.book
        worksheet = writer.sheets['PO_Summary']
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#1f4e79', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
    return output.getvalue()

col_save, col_export, _ = st.columns([1, 1, 4])

# Tombol Simpan
if col_save.button("💾 SIMPAN DATA"):
    st.session_state.master_data = edited_df.copy()
    st.success("Data Berhasil Disimpan!")
    st.rerun()

# Tombol Export (Variabel disamakan: excel_data)
excel_data = to_excel(df_filtered)

col_export.download_button(
    label="📊 EXPORT EXCEL",
    data=excel_data,
    file_name='NHM_Monitoring_PO.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 12px; margin-top: 30px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</p>", unsafe_allow_html=True)