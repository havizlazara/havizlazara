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

# --- 2. KONEKSI DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load_data():
    data = conn.read(ttl=0)
    if data is None or data.empty:
        return pd.DataFrame(columns=['Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note', 'PO No'])
    
    # Cleaning kolom
    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated(keep='first')]
    
    if 'Delivery Note' not in data.columns:
        data['Delivery Note'] = ""
    
    text_cols = ['Resv', 'Material', 'PO No', 'Dept.', 'Fleet', 'Unit no', 'PIC', 'Status', 'Delivery Note']
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.replace(r'\.0$', '', regex=True)
            
    return data

if 'df_master' not in st.session_state:
    st.session_state.df_master = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("🔐 Admin Access")
    if not st.session_state['authenticated']:
        admin_pw = st.text_input("Password Admin:", type="password")
        if st.button("Login"):
            if admin_pw == "nhm123":
                st.session_state['authenticated'] = True
                st.rerun()
            else: st.error("Password Salah")
    else:
        st.success("Mode Admin Aktif")
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

# --- 4. CSS & HEADER ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

header_bg = get_base64_image("BG2.jpg")
logo_img = get_base64_image("NHM.jpg")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #f1f5f9; }}
    .main .block-container {{ background-color: #ffffff; padding: 2rem 3rem; border-radius: 12px; }}
    .custom-header {{
        position: relative; width: 100%; min-height: 250px; padding: 40px 20px;
        border-radius: 15px; overflow: hidden; display: flex; flex-direction: column;
        align-items: center; text-align: center; margin-bottom: 30px;
        background-image: url("data:image/jpeg;base64,{header_bg}");
        background-size: cover; background-position: center; border: 2px solid #1f4e79;
    }}
    .giant-title {{ 
        font-family: 'serif'; font-size: 50px; font-weight: 900; color: #ffffff !important; 
        background: rgba(31, 78, 121, 0.7); padding: 10px 30px; border-radius: 10px; display: inline-block;
    }}
    </style>
    """, unsafe_allow_html=True)

st.markdown(f"""
    <div class="custom-header">
        <div class="header-content">
            <img src="data:image/jpeg;base64,{logo_img}" style="height:100px; mix-blend-mode:multiply;">
            <br><h1 class="giant-title">Purchase Order Monitoring</h1><br>
            <h2 style="color:white; letter-spacing:5px;">NHM SUPPLY CHAIN & LOGISTICS</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 5. FILTER SECTION ---
search_q = st.text_input("🔎 GLOBAL SEARCH:", placeholder="Cari data...")
df_filtered = st.session_state.df_master.copy()
if search_q:
    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_q, case=False).any(), axis=1)]

# --- 6. GRAFIK (FONT PUTIH BOLD) ---
if not df_filtered.empty:
    g1, g2, g3 = st.columns(3)
    font_style = dict(family="Arial Black", size=14, color="white")
    
    with g1:
        fig1 = px.pie(df_filtered, names='PIC', hole=.4, height=250, title="By PIC")
        fig1.update_traces(textposition='inside', textinfo='percent+label', textfont=font_style)
        fig1.update_layout(showlegend=False, margin=dict(t=35,b=5,l=5,r=5))
        st.plotly_chart(fig1, use_container_width=True)
        
    with g2:
        fig2 = px.pie(df_filtered, names='Status', hole=.4, height=250, title="By Status",
                      color='Status', color_discrete_map={'Outstanding':'#ef4444', 'Complete':'#22c55e', 'Partial':'#f39c12'})
        fig2.update_traces(textposition='inside', textinfo='percent+label', textfont=font_style)
        fig2.update_layout(showlegend=False, margin=dict(t=35,b=5,l=5,r=5))
        st.plotly_chart(fig2, use_container_width=True)
        
    with g3:
        ud = df_filtered['Unit no'].value_counts().nlargest(5).reset_index()
        fig3 = px.bar(ud, x='Unit no', y='count', height=250, title="Top 5 Units", 
                      color='Unit no', color_discrete_sequence=px.colors.qualitative.Bold)
        fig3.update_traces(texttemplate='%{y}', textposition='inside', textfont=font_style)
        fig3.update_layout(showlegend=False, yaxis_visible=False, margin=dict(t=35,b=5,l=5,r=5))
        st.plotly_chart(fig3, use_container_width=True)

