import streamlit as st
import pandas as pd
import datetime
import pytz
import io
import os
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.express as px
from fpdf import FPDF

st.set_page_config(page_title="Laerskool Swartland - Gr.7 KT Klasdissipline", layout="wide")

# Swartland Kleurskema & Styl
st.markdown("""
    <style>
    header[data-testid="stHeader"], .stAppHeader {
        display: none !important;
    }
    
    .stAppViewMain {
        padding-top: 5px !important;
    }

    .stApp {
        background-color: #002147 !important;
        color: #ffffff !important;
    }

    /* Input velde: skoon wit agtergrond met donker teks */
    .stTextInput input, .stTextArea textarea {
        color: #002147 !important;
        background-color: #ffffff !important;
        font-weight: 600 !important;
        border: 2px solid #FFD700 !important;
        border-radius: 6px !important;
    }

    /* Standaard Knoppies Styl */
    .stButton>button {
        width: 100%;
        background-color: #001530 !important;
        color: #FFD700 !important;
        font-size: 11px !important;
        font-weight: bold !important;
        border: 1px solid #FFD700 !important;
        border-radius: 6px !important;
        padding: 4px 6px !important;
        height: 36px !important;
        transition: all 0.2s ease-in-out !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* Cursor Hover effek */
    .stButton>button:hover {
        background-color: #FFD700 !important;
        color: #002147 !important;
        transform: scale(1.02) !important;
        box-shadow: 0px 0px 8px rgba(255, 215, 0, 0.7) !important;
        cursor: pointer !important;
    }

    h1, h2, h3, h4, label, p {
        color: #ffffff !important;
        margin-bottom: 0.1rem !important;
    }

    .app-footer {
        text-align: center;
        color: #FFD700 !important;
        font-size: 11px;
        padding: 10px 0px 5px 0px;
        margin-top: 15px;
        border-top: 1px solid #FFD700;
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

# --- KOPSTUK MET LAERSKOOL SWARTLAND TEMA & LOGO ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    logo_pad = "swartland_logo.png"
    if os.path.exists(logo_pad):
        st.image(logo_pad, width=90)
    else:
        st.image("https://raw.githubusercontent.com/streamlit/st-image/main/images/cat.jpg", width=90)
with col_title:
    st.markdown("<h1 style='color: #FFD700 !important; font-size: 26px; margin-top: 5px;'>LAERSKOOL SWARTLAND</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #ffffff !important; font-size: 16px;'>🏫 Gr.7 KT Klasdissipline & Gedragsmonitor</h3>", unsafe_allow_html=True)

st.divider()

# --- GRATIS WHATSAPP SKAKEL GENERATOR ---
def skep_whatsapp_skakel(selnommer, leerder_naam, tipe, gedrag, opvoeder, nota=""):
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

Hierdie is 'n {tipe.lower()} kennisgewing van Laerskool Swartland rakende *{leerder_naam}* in {opvoeder} se klas.

{ikoon} *Gedrag/Aanmoediging:* {gedrag}
📅 *Datum/Tyd:* {tyd_nou}
📝 *Opmerking:* {nota if nota else 'Geen verdere opmerkings nie.'}

Vriendelike groete,
{opvoeder}
Laerskool Swartland"""

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
        msg['From'] = f"{opvoeder} - Laerskool Swartland <{sender_email}>"
        msg['To'] = ontvanger_epos
        msg['Subject'] = f"Laerskool Swartland Gedragskennisgewing: {leerder_naam}"

        body = f"""Beste Ouer,

Hierdie is 'n outomatiese kennisgewing van Laerskool Swartland rakende {leerder_naam} in {opvoeder} se klas.

Gedrag Aangemeld: {gedrag}
Datum/Tyd: {datetime.datetime.now(pytz.timezone('Africa/Johannesburg')).strftime('%Y-%m-%d %H:%M')}
Opmerking: {nota if nota else 'Geen verdere opmerkings nie.'}

Vriendelike groete,
{opvoeder}
Laerskool Swartland
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
    
    pdf.cell(0, 10, f"Laerskool Swartland - Gedragsverslag: {leerder_naam}", new_x="LMARGIN", new_y="NEXT", align="C")
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
    pdf.multi_cell(0, 5, "Hierdie verslag is outomaties geskep deur Laerskool Swartland se Klasdissipline Stelsel.")
    
    return bytes(pdf.output())

# --- DEFAULT LEERDERLYST MET BEIDE SELNOMMER & EPOS ---
default_leerders_met_kontak = """Burger Frederick, 0825442210, cornel.loubser@gmail.com
Carelse Anna-Marie, 0716825677, carelsequinten@gmail.com
Carstens Simon, 0723984064, carin@seedgbn.co.za
Claassen JJ, 0829529901, jmhclaassen@gmail.com
Coetzee Zoë, 0625236510, chenitavdw@gmail.com
Conradie Christel, 0829216737, marian.conradie@gmail.com
De Lange Chantenique, 0840796702, annekedel.2112@gmail.com
Geldenhuys Lani, 0736217513, Bkskoonmaakmiddels@gmail.com
Haak Wilrich, 0737101754, stefaniehaak3@gmail.com
Jenneke Kian, 0716866946, jennekesimone@gmail.com
Keffers Phoenix, 0612732319, mkeffers30@gmail.com
Krugel Willem, 0792437277, willem@voorbeeld.co.za
Lakey Lenvan, 0732147054, lakeyevangileen@gmail.com
Lewies Jolynn, 0651194642, jolynn@voorbeeld.co.za
Mostert Caleb, 0820753949, JacMost1982@gmail.com
Munnik Aniecke, 0826009955, nelita_dewet@yahoo.com
Nackerdien Fariah, 0739412620, Kautharnackerdien8@gmail.com
Roscher Lianke, 0823427576, nicolivanwyk@yahoo.com
Smith Tayo, 0823701140, jmichelle.smith02@gmail.com
Strydom El-Jay, 0730955552, Fredelenestrydom21@gmail.com
Swanepoel Henko, 0832290356, anzkeswanepoel@gmail.com
Taylor Theart, 0766546735, beofox@gmail.com
Van der Westhuizen Laylah, 0781791747, laylah@voorbeeld.co.za
Van Tonder Dia, 0849517558, anisavantonder@gmail.com
Van Wyk Carah, 0824251990, cyrajadevanwyk123@gmail.com
Vogel Jaco, 0764160926, Janien@kbooks.co.za
Walters Yvonne, 0835663059, fm@waltersgrp.co.za
Wijgergangs Jayden, 0824511227, Renewijgergangs@gmail.com
Willers Lilly, 0722441618, arendimoller@yahoo.com
Williams Ethan, 0682151915, ethan@voorbeeld.co.za"""

# --- INSTELINGS ---
with st.expander("⚙️ Klas Instellings & Ouer Kontak Bestuur", expanded=False):
    col_k1, col_k2, col_k3, col_k4 = st.columns([1.5, 1.5, 1, 1])
    klas_naam = col_k1.text_input("Klas", value="Gr.7 KT")
    opvoeder_naam = col_k2.text_input("Opvoeder", value="Mnr. Toerien")
    
    stuur_wa_aktief = col_k3.checkbox("Skep WhatsApp Skakels", value=True)
    stuur_eposse_aktief = col_k4.checkbox("Stuur Outomatiese E-posse", value=False)
    
    st.markdown("**Opdateer Leerderlyste (Formaat: Naam, Selfoonnommer, E-posadres):**")
    raw_leerders = st.text_area("Leerder lys:", value=default_leerders_met_kontak, height=180)
    
    student_dict = {}
    for line in raw_leerders.split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 1 and parts[0]:
            naam = parts[0]
            sel = parts[1] if len(parts) > 1 else ""
            epos = parts[2] if len(parts) > 2 else ""
            student_dict[naam] = {"sel": sel, "epos": epos}

# Funksie om voorvalle te registreer
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
        
        if sheet:
            try:
                sheet.append_row([t_min, klas_naam, opvoeder_naam, leerder, uer_sel, uer_epos, tipe, aksie, punte, nota])
            except Exception as e:
                st.error(f"Kon nie opstoor in Google Sheet vir {leerder}: {e}")
        
        if stuur_wa_aktief and uer_sel:
            wa_url = skep_whatsapp_skakel(uer_sel, leerder, tipe, aksie, opvoeder_naam, nota)
            if wa_url:
                nuwe_wa_skakels.append({
                    "id": f"{leerder}_{datetime.datetime.now().timestamp()}",
                    "leerder": leerder,
                    "tipe": tipe,
                    "aksie": aksie,
                    "url": wa_url,
                    "kontak": uer_sel
                })
        
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

# --- POP-UP DIALOG FUNKSIE VIR GEDRAGSTOEKENNING ---
@st.dialog("📝 Toeekenning van Gedrag / Punte")
def open_gedrag_dialog(gekoose_leerders):
    st.markdown(f"**Gekoose Leerder(s):** {', '.join(gekoose_leerders)}")
    pop_nota = st.text_input("Spesifieke Opmerking / Nota (Opsioneel):", key="dialog_nota")
    
    st.markdown("---")
    st.markdown("**Kies Gedragstipe:**")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("🟢 **Positief (+1)**")
        if st.button("🤝 Hulpvaardig", key="pop_hulp"):
            log_gedrag_massa(gekoose_leerders, "Positief", "Hulpvaardig", 1, pop_nota)
        if st.button("🌟 Goeie waardes", key="pop_waardes"):
            log_gedrag_massa(gekoose_leerders, "Positief", "Goeie waardes", 1, pop_nota)
            
    with col_p2:
        st.markdown("🔴 **Negatief (-1)**")
        if st.button("🗣️ Gesels konstant", key="pop_gesels"):
            log_gedrag_massa(gekoose_leerders, "Negatief", "Gesels konstant", -1, pop_nota)
        if st.button("⚠️ Swak dissipline", key="pop_dissipline"):
            log_gedrag_massa(gekoose_leerders, "Negatief", "Swak dissipline", -1, pop_nota)
        if st.button("🚩 Waarskuwing", key="pop_waarsk"):
            log_gedrag_massa(gekoose_leerders, "Negatief", "Waarskuwing", -1, pop_nota)

# --- MASSAKIESER (MULTI-SELECT REGMERKIES) ---
st.markdown("#### 👥 GROEP / MASSA SELEKSIE")
gekoose_groep = st.multiselect(
    "Merk een of meer leerders vir gelyktydige toekenning:",
    options=sorted(list(student_dict.keys())),
    help="Kies verskeie leerders om gelyktydige inskrywings te maak."
)

if gekoose_groep:
    if st.button(f"⚡ Kliek hier om Aksie Toe te pas op {len(gekoose_groep)} Leerder(s)"):
        open_gedrag_dialog(gekoose_groep)

st.divider()

# --- KLASREKENAAR RASTER (5 KOLOMME VIR 6 RYE IS SPASIËRING OPTIMAAL) ---
st.markdown("#### 🏃 KLASLEERDERS RASTER (5 Kolomme x 6 Rye)")
st.caption("💡 Kliek op enige leerder se naam om die Pop-Up venster oop te maak.")

leerders_lys_gesorteer = sorted(list(student_dict.keys()))
cols = st.columns(5)

for idx, leerder in enumerate(leerders_lys_gesorteer):
    col_target = cols[idx % 5]
    with col_target:
        if st.button(f"👤 {leerder}", key=f"btn_card_{leerder}"):
            open_gedrag_dialog([leerder])

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

# --- WHATSAPP STUUR BANNER MET INDIVIDUELE VERWYDERING ---
if st.session_state.laaste_wa_skakels:
    col_wa_hdr, col_wa_clr = st.columns([4, 1])
    with col_wa_hdr:
        st.markdown("### 📲 Stuur WhatsApp Kennisgewings vir Laaste Inskrywings:")
    with col_wa_clr:
        if st.button("🗑️ Maak Alles Skoon"):
            st.session_state.laaste_wa_skakels = []
            st.rerun()
            
    # Vertoon en verwyder individuele knoppies
    oorblewende_skakels = []
    for wa_data in st.session_state.laaste_wa_skakels:
        tipe_ikoon = "🟢" if wa_data['tipe'] == "Positief" else "🔴"
        col_txt, col_btn = st.columns([3, 1])
        with col_txt:
            st.markdown(f"{tipe_ikoon} **{wa_data['leerder']}** ({wa_data['kontak']}) - *{wa_data['aksie']}*")
        with col_btn:
            if st.button(f"📲 Stuur & Verwyder", key=f"btn_wa_{wa_data['id']}"):
                js_code = f"<script>window.open('{wa_data['url']}', '_self');</script>"
                st.components.v1.html(js_code, height=0)
            else:
                oorblewende_skakels.append(wa_data)
                
    if len(oorblewende_skakels) != len(st.session_state.laaste_wa_skakels):
        st.session_state.laaste_wa_skakels = oorblewende_skakels
        st.rerun()

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

st.markdown("<div class='app-footer'>Laerskool Swartland • Klasdissipline & Gedragsmonitor - Gr.7 KT</div>", unsafe_allow_html=True)
