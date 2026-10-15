import streamlit as st
import google.genai as genai
from google.genai import types
import urllib.parse
import time

# --- CONFIGURAZIONE CHIAVE API INTEGRATA ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# --- CONFIGURAZIONE PAGINA STREAMLIT ---
st.set_page_config(
    page_title="NutriMind Salute",
    page_icon="🥗",
    layout="wide"
)

# --- CSS PERSONALIZZATO: RIQUADRO BLU SCURO E CORREZIONE MARGINI ---
st.markdown("""
<style>
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
    }
    
    /* Riquadro del Titolo Principale in BLU SCURO con testo chiaro */
    .title-box-darkblue {
        background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%);
        border: 2px solid #3b82f6;
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.15);
        margin-top: 10px;
        margin-bottom: 25px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE DI SUPPORTO CON LOOP AUTOMATICO (RETRY) ---
def chiama_gemini_con_retry(client, model, contents, max_tentativi=3):
    tentativo = 0
    while tentativo < max_tentativi:
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            return response
        except Exception as e:
            err_str = str(e)
            if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                tentativo += 1
                if tentativo >= max_tentativi:
                    raise e
                # Attesa crescente prima di ripetere automaticamente la richiesta
                time.sleep(2 * tentativo)
            else:
                raise e

# --- TITOLO PRINCIPALE IN RIQUADRO BLU SCURO ---
st.markdown("""
<div class="title-box-darkblue">
    <h1 style="color: #ffffff; margin: 0; font-size: 2.2rem;">🥗 NutriMind e Salute</h1>
    <h3 style="color: #93c5fd; margin: 6px 0 0 0; font-weight: 500;"> La scienza nel piatto, la salute nella mente.</h3>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR: PROFILO CLINICO E SPORTIVO ---
with st.sidebar:
    st.header("👤 Profilo Clinico & Sportivo")
    
    patologie_comuni = [
        "Meteorismo / Gonfiore addominale",
        "Sindrome del Colon Irritabile",
        "Ansia / Stress cronico",
        "Depressione / Calo dell'umore",
        "Ipertensione (Pressione alta)",
        "Ipotensione (Pressione bassa)",
        "Fibromi / Squilibri ormonali",
        "Reflusso gastroesofageo",
        "Insulino-resistenza / Diabete"
    ]
    patologie_selezionate = st.multiselect("Patologie e Condizioni:", patologie_comuni)
    altre_patologie = st.text_input("Altre patologie o dettagli clinici:")
    
    fa_sport = st.radio("Pratichi attività sportiva?", ["No", "Sì"])
    sport_praticato = ""
    intensita_sport = ""
    if fa_sport == "Sì":
        sport_praticato = st.text_input("Sport praticato (es. Calcio, Volley, Corsa, Nuoto):")
        intensita_sport = st.select_slider("Intensità:", options=["Lieve", "Moderata", "Agonistica / Intensa"])

# --- DISPENSARIA INGREDIENTI ---
st.subheader("🛒 Prodotti in tuo possesso")
ingredienti = st.text_area(
    "Elenca gli ingredienti a tua disposizione:",
    placeholder="Es. Zucchine, farina, uova, ecc..",
    key="input_ingredienti"
)

def genera_prompt(ingredienti, patologie, altre_pat, fa_sport, sport, intensita):
    patologie_str = ", ".join(patologie)
    if altre_pat:
        patologie_str += f", {altre_pat}"
    if not patologie_str:
        patologie_str = "Nessuna patologia dichiarata"
        
    info_sport = "Nessun esercizio fisico praticato"
    if fa_sport == "Sì":
        info_sport = f"Pratica {sport} con intensità {intensita}"

    return f"""
Sei un'equipe multidisciplinare (Medico, Nutrizionista, Psicologo, Fisiologo dello Sport).
L'utente fornisce un elenco di ingredienti e il proprio profilo.

--- PROFILO UTENTE ---
- Patologie/Condizioni: {patologie_str}
- Attività sportiva: {info_sport}
- Ingredienti inseriti: {ingredienti}

--- ISTRUZIONI DI RISPOSTA ---
Genera l'analisi strutturata esattamente nelle seguenti sezioni Markdown:
### 1. 🔍 ANALISI SCIENTIFICA DETTAGLIATA INGREDIENTE PER INGREDIENTE
Analizza OGNI SINGOLO PRODOTTO inserito dall'utente (nessuno escluso, inclusi zuccheri e farine raffinate):
- Perché è raccomandato (o obbligatorio) il BIOLOGICO per questo specifico prodotto.
- Cosa contiene la versione NON biologica o raffinata e perché è dannosa.
- Impatto clinico e psicologico.

### 2. 🛑 ALIMENTI VIETATI E PERICOLOSI (DA EVITARE ASSOLUTAMENTE)
- Evidenzia gli ingredienti con impatto NEGATIVO o VIETATO per le patologie o lo sport e spiega il motivo medico/digestivo.

### 3. ✅ ALIMENTI CONSIGLIATI E BENEFICI
- Elenca gli ingredienti sani e funzionali tra quelli inseriti.

### 4. 🍽️ PIANO PASTI GIORNALIERO (Colazione, Pranzo, Merenda, Cena)
- Crea il menù usando SOLO gli ingredienti sani/consentiti.

### 5. 🧠 CONSIGLIO PSICO-NUTRIZIONALE E SPORTIVO
- Consigli pratici su idratazione, timing e gestione dello stress.
"""

# --- BOTTONE GENERAZIONE PIANO NUTRIZIONALE (CON LOOP DI RETRY) ---
if st.button("🚀 Genera Analisi e Piatti", type="primary"):
    if not ingredienti.strip():
        st.warning("⚠️ Inserisci almeno un ingrediente nella dispensaria.")
    else:
        try:
            with st.spinner("Analisi clinica, biologica e nutrizionale in corso (tentativo automatico in caso di traffico)..."):
                client = genai.Client(api_key=GEMINI_API_KEY)
                prompt_completo = genera_prompt(
                    ingredienti, patologie_selezionate, altre_patologie, 
                    fa_sport, sport_praticato, intensita_sport
                )
                
                response = chiama_gemini_con_retry(client, 'gemini-2.5-flash', prompt_completo)
                st.success("✅ Analisi completata con successo!")
                st.markdown(response.text)

        except Exception as e:
            st.error(f"Errore persistente durante la chiamata API: {e}")

st.divider()

# ==========================================
# SEZIONE A SÉ STANTE: DOVE ACQUISTARE I PRODOTTI
# ==========================================
st.header("📍 Dove acquistare i tuoi prodotti")
st.write("Verifica dove reperire i prodotti biologici indicati.")

col_citta, col_prod = st.columns(2)
with col_citta:
    citta_ricerca = st.text_input("Indica la tua Città:", value="Palermo", key="citta_negozi")
with col_prod:
    prodotti_ricerca = st.text_area("Prodotti biologici da cercare:", value=ingredienti, key="prodotti_negozi")

# --- BOTTONE RICERCA NEGOZI E GDO (CON LOOP DI RETRY) ---
if st.button("🔍 Cerca Negozi, Supermercati e Prodotti", type="secondary"):
    if not citta_ricerca.strip() or not prodotti_ricerca.strip():
        st.warning("⚠️ Inserisci sia la città che i prodotti da cercare.")
    else:
        with st.spinner("Ricerca punti vendita specializzati e reparti bio della GDO in corso (con ripetizione automatica se necessario)..."):
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                prompt_mappa = f"""
                L'utente si trova nella città di: {citta_ricerca}.
                Vuole acquistare i seguenti prodotti biologici: {prodotti_ricerca}.
                
                Fornisci una guida dettagliata indicando sia i **negozi biologici specializzati** sia le **grandi catene di supermercati della GDO** presenti in città (come Conad, Decò, Famila, Sisa, Coop, LIDL o simili) che dispongono di ampi scaffali e reparti dedicati al biologico dove è possibile trovare questi specifici articoli.
                Per ogni opzione (supermercato GDO o negozio bio), spiega quali tra i prodotti indicati si possono trovare più facilmente.
                """
                
                resp_mappa = chiama_gemini_con_retry(client, 'gemini-2.5-flash', prompt_mappa)
                st.markdown(resp_mappa.text)
                
                query_mappa = f"supermercati con reparti biologici e negozi bio {prodotti_ricerca} {citta_ricerca}"
                maps_link = f"https://www.google.com/maps/search/{urllib.parse.quote(query_mappa)}"
                st.markdown("---")
                st.markdown(f"### 🗺️ [Clicca qui per aprire la mappa interattiva dei negozi e supermercati GDO a {citta_ricerca}]({maps_link})")
                
            except Exception as e:
                st.error(f"Errore persistente durante la ricerca: {e}")
