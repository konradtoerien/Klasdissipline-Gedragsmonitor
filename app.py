import streamlit as st
import pandas as pd
import datetime
import pytz
import io
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.express as px
from fpdf import FPDF

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

    /* Text Inputs & Text Areas: Dark, high-contrast text on bright backgrounds */
    .stTextInput input, .stTextArea textarea {
        color: #0d1b2a !important;
        background-color: #ffffff !important;
        font-weight: 500 !important;
        border-radius: 4px !important;
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
        transition: all 0.2s ease-in-out !important;
    }

    /* Button Hover / Cursor Highlight Effect */
    .stButton>button:hover {
        background-color: #f4a261 !important;
        color: #0d1b2a !important;
        border-color: #f4a261 !important;
        transform: scale(1.03) !important;
        box-shadow: 0px 0px 8px rgba(244, 162, 97, 0.6) !important;
        cursor: pointer !important;
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

    /* WhatsApp Knoppie Styl */
    .wa-button {
        display: inline-block;
        background-color: #25D366;
        color: #ffffff !important;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: bold;
        text-decoration: none;
        border-radius: 5px;
        margin-top: 2px;
        margin-bottom: 2px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.3);
    }
    .wa-button:hover {
        background-color: #128C7E;
        color: #ffffff !important;
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
    sheet = client.open("Gr.7KT 2026 Gedrag").sheet1
    return sheet

try:
    sheet = get_google_sheet()
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["Datum/Tyd", "Klas", "Opvoeder", "Leerder", "Ouer_Sel", "Ouer_Epos", "Tipe", "Gedrag", "Punte", "Nota"])
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

if "laaste_wa_skakels" not in st.session_state:
    st.session_state.laaste_wa_skakels = []

st.title("🏫 Klasdissipline & Gedragsmonitor")

# --- GRATIS WHATSAPP SKAKEL GENERATOR ---
def skep_whatsapp_skakel(selnommer, leerder_naam, tipe, gedrag, opvoeder, nota=""):
    """Genereer 'n whatsapp:// skakel wat die WhatsApp app direk oopmaak."""
    if not selnommer or not str(selnommer).strip():
        return None
    
    skoon_nommer = str(selnommer).replace(" ", "").replace("-", "").strip()
    if skoon_nommer.startswith("0"):
        skoon_nommer = "27" + skoon_nommer[1:]
    elif skoon_nommer.startswith("+"):
        skoon_nommer = skoon_nommer[1:]

    tyd_nou = datetime.datetime.now(pytz.timezone('Africa/Johannesburg')).strftime('%Y-%m-%d %H:%M')
    ikoon = "🌟" if tipe == "Positief" else "⚠️"
    
    boodskap = f"""Beste Ouer,

Hierdie is 'n {tipe.lower()} kennisgewing rakende *{leerder_naam}* in {opvoeder} se klas.

{ikoon} *Gedrag/Aanmoediging:* {gedrag}
📅 *Datum/Tyd:* {tyd_nou}
📝 *Opmerking:* {nota if nota else 'Geen verdere opmerkings nie.'}

Vriendelike groete,
{opvoeder}"""

    encoded_boodskap = urllib.parse.quote(boodskap)
    return f"whatsapp://send?phone={skoon_nommer}&text={encoded_boodskap}"

