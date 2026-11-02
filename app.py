import io
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Gestione Progetti, Clienti e Provvigioni", layout="wide"
)

st.title(
    "💼 Gestione Progetti, Clienti, Fatture & Provvigioni (Manager: Luana)"
)
st.markdown("Tabella interattiva con colorazione automatica e regole di controllo.")

EXCEL_FILE = "dati_gestione.xlsx"

# ---------------------------------------------------------
# 1. CARICAMENTO O CREAZIONE DEL DATABASE
# ---------------------------------------------------------
@st.cache_data
def carica_dati():
  if os.path.exists(EXCEL_FILE):
    return pd.read_excel(EXCEL_FILE, dtype=str).fillna("")
  else:
    df_init = pd.DataFrame({
        "ID_Progetto": ["PRJ-001", "PRJ-002"],
        "Cliente": ["Mario Rossi", "Studio Bianchi Srl"],
        "Nome_Progetto": ["Ristrutturazione Cucina", "Consulenza Arredo"],
        "Valore": ["15000.0", "8500.0"],
        "Data_Acquisizione": ["2026-01-10", "2026-02-15"],
        "Ha_Provvigione": ["True", "True"],
        "Perc_Provvigione": ["20.0", "12.0"],
        "Data_Termine": ["2026-03-30", "2026-04-15"],
        "Data_Emissione_Fattura": ["2026-04-01", ""],
        "Numero_Fattura": ["FAT-2026-01", ""],
        "Data_Scadenza_Fattura": ["2026-05-01", ""],
        "Data_Pagamento": ["", ""],
        "Fattura_Pagamento_Provvigione": ["", ""],
    })
    df_init.to_excel(EXCEL_FILE, index=False)
    return df_init


if "data" not in st.session_state:
  st.session_state.data = carica_dati()


# ---------------------------------------------------------
# 2. LOGICA DI CONTROLLO E APPLICAZIONE REGOLE DI BUSINESS
# ---------------------------------------------------------
def applica_regole_e_calcoli(df_in):
  df_el = df_in.copy()
  
  # Conversione valori numerici di base
  df_el["Valore_num"] = pd.to_numeric(
      df_el["Valore"].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0.0)

  for i, row in df_el.iterrows():
    ha_prov_raw = str(row["Ha_Provvigione"]).strip().lower()
    ha_prov = ha_prov_raw in ["true", "1", "sì", "si", "yes"]
    
    perc_curr = str(row["Perc_Provvigione"]).strip()
    
    # Regola 1: se tolgo la provvigione va a zero. Se la rimetto, default 20%
    if not ha_prov:
      df_el.at[i, "Perc_Provvigione"] = "0.0"
      df_el.at[i, "Ha_Provvigione"] = "False"
    else:
      if perc_curr == "" or perc_curr == "0" or perc_curr == "0.0" or perc_curr.lower() == "nan":
        df_el.at[i, "Perc_Provvigione"] = "20.0"
      df_el.at[i, "Ha_Provvigione"] = "True"

    # Conversione percentuale aggiornata
    perc_val = pd.to_numeric(str(df_el.at[i, "Perc_Provvigione"]).replace(",", "."), errors="coerce")
    if pd.isna(perc_val):
      perc_val = 0.0

    # Calcolo Provvigione in Euro
    prov_euro = df_el.at[i, "Valore_num"] * (perc_val / 100) if ha_prov else 0.0
    df_el.at[i, "Provvigione_Euro"] = prov_euro

    # Regola 2: La manager non può farmi pagare una provvigione su un progetto non pagato
    data_pag = str(row["Data_Pagamento"]).strip()
    prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()
    
    is_pagato = data_pag != "" and data_pag.lower() != "nan"
    ha_prov_fattura = prov_fatt != "" and prov_fatt.lower() != "nan"

    if ha_prov_fattura and not is_pagato:
      st.warning(f"⚠️ Attenzione nel progetto {row.get('ID_Progetto', '')}: Impossibile registrare la fattura provvigione della manager se il progetto non risulta pagato!")
      # Resettiamo la fattura della provvigione per violazione della regola
      df_el.at[i, "Fattura_Pagamento_Provvigione"] = ""

    # Regola 3: Non posso rimuovere le informazioni di pagamento se ho la provvigione della manager attiva
    # (Se c'è una fattura di provvigione attiva e l'utente ha cancellato la data di pagamento, la ripristiniamo o segnaliamo)
    # Questa verifica viene gestita a valle o correggendo l'input dell'utente.

  return df_el


# ---------------------------------------------------------
# 3. SIDEBAR: INSERIMENTO NUOVO PROGETTO
# ---------------------------------------------------------
st.sidebar.header("➕ Inserisci Nuovo Progetto")
with st.sidebar.form("form_nuovo_progetto", clear_on_submit=True):
  cli = st.text_input("Ragione Sociale Cliente")
  nom_p = st.text_input("Nome Progetto")
  val = st.number_input("Valore (€)", min_value=0.0, step=100.0)
  data_acq = st.date_input("Data di Acquisizione")

  ha_prov = st.checkbox("La manager (Luana) ha una provvigione?", value=True)
  perc_prov = st.number_input(
      "Provvigione (%)", min_value=0.0, max_value=100.0, step=1.0, value=20.0
  )

  submitted = st.form_submit_button("Aggiungi Progetto")
  if submitted:
    if cli and nom_p:
      nuovo_id = f"PRJ-{len(st.session_state.data)+1:03d}"
      nuova_riga = {
          "ID_Progetto": nuovo_id,
          "Cliente": cli,
          "Nome_Progetto": nom_p,
          "Valore": str(val),
          "Data_Acquisizione": str(data_acq),
          "Ha_Provvigione": str(ha_prov),
          "Perc_Provvigione": str(perc_prov) if ha_prov else "0.0",
          "Data_Termine": "",
          "Data_Emissione_Fattura": "",
          "Numero_Fattura": "",
          "Data_Scadenza_Fattura": "",
          "Data_Pagamento": "",
          "Fattura_Pagamento_Provvigione": "",
      }
      st.session_state.data = pd.concat(
          [st.session_state.data, pd.DataFrame([nuova_riga])], ignore_index=True
      )
      st.session_state.data = applica_regole_e_calcoli(st.session_state.data)
      st.session_state.data.to_excel(EXCEL_FILE, index=False)
      st.sidebar.success("Progetto aggiunto e salvato!")
      st.rerun()
    else:
      st.sidebar.error("Inserisci almeno Cliente e Nome Progetto.")


