import streamlit as st
import pandas as pd
import datetime
import pytz
import io

st.set_page_config(page_title="Gr.7 KT Klasdissipline", layout="wide")

# Tema en CSS Styl
st.markdown("""
    <style>
    header[data-testid="stHeader"], .stAppHeader {
        display: none !important;
    }
    
    .stAppViewMain {
        padding-top: 0px !important;
    }

    .stApp {
        background-color: #0d1b2a !important;
        color: #ffffff !important;
    }

    /* Knoppie-style vir Positief en Negatief */
    .stButton>button {
        width: 100%;
        height: 32px !important;
        font-size: 10px !important;
        font-weight: bold;
        border-radius: 4px;
        padding: 0px !important;
        margin-bottom: 0px !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.2rem !important;
        align-items: center !important;
    }
    
    h1, h2, h3, h4, label, p {
        color: #e0e1dd !important;
        margin-bottom: 0.1rem !important;
    }
    
    .student-label {
        font-size: 11px;
        font-weight: bold;
        color: #f4a261;
        line-height: 32px;
        height: 32px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: flex;
        align-items: center;
    }

    .app-footer {
        text-align: center;
        color: #778da9 !important;
        font-size: 10px;
        padding: 15px 0px 5px 0px;
        margin-top: 20px;
        border-top: 1px solid #1b263b;
    }
    </style>
""", unsafe_allow_html=True)

# Sessie-toestand vir die logboek
if "gedrag_events" not in st.session_state:
    st.session_state.gedrag_events = []

st.title("🏫 Klasdissipline & Gedragsmonitor")

# --- INSTELINGS ---
with st.expander("⚙️ Klas Instellings & Leerderlys", expanded=False):
    col_k1, col_k2 = st.columns(2)
    klas_naam = col_k1.text_input("Klas", value="Gr.7 KT")
    opvoeder_naam = col_k2.text_input("Opvoeder", value="Mnr. Toerien")
    
    default_leerders = """Burger Frederick, Carelse Anna-Marie, Carstens Simon, Claassen JJ, Coetzee Zoë, Conradie Christel, De Lange Chantenique, Geldenhuys Lani, Haak Wilrich, Jenneke Kian, Keffers Phoenix, Krugel Willem, Lakey Lenvan, Lewies Jolynn, Mostert Caleb, Munnik Aniecke, Nackerdien Fariah, Roscher Lianke, Smith Tayo, Strydom El-Jay, Swanepoel Henko, Taylor Theart, Van der Westhuizen Laylah, Van Tonder Dia, Van Wyk Carah, Vogel Jaco, Walters Yvonne, Wijgergangs Jayden, Willers Lilly, Williams Ethan"""
    raw_leerders = st.text_area("Leerders se Name (geskei met 'n komma):", value=default_leerders, height=120)
    leerder_lys = [l.strip() for l in raw_leerders.split(",") if l.strip()]

# Funksie om voorvalle te registreer
def log_gedrag(leerder, tipe, aksie, punte, nota=""):
    sa_time = datetime.datetime.now(pytz.timezone('Africa/Johannesburg'))
    t_min = sa_time.strftime("%Y-%m-%d %H:%M:%S")
    
    st.session_state.gedrag_events.append({
        "Datum/Tyd": t_min,
        "Klas": klas_naam,
        "Opvoeder": opvoeder_naam,
        "Leerder": leerder,
        "Tipe": tipe,
        "Gedrag": aksie,
        "Punte": punte,
        "Nota": nota
    })
    
    ikoon = "🟢" if punte > 0 else "🔴"
    st.toast(f"{ikoon} {leerder}: {aksie} ({'+' if punte > 0 else ''}{punte})")

def kanselleer_laaste():
    if st.session_state.gedrag_events:
        laaste = st.session_state.gedrag_events.pop()
        st.toast(f"↩️ Verwyder: {laaste['Leerder']} - {laaste['Gedrag']}")

st.divider()

