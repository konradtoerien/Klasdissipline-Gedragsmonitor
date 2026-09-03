import streamlit as st
import pandas as pd
import datetime
import pytz
import io
import gspread
from google.oauth2.service_account import Credentials

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

# --- GOOGLE SHEETS VERBINDING ---
@st.cache_resource
def get_google_sheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    client = gspread.authorize(credentials)
    # Maak die spesifieke sheet oop
    sheet = client.open("Gr.7KT 2026 Gedrag").sheet1
    return sheet

try:
    sheet = get_google_sheet()
    
    # Skep opskrifte as die sheet nog heeltemal leeg is
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["Datum/Tyd", "Klas", "Opvoeder", "Leerder", "Ouer_Epos", "Tipe", "Gedrag", "Punte", "Nota"])
except Exception as e:
    st.error(f"Fout met verbinding na Google Sheets: {e}")
    sheet = None

# --- HERLAAI DATA VANAF GOOGLE SHEETS ---
def laai_data_van_sheet():
    if sheet:
        records = sheet.get_all_records()
        return records
    return []

if "gedrag_events" not in st.session_state:
    st.session_state.gedrag_events = laai_data_van_sheet()

st.title("🏫 Klasdissipline & Gedragsmonitor")

# --- DEFAULT LEERDERLYST MET EPOSSE ---
default_leerders_met_epos = """Burger Frederick, frederick@voorbeeld.co.za
Carelse Anna-Marie, annamarie@voorbeeld.co.za
Carstens Simon, simon@voorbeeld.co.za
Claassen JJ, jj@voorbeeld.co.za
Coetzee Zoë, zoe@voorbeeld.co.za
Conradie Christel, christel@voorbeeld.co.za
De Lange Chantenique, chantenique@voorbeeld.co.za
Geldenhuys Lani, lani@voorbeeld.co.za
Haak Wilrich, wilrich@voorbeeld.co.za
Jenneke Kian, kian@voorbeeld.co.za
Keffers Phoenix, phoenix@voorbeeld.co.za
Krugel Willem, willem@voorbeeld.co.za
Lakey Lenvan, lenvan@voorbeeld.co.za
Lewies Jolynn, jolynn@voorbeeld.co.za
Mostert Caleb, caleb@voorbeeld.co.za
Munnik Aniecke, aniecke@voorbeeld.co.za
Nackerdien Fariah, fariah@voorbeeld.co.za
Roscher Lianke, lianke@voorbeeld.co.za
Smith Tayo, tayo@voorbeeld.co.za
Strydom El-Jay, eljay@voorbeeld.co.za
Swanepoel Henko, henko@voorbeeld.co.za
Taylor Theart, theart@voorbeeld.co.za
Van der Westhuizen Laylah, laylah@voorbeeld.co.za
Van Tonder Dia, dia@voorbeeld.co.za
Van Wyk Carah, carah@voorbeeld.co.za
Vogel Jaco, jaco@voorbeeld.co.za
Walters Yvonne, yvonne@voorbeeld.co.za
Wijgergangs Jayden, jayden@voorbeeld.co.za
Willers Lilly, lilly@voorbeeld.co.za
Williams Ethan, ethan@voorbeeld.co.za"""

# --- INSTELINGS ---
with st.expander("⚙️ Klas Instellings & Leerderlys", expanded=False):
    col_k1, col_k2 = st.columns(2)
    klas_naam = col_k1.text_input("Klas", value="Gr.7 KT")
    opvoeder_naam = col_k2.text_input("Opvoeder", value="Mnr. Toerien")
    
    raw_leerders = st.text_area("Leerders se Name en Ouer E-posse (Formaat: Naam, Epos):", value=default_leerders_met_epos, height=150)
    
    # Parse name en eposadresse
    student_dict = {}
    for line in raw_leerders.split("\n"):
        if "," in line:
            parts = line.split(",")
            naam = parts[0].strip()
            epos = parts[1].strip()
            if naam:
                student_dict[naam] = epos

# Funksie om voorvalle te registreer
def log_gedrag(leerder, tipe, aksie, punte, nota=""):
    sa_time = datetime.datetime.now(pytz.timezone('Africa/Johannesburg'))
    t_min = sa_time.strftime("%Y-%m-%d %H:%M:%S")
    uer_epos = student_dict.get(leerder, "")
    
    nuwe_ry = {
        "Datum/Tyd": t_min,
        "Klas": klas_naam,
        "Opvoeder": opvoeder_naam,
        "Leerder": leerder,
        "Ouer_Epos": uer_epos,
        "Tipe": tipe,
        "Gedrag": aksie,
        "Punte": punte,
        "Nota": nota
    }
    
    # Voeg toe aan plaaslike geheue
    st.session_state.gedrag_events.append(nuwe_ry)
    
    # Skryf direk na Google Sheet
    if sheet:
        try:
            sheet.append_row([t_min, klas_naam, opvoeder_naam, leerder, uer_epos, tipe, aksie, punte, nota])
        except Exception as e:
            st.error(f"Koor nie op te stoor in Google Sheet nie: {e}")
    
    ikoon = "🟢" if punte > 0 else "🔴"
    st.toast(f"{ikoon} {leerder}: {aksie} ({'+' if punte > 0 else ''}{punte})")

def kanselleer_laaste():
    if st.session_state.gedrag_events:
        laaste = st.session_state.gedrag_events.pop()
        # Verwyder ook die laaste ry in Google Sheet
        if sheet:
            try:
                values = sheet.get_all_values()
                if len(values) > 1:
                    sheet.delete_rows(len(values))
            except Exception as e:
                st.error(f"Koor nie laaste ry te skrap nie: {e}")
        st.toast(f"↩️ Verwyder: {laaste['Leerder']} - {laaste['Gedrag']}")

st.divider()

# --- SPESIFIEKE NOTA INSET ---
optionele_nota = st.text_input("📝 Opsionele Opmerking/Nota (Tik hier voor jy 'n knoppie druk):", value="")

st.divider()

# --- LEERDER ROSTER & GEDRAGSKNOPPIES ---
st.markdown("#### 🏃 LEERDER GEDRAGSKNOPPIES")
st.caption("🟢 **Positief (+1):** Hulpvaardig | Goeie waardes  ──  🔴 **Negatief (-1):** Gesels konstant | Swak dissipline | Waarskuwing")

for leerder in student_dict.keys():
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
with col_ctrl2:
    if st.button("🔄 Herlaai Data vanaf Google Sheets"):
        st.session_state.gedrag_events = laai_data_van_sheet()
        st.toast("✅ Data suksesvol herlaai!")

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