# --- EMAIL KENNISGEWING FUNKSIE ---
def stuur_ouer_epos(ontvanger_epos, leerder_naam, gedrag, opvoeder, nota=""):
    if not ontvanger_epos or "@" not in ontvanger_epos or "voorbeeld.co.za" in ontvanger_epos:
        return False
    
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]

        msg = MIMEMultipart()
        msg['From'] = f"{opvoeder} <{sender_email}>"
        msg['To'] = ontvanger_epos
        msg['Subject'] = f"Gedragskennisgewing: {leerder_naam}"

        body = f"""Beste Ouer,

Hierdie is 'n outomatiese kennisgewing rakende {leerder_naam} in {opvoeder} se klas.

Gedrag Aangemeld: {gedrag}
Datum/Tyd: {datetime.datetime.now(pytz.timezone('Africa/Johannesburg')).strftime('%Y-%m-%d %H:%M')}
Opmerking: {nota if nota else 'Geen verdere opmerkings nie.'}

Aanvaar asseblief hierdie kennisgewing ter inligting.

Vriendelike groete,
{opvoeder}
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Kon nie e-pos stuur na {ontvanger_epos} nie: {e}")
        return False

# --- PDF GELEENTHEID FUNKSIE ---
def genereer_leerder_pdf(leerder_naam, df_leerder_events, opvoeder_naam, klas_naam):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    pdf.cell(0, 10, f"Gedragsverslag: {leerder_naam}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Klas: {klas_naam} | Opvoeder: {opvoeder_naam} | Datum: {datetime.date.today().strftime('%Y-%m-%d')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)
    
    pos = len(df_leerder_events[df_leerder_events["Tipe"] == "Positief"])
    neg = len(df_leerder_events[df_leerder_events["Tipe"] == "Negatief"])
    punte = df_leerder_events["Punte"].sum()
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"Totaal Positief: {pos} | Totaal Negatief: {neg} | Totale Punte: {punte}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 8, "Datum/Tyd", border=1, fill=True)
    pdf.cell(25, 8, "Tipe", border=1, fill=True)
    pdf.cell(45, 8, "Gedrag", border=1, fill=True)
    pdf.cell(15, 8, "Punte", border=1, fill=True)
    pdf.cell(65, 8, "Nota", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 9)
    for _, row in df_leerder_events.iterrows():
        dt = str(row.get("Datum/Tyd", ""))[:16]
        tipe = str(row.get("Tipe", ""))
        gedrag = str(row.get("Gedrag", ""))
        pnt = str(row.get("Punte", ""))
        nota = str(row.get("Nota", ""))[:35]
        
        pdf.cell(40, 7, dt, border=1)
        pdf.cell(25, 7, tipe, border=1)
        pdf.cell(45, 7, gedrag, border=1)
        pdf.cell(15, 7, pnt, border=1)
        pdf.cell(65, 7, nota, border=1, new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, "Hierdie verslag is outomaties geskep deur die Klasdissipline & Gedragsmonitor stelsel.")
    
    return bytes(pdf.output())

# --- DEFAULT LEERDERLYST MET BEIDE SELNOMMER & EPOS ---
default_leerders_met_kontak = """Burger Frederick, 0821234567, frederick@voorbeeld.co.za
Carelse Anna-Marie, 0821234568, annamarie@voorbeeld.co.za
Carstens Simon, 0821234569, simon@voorbeeld.co.za
Claassen JJ, 0829529901, jmhclaassen@gmail.com
Coetzee Zoë, 0625236510, chenitavdw@gmail.com
Conradie Christel, 0829216737, marian.conradie@gmail.com
De Lange Chantenique, 0821234573, chantenique@voorbeeld.co.za
Geldenhuys Lani, 0736217513, Bkskoonmaakmiddels@gmail.com
Haak Wilrich, 0737101754, stefaniehaak3@gmail.com
Jenneke Kian, 0821234576, kian@voorbeeld.co.za
Keffers Phoenix, 0821234577, phoenix@voorbeeld.co.za
Krugel Willem, 0821234578, willem@voorbeeld.co.za
Lakey Lenvan, 0821234579, lenvan@voorbeeld.co.za
Lewies Jolynn, 0821234580, jolynn@voorbeeld.co.za
Mostert Caleb, 0821234581, caleb@voorbeeld.co.za
Munnik Aniecke, 0821234582, aniecke@voorbeeld.co.za
Nackerdien Fariah, 0739412620, Kautharnackerdien8@gmail.com
Roscher Lianke, 0823427576, nicolivanwyk@yahoo.com
Smith Tayo, 0821234585, tayo@voorbeeld.co.za
Strydom El-Jay, 0730955552, Fredelenestrydom21@gmail.com
Swanepoel Henko, 0832290356, anzkeswanepoel@gmail.com
Taylor Theart, 0766546735, beofox@gmail.com
Van der Westhuizen Laylah, 0821234589, laylah@voorbeeld.co.za
Van Tonder Dia, 0821234590, dia@voorbeeld.co.za
Van Wyk Carah, 0824251990, cyrajadevanwyk123@gmail.com
Vogel Jaco, 0764160926, Janien@kbooks.co.za
Walters Yvonne, 0821234593, yvonne@voorbeeld.co.za
Wijgergangs Jayden, 0821234594, jayden@voorbeeld.co.za
Willers Lilly, 0821234595, lilly@voorbeeld.co.za
Williams Ethan, 0821234596, ethan@voorbeeld.co.za"""

# --- INSTELINGS ---
with st.expander("⚙️ Klas Instellings & Ouer Kontak Bestuur", expanded=False):
    col_k1, col_k2, col_k3, col_k4 = st.columns([1.5, 1.5, 1, 1])
    klas_naam = col_k1.text_input("Klas", value="Gr.7 KT")
    opvoeder_naam = col_k2.text_input("Opvoeder", value="Mnr. Toerien")
    
    # Skakelaars vir WhatsApp en E-posse
    stuur_wa_aktief = col_k3.checkbox("Skep WhatsApp Skakels", value=True)
    stuur_eposse_aktief = col_k4.checkbox("Stuur Outomatiese E-posse", value=False)
    
    st.markdown("**Opdateer Leerderlyste (Formaat: Naam, Selfoonnommer, E-posadres):**")
    raw_leerders = st.text_area("Leerder lys:", value=default_leerders_met_kontak, height=200)
    
    student_dict = {}
    for line in raw_leerders.split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 1 and parts[0]:
            naam = parts[0]
            sel = parts[1] if len(parts) > 1 else ""
            epos = parts[2] if len(parts) > 2 else ""
            student_dict[naam] = {"sel": sel, "epos": epos}

# Funksie om voorvalle vir 'n LYS leerders te registreer
def log_gedrag_massa(leerders_lys, tipe, aksie, punte, nota=""):
    if not leerders_lys:
        st.warning("⚠️ Geen leerders is gekies nie!")
        return

    sa_time = datetime.datetime.now(pytz.timezone('Africa/Johannesburg'))
    t_min = sa_time.strftime("%Y-%m-%d %H:%M:%S")
    
    nuwe_wa_skakels = []
    
    for leerder in leerders_lys:
        kontak_info = student_dict.get(leerder, {"sel": "", "epos": ""})
        uer_sel = kontak_info["sel"]
        uer_epos = kontak_info["epos"]
        
        nuwe_ry = {
            "Datum/Tyd": t_min,
            "Klas": klas_naam,
            "Opvoeder": opvoeder_naam,
            "Leerder": leerder,
            "Ouer_Sel": uer_sel,
            "Ouer_Epos": uer_epos,
            "Tipe": tipe,
            "Gedrag": aksie,
            "Punte": punte,
            "Nota": nota
        }
        
        st.session_state.gedrag_events.append(nuwe_ry)
        
        # Skryf na Google Sheet
        if sheet:
            try:
                sheet.append_row([t_min, klas_naam, opvoeder_naam, leerder, uer_sel, uer_epos, tipe, aksie, punte, nota])
            except Exception as e:
                st.error(f"Kon nie opstoor in Google Sheet vir {leerder}: {e}")
        
        # Skep WhatsApp Skakels slegs as die skakelaar AAN is én daar 'n nommer is
        if stuur_wa_aktief and uer_sel:
            wa_url = skep_whatsapp_skakel(uer_sel, leerder, tipe, aksie, opvoeder_naam, nota)
            if wa_url:
                nuwe_wa_skakels.append({
                    "leerder": leerder,
                    "tipe": tipe,
                    "aksie": aksie,
                    "url": wa_url,
                    "kontak": uer_sel
                })
        
        # Stuur E-posse slegs as die skakelaar AAN is én daar 'n e-posadres is
        if stuur_eposse_aktief and uer_epos:
            stuur_ouer_epos(uer_epos, leerder, aksie, opvoeder_naam, nota)

    st.session_state.laaste_wa_skakels = nuwe_wa_skakels
    ikoon = "🟢" if punte > 0 else "🔴"
    st.toast(f"{ikoon} {len(leerders_lys)} Leerder(s) geregistreer vir: {aksie}")
    st.rerun()

def kanselleer_laaste():
    if st.session_state.gedrag_events:
        laaste = st.session_state.gedrag_events.pop()
        if sheet:
            try:
                values = sheet.get_all_values()
                if len(values) > 1:
                    sheet.delete_rows(len(values))
            except Exception as e:
                st.error(f"Kon nie laaste ry skrap nie: {e}")
        st.session_state.laaste_wa_skakels = []
        st.toast(f"↩️ Verwyder: {laaste['Leerder']} - {laaste['Gedrag']}")
        st.rerun()

st.divider()

# --- SPESIFIEKE NOTA INSET ---
optionele_nota = st.text_input("📝 Opsionele Opmerking/Nota (Tik hier voor jy 'n knoppie druk):", value="")

st.divider()

# --- MASSAKIESER (MULTI-SELECT REGMERKIES) ---
st.markdown("#### 👥 GROEP / MASSA LEERDER KIESER")
gekoose_groep = st.multiselect(
    "Merk/Kies een of meer leerders vir dieselfde inskrywing:",
    options=sorted(list(student_dict.keys())),
    help="Kies verskeie leerders as jy vir almal gelyktydig dieselfde positiewe of negatiewe punte wil gee."
)

if gekoose_groep:
    st.markdown(f"**Pas aksie toe op {len(gekoose_groep)} gekose leerder(s):**")
    m_b1, m_b2, m_b3, m_b4, m_b5 = st.columns(5)
    
    if m_b1.button("🤝 Hulpvaardig (+1)", key="massa_hulp"):
        log_gedrag_massa(gekoose_groep, "Positief", "Hulpvaardig", 1, optionele_nota)
    if m_b2.button("🌟 Goeie waardes (+1)", key="massa_waardes"):
        log_gedrag_massa(gekoose_groep, "Positief", "Goeie waardes", 1, optionele_nota)
    if m_b3.button("🗣️ Gesels konstant (-1)", key="massa_gesels"):
        log_gedrag_massa(gekoose_groep, "Negatief", "Gesels konstant", -1, optionele_nota)
    if m_b4.button("⚠️ Swak dissipline (-1)", key="massa_dissipline"):
        log_gedrag_massa(gekoose_groep, "Negatief", "Swak dissipline", -1, optionele_nota)
    if m_b5.button("🚩 Waarskuwing (-1)", key="massa_waarsk"):
        log_gedrag_massa(gekoose_groep, "Negatief", "Waarskuwing", -1, optionele_nota)

st.divider()

# --- INDIVIDUELE LEERDER ROSTER & GEDRAGSKNOPPIES ---
st.markdown("#### 🏃 INDIVIDUELE LEERDER SKAKELS")
st.caption("🟢 **Positief (+1):** Hulpvaardig | Goeie waardes  ──  🔴 **Negatief (-1):** Gesels konstant | Swak dissipline | Waarskuwing")

for leerder in student_dict.keys():
    c_label, b1, b2, b3, b4, b5 = st.columns([2.5, 1.2, 1.2, 1.2, 1.2, 1.2])
    
    with c_label:
        st.markdown(f"<div class='student-label'>{leerder}</div>", unsafe_allow_html=True)
        
    if b1.button("🤝 Hulpvaardig", key=f"hulp_{leerder}"): 
        log_gedrag_massa([leerder], "Positief", "Hulpvaardig", 1, optionele_nota)
    if b2.button("🌟 Goeie waardes", key=f"waardes_{leerder}"): 
        log_gedrag_massa([leerder], "Positief", "Goeie waardes", 1, optionele_nota)
        
    if b3.button("🗣️ Gesels konstant", key=f"gesels_{leerder}"): 
        log_gedrag_massa([leerder], "Negatief", "Gesels konstant", -1, optionele_nota)
    if b4.button("⚠️ Swak dissipline", key=f"dissipline_{leerder}"): 
        log_gedrag_massa([leerder], "Negatief", "Swak dissipline", -1, optionele_nota)
    if b5.button("🚩 Waarskuwing", key=f"waarsk_{leerder}"): 
        log_gedrag_massa([leerder], "Negatief", "Waarskuwing", -1, optionele_nota)

st.divider()

# --- KONTROLE KNOPPIES ---
col_ctrl1, col_ctrl2 = st.columns(2)
with col_ctrl1:
    if st.button("↩️ Kanselleer Laaste Inskrywing"):
        kanselleer_laaste()
with col_ctrl2:
    if st.button("🔄 Herlaai Data vanaf Google Sheets"):
        st.session_state.gedrag_events = laai_data_van_sheet()
        st.session_state.laaste_wa_skakels = []
        st.toast("✅ Data suksesvol herlaai!")
        st.rerun()

st.divider()

# --- WHATSAPP STUUR BANNER (ONDER-AAN DIE SKERM GEPLAAS) ---
if st.session_state.laaste_wa_skakels:
    st.markdown("### 📲 Stuur WhatsApp Kennisgewings vir Laaste Inskrywings:")
    for wa_data in st.session_state.laaste_wa_skakels:
        tipe_ikoon = "🟢" if wa_data['tipe'] == "Positief" else "🔴"
        st.markdown(
            f"{tipe_ikoon} **{wa_data['leerder']}** ({wa_data['kontak']}): "
            f"<a href='{wa_data['url']}' target='_self' class='wa-button'>Stuur WhatsApp ({wa_data['aksie']})</a>", 
            unsafe_allow_html=True
        )
    st.divider()

# --- EXPORT, GRAFIEKE & OPSOMMING ---
if st.session_state.gedrag_events:
    df_events = pd.DataFrame(st.session_state.gedrag_events)
    
    df_pivot = df_events.groupby(["Leerder", "Tipe"]).size().unstack(fill_value=0)
    for col in ["Positief", "Negatief"]:
        if col not in df_pivot.columns:
            df_pivot[col] = 0
            
    df_leerder_opsomming = df_pivot.reset_index()
    df_punte = df_events.groupby("Leerder")["Punte"].sum().reset_index(name="Totale Gedragspunte")
    df_leerder_finaal = pd.merge(df_leerder_opsomming, df_punte, on="Leerder")

    st.markdown("#### 📊 Gedragsverslag & Visualisering")
    
    t1, t2, t3, t4, t5 = st.tabs([
        "🏃 Opsomming per Leerder", 
        "📈 Grafieke & Analise", 
        "📄 PDF Leerder-Verslag", 
        "📋 Alle Voorvalle (Tydlyn)", 
        "⚠️ Ouer-Verslag Data"
    ])
    
    with t1:
        st.dataframe(df_leerder_finaal, use_container_width=True)
        
    with t2:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("**Positief vs Negatief per Leerder**")
            fig_bar = px.bar(
                df_leerder_opsomming, 
                x="Leerder", 
                y=["Positief", "Negatief"], 
                barmode="group",
                color_discrete_map={"Positief": "#2a9d8f", "Negatief": "#e76f51"},
                template="plotly_dark"
            )
            fig_bar.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=80))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_g2:
            st.markdown("**Verdeling van Gedragstipes**")
            df_gedrag_counts = df_events["Gedrag"].value_counts().reset_index()
            df_gedrag_counts.columns = ["Gedrag", "Aantal"]
            fig_pie = px.pie(
                df_gedrag_counts, 
                names="Gedrag", 
                values="Aantal", 
                hole=0.4,
                template="plotly_dark"
            )
            fig_pie.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with t3:
        st.markdown("**Genereer Individuele PDF Verslag vir Ouers**")
        gekoose_leerder = st.selectbox("Kies 'n Leerder:", options=sorted(list(student_dict.keys())))
        
        df_spec_student = df_events[df_events["Leerder"] == gekoose_leerder]
        
        if not df_spec_student.empty:
            pdf_bytes = genereer_leerder_pdf(gekoose_leerder, df_spec_student, opvoeder_naam, klas_naam)
            st.download_button(
                label=f"📄 Laai PDF Verslag af vir {gekoose_leerder}",
                data=pdf_bytes,
                file_name=f"{gekoose_leerder}_Gedragsverslag.pdf",
                mime="application/pdf"
            )
        else:
            st.info(f"Geen inskrywings vir {gekoose_leerder} om 'n PDF te genereer nie.")

    with t4:
        st.dataframe(df_events, use_container_width=True)
        
    with t5:
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