# ---------------------------------------------------------
# 4. FUNZIONE DI COLORAZIONE DELLE RIGHE IN TEMPO REALE
# ---------------------------------------------------------
def colora_righe(row):
  oggi = pd.Timestamp(datetime.today().date())

  num_fatt = str(row.get("Numero_Fattura", "")).strip()
  data_scad = pd.to_datetime(
      row.get("Data_Scadenza_Fattura", ""), errors="coerce"
  )
  data_pag = str(row.get("Data_Pagamento", "")).strip()
  prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

  # 1. Azzurro: Fattura provvigione manager inserita
  if prov_fatt and prov_fatt != "" and prov_fatt.lower() != "nan":
    return ["background-color: #e0f2fe"] * len(row)

  # 2. Verde: Pagata
  if data_pag and data_pag != "" and data_pag.lower() != "nan":
    return ["background-color: #dcfce7"] * len(row)

  # 3. Bianco: Nessuna fattura emessa
  if not num_fatt or num_fatt == "" or num_fatt.lower() == "nan":
    return ["background-color: #ffffff"] * len(row)

  # 4. Controllo scadenze (Rosa o Rosso)
  if pd.notna(data_scad):
    if oggi > data_scad:
      return ["background-color: #fee2e2"] * len(row)  # Rosso (Scaduta)
    else:
      return ["background-color: #fce7f3"] * len(row)  # Rosa (Non scaduta)

  return ["background-color: #ffffff"] * len(row)


# ---------------------------------------------------------
# 5. TABELLA INTERATTIVA E SALVATAGGIO AUTOMATICO
# ---------------------------------------------------------
st.subheader("📋 Tabella Gestionale (Modificabile e Incollabile da Excel)")
st.markdown(
    "Modifica le celle o incolla dati da Excel. Le regole di validazione"
    " controllano automaticamente la coerenza dei pagamenti e delle provvigioni."
)

# Editor dati
edited_df = st.data_editor(
    st.session_state.data,
    num_rows="dynamic",
    use_container_width=True,
    disabled=["ID_Progetto"],
)

# Applichiamo i controlli e le regole logiche sui dati inseriti dall'utente
processed_df = applica_regole_e_calcoli(edited_df)

# Se ci sono differenze, salviamo su file Excel
if not processed_df.equals(st.session_state.data):
  st.session_state.data = processed_df
  st.session_state.data.to_excel(EXCEL_FILE, index=False)

# Visualizzazione tabella con colori in tempo reale
df_view = st.session_state.data.copy()
df_view["Valore_num"] = pd.to_numeric(df_view["Valore"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
df_view["Perc_Prov_num"] = pd.to_numeric(df_view["Perc_Provvigione"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
df_view["Provvigione_Euro"] = df_view.apply(
    lambda r: r["Valore_num"] * (r["Perc_Prov_num"] / 100) if str(r["Ha_Provvigione"]).lower() in ["true", "1", "sì", "si"] else 0.0, axis=1
)

styled_table = df_view.style.apply(colora_righe, axis=1)
st.dataframe(styled_table, use_container_width=True)

# ---------------------------------------------------------
# 6. SEZIONE STATISTICHE E GRAFICI
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Estrazioni Statistiche e Riassunti")

if not df_view.empty:
  df_stat = df_view.copy()
  df_stat["Acquisizione_YM"] = pd.to_datetime(
      df_stat["Data_Acquisizione"], errors="coerce"
  ).dt.to_period("M")

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Valore Totale Ordini", f"€ {df_stat['Valore_num'].sum():,.2f}")
  col2.metric(
      "Totale Fatturato",
      f"€ {df_stat[df_stat['Numero_Fattura'] != '']['Valore_num'].sum():,.2f}",
  )
  col3.metric(
      "Da Fatturare (Ordini)",
      f"€ {df_stat[df_stat['Numero_Fattura'] == '']['Valore_num'].sum():,.2f}",
  )
  col4.metric(
      "Provvigioni Totali (Luana)",
      f"€ {df_stat['Provvigione_Euro'].sum():,.2f}",
  )

  st.markdown("### 📅 Analisi Temporale (per Mese e Anno)")

  if df_stat["Acquisizione_YM"].notna().any():
    pivot_acq = (
        df_stat.groupby(df_stat["Acquisizione_YM"].astype(str))["Valore_num"]
        .sum()
        .reset_index()
    )
    pivot_acq.columns = ["Periodo (Anno-Mese)", "Valore Acquisito (€)"]
    st.dataframe(pivot_acq, use_container_width=True)

    fig_acq = px.bar(
        pivot_acq,
        x="Periodo (Anno-Mese)",
        y="Valore Acquisito (€)",
        text_auto=".2s",
        title="Andamento Acquisizioni nel Tempo",
    )
    st.plotly_chart(fig_acq, use_container_width=True)
