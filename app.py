import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import os
import plotly.express as px
import plotly.graph_objects as go

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring PO NHM", layout="wide")

# --- 1. CUSTOM CSS (MODERN DESIGN) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main .block-container {
        background-color: #ffffff;
        padding: 2rem 3rem; 
        max-width: 98%;
        margin: auto;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.03);
    }
    .giant-title { 
        font-size: 45px; 
        font-weight: 800; 
        background: -webkit-linear-gradient(#1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .giant-sub { font-size: 20px; color: #64748b; margin-top: 0; font-weight: 500; letter-spacing: 1px; }
    
    /* Styling Card Summary */
    .metric-card {
        background: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-left: 5px solid #1e3a8a;
        transition: transform 0.3s;
    }
    .metric-card:hover { transform: translateY(-5px); }
    
    .stButton>button { 
        width: 100%; 
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white; 
        border-radius: 12px; 
        font-weight: 600; 
        height: 3.5em;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. KONEKSI DATA DENGAN CACHE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data():
    data = conn.read(ttl=0) 
    if data is None or data.empty:
        cols = ['Fleet', 'Unit no', 'PIC', 'Resv', 'Material', 'Short Text', 'Qty', 'Doc Date', 'PO No', 'Supplier', 'Status', 'Update Status']
        return pd.DataFrame(columns=cols)
    
    # Cleaning format angka
    cols_to_fix = ['Material', 'PO No', 'Resv']
    for col in cols_to_fix:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0).astype(int).astype(str)
            data[col] = data[col].replace('0', '')
    
    if 'Doc Date' in data.columns:
        data['Doc Date'] = pd.to_datetime(data['Doc Date'], errors='coerce')
    
    str_cols = ['Fleet', 'Unit no', 'PIC', 'Short Text', 'Supplier', 'Status', 'Update Status']
    for col in str_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
    return data

def refresh_all_data():
    st.cache_data.clear()

try:
    df_master = load_data()
except Exception as e:
    st.error(f"Koneksi Gagal: {e}")
    st.stop()

# --- 3. HEADER ---
col_logo, col_text = st.columns([1, 5])
with col_logo:
    if os.path.exists("NHM.jpg"): st.image("NHM.jpg", width=120)

with col_text:
    st.markdown('<h1 class="giant-title">PO Monitoring Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="giant-sub">NUSA HALMAHERA MINERALS | SCM LOGISTICS</p>', unsafe_allow_html=True)

st.divider()

# --- 4. FILTER ---
with st.expander("🔍 Filter & Advanced Search", expanded=True):
    search_query = st.text_input("Global Search", placeholder="Cari PIC, PO, atau Fleet...")
    c1, c2, c3 = st.columns(3)
    def get_opts(col):
        return sorted([x for x in df_master[col].unique() if x and str(x) != "nan"]) if col in df_master.columns else []
    
    f_fleet = c1.multiselect("Fleet", options=get_opts("Fleet"))
    f_unit = c2.multiselect("Unit", options=get_opts("Unit no"))
    f_status = c3.multiselect("Status", options=get_opts("Status"))

df_display = df_master.copy()
if search_query:
    df_display = df_display[df_display.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
if f_fleet: df_display = df_display[df_display["Fleet"].isin(f_fleet)]
if f_unit: df_display = df_display[df_display["Unit no"].isin(f_unit)]
if f_status: df_display = df_display[df_display["Status"].isin(f_status)]

# --- 5. VISUALISASI MODERN ---
st.markdown("### 📈 Analytics Overview")
m1, m2, m3 = st.columns(3)
metrics = [
    ("TOTAL ITEMS", len(df_display), "#1e3a8a"),
    ("OUTSTANDING", len(df_display[df_display['Status'] == 'Outstanding']), "#ef4444"),
    ("COMPLETE", len(df_display[df_display['Status'] == 'Complete']), "#22c55e")
]

for col, (label, val, color) in zip([m1, m2, m3], metrics):
    col.markdown(f"""
        <div class="metric-card" style="border-left-color: {color};">
            <p style="color:#64748b; font-size:12px; font-weight:700; margin:0;">{label}</p>
            <p style="font-size:30px; font-weight:800; color:{color}; margin:0;">{val}</p>
        </div>
    """, unsafe_allow_html=True)

if not df_display.empty:
    st.write("") # Spacer
    g1, g2, g3 = st.columns([1, 1, 1.2])

    # 1. PIC WORKLOAD (Donut Modern)
    with g1:
        st.markdown("<p style='text-align:center; font-weight:700;'>Workload by PIC</p>", unsafe_allow_html=True)
        counts = df_display['PIC'].value_counts()
        fig = px.pie(names=counts.index, values=counts.values, hole=0.6,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_traces(textinfo='label+percent', textposition='outside', marker=dict(line=dict(color='#FFFFFF', width=2)))
        fig.update_layout(height=350, showlegend=False, margin=dict(t=30, b=30, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    # 2. STATUS DISTRIBUTION (Soft Colors)
    with g2:
        st.markdown("<p style='text-align:center; font-weight:700;'>Status Breakdown</p>", unsafe_allow_html=True)
        stat = df_display['Status'].value_counts()
        fig = px.pie(names=stat.index, values=stat.values, hole=0.6,
                     color=stat.index,
                     color_discrete_map={'Complete': '#22c55e', 'Outstanding': '#ef4444', 'On Process': '#3b82f6'})
        fig.update_traces(textinfo='label+percent', marker=dict(line=dict(color='#FFFFFF', width=2)))
        fig.update_layout(height=350, showlegend=False, margin=dict(t=30, b=30, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    # 3. UNIT ANALYSIS (Modern Gradient-like Bar)
    with g3:
        st.markdown("<p style='text-align:center; font-weight:700;'>Top Units Performance</p>", unsafe_allow_html=True)
        unit_data = df_display['Unit no'].value_counts().nlargest(7).reset_index()
        fig = px.bar(unit_data, x='count', y='Unit no', orientation='h', 
                     color='count', color_continuous_scale='Blues', text_auto=True)
        fig.update_layout(height=350, showlegend=False, xaxis_visible=False, yaxis_title=None, 
                          coloraxis_showscale=False, margin=dict(t=0, b=0, l=0, r=20))
        fig.update_traces(marker_line_color='rgb(8,48,107)', marker_line_width=1.5, opacity=0.8)
        st.plotly_chart(fig, use_container_width=True)

# --- 6. DATA EDITOR ---
st.markdown("### 📋 Detailed Records")
df_to_edit = df_display if (f_fleet or f_unit or f_status or search_query) else df_master
df_to_edit.index = range(1, len(df_to_edit) + 1)

edited_data = st.data_editor(
    df_to_edit, use_container_width=True, hide_index=False, num_rows="dynamic", height=500,
    key="editor_modern_v1",
    column_config={
        "Fleet": st.column_config.TextColumn("Fleet", width=120, pinned=True),
        "Unit no": st.column_config.TextColumn("Unit", width=100, pinned=True),
        "PIC": st.column_config.TextColumn("PIC", width=120),
        "Qty": st.column_config.NumberColumn("Qty", width=80),
        "Doc Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "Status": st.column_config.SelectboxColumn("Status", options=["Complete", "Outstanding", "On Process"], width=130),
        "Update Status": st.column_config.TextColumn("Update Status", width=400)
    }
)

# --- 7. ACTIONS ---
c_save, c_exp, _ = st.columns([1.5, 1.5, 4])
if c_save.button("💾 SYNC TO CLOUD"):
    try:
        final_df = pd.concat([df_master[~df_master.index.isin(df_display.index)], edited_data.reset_index(drop=True)]).reset_index(drop=True)
        if 'Doc Date' in final_df.columns:
            final_df['Doc Date'] = pd.to_datetime(final_df['Doc Date']).dt.strftime('%Y-%m-%d').replace('NaT', '')
        conn.update(data=final_df)
        refresh_all_data()
        st.success("Cloud Synchronized Successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Sync Failed: {e}")

excel_data = io.BytesIO()
with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
    df_display.to_excel(writer, index=False)
c_exp.download_button("📊 DOWNLOAD EXCEL", data=excel_data.getvalue(), file_name='NHM_Report.xlsx')

st.markdown("<div style='text-align:center; color:#94a3b8; font-size:12px; padding:30px;'>PT Nusa Halmahera Minerals | SCM Division © 2026</div>", unsafe_allow_html=True)