# --- 7. DATABASE DENGAN EFEK "DRAG HIGHLIGHT" MERAH ---
st.markdown("---")
st.markdown("### 📋 Database Monitoring")

if st.session_state['authenticated']:
    df_editor = df_filtered.copy()
    if 'Pilih' not in df_editor.columns:
        df_editor.insert(0, 'Pilih', False)

    # LOGIKA STYLING: Memberikan efek highlight penuh saat kolom 'Pilih' bernilai True
    def apply_full_drag_highlight(row):
        # Warna merah terang untuk efek 'dragged/selected'
        color_selected = 'background-color: #ff5252; color: white; font-weight: bold; border: 1px solid #b71c1c;'
        return [color_selected] * len(row) if row['Pilih'] else [''] * len(row)

    edited_df = st.data_editor(
        df_editor.style.apply(apply_full_drag_highlight, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pilih": st.column_config.CheckboxColumn("Pilih", default=False, width="small"),
            "Status": st.column_config.SelectboxColumn("Status", options=["Outstanding", "Partial", "Complete"]),
            "Delivery Note": st.column_config.TextColumn("Delivery Note", width="large")
        },
        key="editor_nhm_drag_effect"
    )

    selected_indices = edited_df[edited_df['Pilih'] == True].index

    # ACTION BUTTONS
    st.write("🔧 **Admin Actions:**")
    a1, a2, a3, a4 = st.columns([1, 1, 1, 3])
    
    if a1.button("🔴 Outstanding", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Outstanding"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = ""
            st.rerun()

    if a2.button("🟡 Partial", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.df_master.loc[selected_indices, 'Status'] = "Partial"
            st.session_state.df_master.loc[selected_indices, 'Delivery Note'] = "Partial Delivery"
            st.rerun()

    if a3.button("🟢 Complete", use_container_width=True):
        if not selected_indices.empty:
            st.session_state.show_complete_options = True
            st.session_state.target_indices = selected_indices
            st.rerun()

    if a4.button("💾 SIMPAN KE CLOUD", type="primary", use_container_width=True):
        try:
            save_df = st.session_state.df_master.drop(columns=['Pilih'], errors='ignore')
            conn.update(data=save_df)
            st.cache_data.clear()
            st.success("Tersimpan!")
        except Exception as e: st.error(f"Gagal: {e}")

    # LOGIKA COMPLETE (Receive on Bitung/Site)
    if st.session_state.show_complete_options:
        st.warning("📍 Pilih lokasi untuk baris yang dipilih:")
        c1, c2, c3 = st.columns([1,1,2])
        if c1.button("📦 Receive on Bitung", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Bitung"
            st.session_state.show_complete_options = False
            st.rerun()
        if c2.button("🚜 Receive on Site", use_container_width=True):
            st.session_state.df_master.loc[st.session_state.target_indices, 'Status'] = "Complete"
            st.session_state.df_master.loc[st.session_state.target_indices, 'Delivery Note'] = "Receive on Site"
            st.session_state.show_complete_options = False
            st.rerun()
        if c3.button("❌ Batal", use_container_width=True):
            st.session_state.show_complete_options = False
            st.rerun()
else:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# --- 8. EXPORT ---
ex_buf = io.BytesIO()
with pd.ExcelWriter(ex_buf, engine='xlsxwriter') as wr:
    df_filtered.to_excel(wr, index=False)
st.download_button("📊 DOWNLOAD EXCEL", data=ex_buf.getvalue(), file_name="PO_Monitoring.xlsx")