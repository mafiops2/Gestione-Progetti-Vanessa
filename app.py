import io
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
st.markdown(
    "Foglio interattivo con colorazione dinamica in base alle scadenze e ai"
    " pagamenti."
)

# ---------------------------------------------------------
# 1. INIZIALIZZAZIONE DEL DATABASE IN MEMORIA
# ---------------------------------------------------------
if "data" not in st.session_state:
  st.session_state.data = pd.DataFrame({
      "ID_Progetto": ["PRJ-001", "PRJ-002", "PRJ-003"],
      "Cliente": ["Mario Rossi", "Studio Bianchi Srl", "Verdi Design"],
      "Nome_Progetto": [
          "Ristrutturazione Cucina",
          "Consulenza Arredo",
          "Salotto Moderno",
      ],
      "Valore": [15000.0, 8500.0, 12000.0],
      "Data_Acquisizione": ["2026-01-10", "2026-02-15", "2026-03-01"],
      "Ha_Provvigione": [True, True, True],
      "Perc_Provvigione": [10.0, 12.0, 10.0],
      # Campi secondari
      "Data_Termine": ["2026-03-30", "2026-04-15", "2026-05-01"],
      "Data_Emissione_Fattura": ["2026-04-01", "2026-03-01", "2026-02-01"],
      "Numero_Fattura": ["FAT-2026-01", "FAT-2026-02", "FAT-2026-03"],
      "Data_Scadenza_Fattura": ["2026-05-01", "2026-03-15", "2026-02-28"],
      "Data_Pagamento": ["", "", "2026-02-20"],
      "Fattura_Pagamento_Provvigione": ["", "PROV-01", ""],
  })

df = st.session_state.data


# ---------------------------------------------------------
# 2. FUNZIONE PER CALCOLI AUTOMATICI
# ---------------------------------------------------------
def calcola_campi(dataframe):
  dataframe["Provvigione_Euro"] = dataframe.apply(
      lambda row: row["Valore"] * (row["Perc_Provvigione"] / 100)
      if row["Ha_Provvigione"]
      else 0.0,
      axis=1,
  )
  return dataframe


df = calcola_campi(df)


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
      "Provvigione (%)", min_value=0.0, max_value=100.0, step=1.0, value=10.0
  )

  submitted = st.form_submit_button("Aggiungi Progetto")
  if submitted:
    if cli and nom_p:
      nuova_riga = {
          "ID_Progetto": f"PRJ-{len(df)+1:03d}",
          "Cliente": cli,
          "Nome_Progetto": nom_p,
          "Valore": val,
          "Data_Acquisizione": str(data_acq),
          "Ha_Provvigione": ha_prov,
          "Perc_Provvigione": perc_prov if ha_prov else 0.0,
          "Data_Termine": "",
          "Data_Emissione_Fattura": "",
          "Numero_Fattura": "",
          "Data_Scadenza_Fattura": "",
          "Data_Pagamento": "",
          "Fattura_Pagamento_Provvigione": "",
      }
      st.session_state.data = pd.concat(
          [df, pd.DataFrame([nuova_riga])], ignore_index=True
      )
      st.sidebar.success("Progetto aggiunto con successo!")
      st.rerun()
    else:
      st.sidebar.error("Inserisci almeno Cliente e Nome Progetto.")