# --- SPESIFIEKE NOTA INSET ---
optionele_nota = st.text_input("📝 Opsionele Opmerking/Nota (Tik hier voor jy 'n knoppie druk):", value="")

st.divider()

# --- LEERDER ROSTER & GEDRAGSKNOPPIES ---
st.markdown("#### 🏃 LEERDER GEDRAGSKNOPPIES")
st.caption("🟢 **Positief (+1):** Hulpvaardig | Goeie waardes  ──  🔴 **Negatief (-1):** Gesels konstant | Swak dissipline | Waarskuwing")

for leerder in leerder_lys:
    c_label, b1, b2, b3, b4, b5 = st.columns([2.5, 1.2, 1.2, 1.2, 1.2, 1.2])
    
    with c_label:
        st.markdown(f"<div class='student-label'>{leerder}</div>", unsafe_allow_html=True)
        
    # Positiewe Knoppies (+1)
    if b1.button("🤝 Hulpvaardig", key=f"hulp_{leerder}"): 
        log_gedrag(leerder, "Positief", "Hulpvaardig", 1, optionele_nota)
    if b2.button("🌟 Goeie waardes", key=f"waardes_{leerder}"): 
        log_gedrag(leerder, "Positief", "Goeie waardes", 1, optionele_nota)
        
    # Negatiewe Knoppies (-1)
    if b3.button("🗣️ Gesels konstant", key=f"gesels_{leerder}"): 
        log_gedrag(leerder, "Negatief", "Gesels konstant", -1, optionele_nota)
    if b4.button("⚠️ Swak dissipline", key=f"dissipline_{leerder}"): 
        log_gedrag(leerder, "Negatief", "Swak dissipline", -1, optionele_nota)
    if b5.button("🚩 Waarskuwing", key=f"waarsk_{leerder}"): 
        log_gedrag(leerder, "Negatief", "Waarskuwing", -1, optionele_nota)

st.divider()

# --- KONTROLE KNOPPIES ---
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    if st.button("↩️ Kanselleer Laaste Inskrywing"):
        kanselleer_laaste()

st.divider()

# --- EXPORT & OPSOMMING ---
if st.session_state.gedrag_events:
    df_events = pd.DataFrame(st.session_state.gedrag_events)
    
    # Berekende opsommings
    df_leerder_opsomming = df_events.groupby(["Leerder", "Tipe"]).size().unstack(fill_value=0).reset_index()
    df_punte = df_events.groupby("Leerder")["Punte"].sum().reset_index(name="Totale Gedragspunte")
    df_leerder_finaal = pd.merge(df_leerder_opsomming, df_punte, on="Leerder")

    st.markdown("#### 📊 Gedragsverslag & Opsomming")
    
    t1, t2, t3 = st.tabs(["🏃 Opsomming per Leerder", "📋 Alle Voorvalle (Tydlyn)", "⚠️ Ouer-Verslag Data"])
    
    with t1:
        st.dataframe(df_leerder_finaal, use_container_width=True)
    with t2:
        st.dataframe(df_events, use_container_width=True)
    with t3:
        df_negatief = df_events[df_events["Tipe"] == "Negatief"]
        st.dataframe(df_negatief, use_container_width=True)

    # Excel Aflaai
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_leerder_finaal.to_excel(writer, sheet_name='Klas Opsomming', index=False)
        df_events.to_excel(writer, sheet_name='Volledige Tydlyn', index=False)
        df_events[df_events["Tipe"] == "Negatief"].to_excel(writer, sheet_name='Negatiewe Voorvalle (Ouers)', index=False)
        df_events[df_events["Tipe"] == "Positief"].to_excel(writer, sheet_name='Positiewe Inskrywings', index=False)
        
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Laai Klas-Verslag Excel Worksheet (.xlsx) Af",
        data=excel_data,
        file_name=f"{klas_naam}_Gedragsverslag.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("<div class='app-footer'>Klasdissipline & Gedragsmonitor - Gr.7 KT</div>", unsafe_allow_html=True)