# ---------------------------------------------------------
# 4. FUNZIONE DI COLORAZIONE RIGHE (Stile Excel condizionale)
# ---------------------------------------------------------
def colora_righe(row):
  oggi = pd.Timestamp(datetime.today().date())

  num_fatt = str(row.get("Numero_Fattura", "")).strip()
  data_scad = pd.to_datetime(
      row.get("Data_Scadenza_Fattura", ""), errors="coerce"
  )
  data_pag = str(row.get("Data_Pagamento", "")).strip()
  prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

  # 1. Riga azzurra se la manager ha inserito la fattura per la provvigione
  if prov_fatt and prov_fatt != "" and prov_fatt.lower() != "nan":
    return ["background-color: #e0f2fe"] * len(row)  # Azzurro chiaro

  # 2. Riga verde se la fattura è pagata
  if data_pag and data_pag != "" and data_pag.lower() != "nan":
    return ["background-color: #dcfce7"] * len(row)  # Verde chiaro

  # Se non c'è fattura (numero fattura vuoto) -> Riga bianca
  if not num_fatt or num_fatt == "" or num_fatt.lower() == "nan":
    return ["background-color: #ffffff"] * len(row)  # Bianco

  # C'è fattura ma NON è pagata: controlliamo la scadenza
  if pd.notna(data_scad):
    if oggi > data_scad:
      return ["background-color: #fee2e2"] * len(row)  # Rosso chiaro (scaduta)
    else:
      return ["background-color: #fce7f3"] * len(row)  # Rosa chiaro (non scaduta)

  return ["background-color: #ffffff"] * len(row)


# ---------------------------------------------------------
# 5. TABELLA INTERATTIVA CON COLORI E MODIFICHE
# ---------------------------------------------------------
st.subheader("📋 Tabella Gestionale con Colorazione Dinamica")
st.markdown("""
**Legenda Colori:**
* ⬜ **Bianco:** Nessuna fattura emessa
* 🩷 **Rosa:** Fattura emessa, non pagata (scadenza non superata)
* 🟥 **Rosso:** Fattura non pagata (scadenza SUPERATA)
* 🟩 **Verde:** Fattura pagata
* 🟦 **Azzurro:** Fattura provvigione manager inserita
""")

# Editor della tabella
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    disabled=["ID_Progetto", "Provvigione_Euro"],
)

st.session_state.data = calcola_campi(edited_df)
df = st.session_state.data

# Visualizzazione della tabella applicando gli stili di colore
st.markdown("### Visualizzazione Tabella Colorata")
styled_table = df.style.apply(colora_righe, axis=1)
st.dataframe(styled_table, use_container_width=True)

# ---------------------------------------------------------
# 6. SEZIONE STATISTICHE E GRAFICI (Divisi per Mese e Anno)
# ---------------------------------------------------------
st.divider()
st.subheader("📊 Estrazioni Statistiche e Riassunti")

if not df.empty:
  df_stat = df.copy()
  df_stat["Acquisizione_YM"] = pd.to_datetime(
      df_stat["Data_Acquisizione"], errors="coerce"
  ).dt.to_period("M")
  df_stat["Fatturazione_YM"] = pd.to_datetime(
      df_stat["Data_Emissione_Fattura"], errors="coerce"
  ).dt.to_period("M")

  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Valore Totale Ordini", f"€ {df_stat['Valore'].sum():,.2f}")
  col2.metric(
      "Totale Fatturato",
      f"€ {df_stat[df_stat['Numero_Fattura'] != '']['Valore'].sum():,.2f}",
  )
  col3.metric(
      "Da Fatturare (Ordini)",
      f"€ {df_stat[df_stat['Numero_Fattura'] == '']['Valore'].sum():,.2f}",
  )
  col4.metric(
      "Provvigioni Totali (Luana)",
      f"€ {df_stat['Provvigione_Euro'].sum():,.2f}",
  )

  st.markdown("### 📅 Analisi Temporale (per Mese e Anno)")

  if df_stat["Acquisizione_YM"].notna().any():
    st.markdown("**1. Valore Acquisizioni per Mese/Anno**")
    pivot_acq = (
        df_stat.groupby(df_stat["Acquisizione_YM"].astype(str))["Valore"]
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

# ---------------------------------------------------------
# 7. ESPORTAZIONE IN EXCEL
# ---------------------------------------------------------
st.divider()
st.subheader("📥 Esportazione Dati")
if not df.empty:


  @st.cache_data
  def convert_df_to_excel(df_to_save):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df_to_save.to_excel(writer, index=False, sheet_name="Gestione_Progetti")
    return output.getvalue()


  excel_data = convert_df_to_excel(df)
  st.download_button(
      label="Scarica il file completo in formato Excel (.xlsx)",
      data=excel_data,
      file_name="gestione_progetti_clienti_provvigioni.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )
