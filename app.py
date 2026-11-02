from datetime import datetime
import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vaneblandy", layout="wide")

EXCEL_FILE = "dati_gestione.xlsx"


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
        "Data_Acquisizione": ["10/01/2026", "15/02/2026"],
        "Ha_Provvigione": ["Sì", "Sì"],
        "Perc_Provvigione": ["10.0", "20.0"],
        "Provvigione_Euro": ["1500.0", "1700.0"],
        "Data_Termine": ["30/03/2026", "15/04/2026"],
        "Data_Emissione_Fattura": ["01/04/2026", ""],
        "Numero_Fattura": ["FAT-2026-01", ""],
        "Data_Scadenza_Fattura": ["01/05/2026", ""],
        "Data_Pagamento": ["", ""],
        "Fattura_Pagamento_Provvigione": ["", ""],
    })
    df_init.to_excel(EXCEL_FILE, index=False)
    return df_init


if "data" not in st.session_state:
  st.session_state.data = carica_dati()


def elabora_e_valida(df_in):
  df_el = df_in.copy()
  df_el["Valore_num"] = pd.to_numeric(
      df_el["Valore"].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0.0)

  ha_prov_list = []
  perc_list = []
  prov_euro_list = []

  for idx, row in df_el.iterrows():
    val_ha_prov = row.get("Ha_Provvigione", "Sì")
    if isinstance(val_ha_prov, bool):
      ha_prov = val_ha_prov
    else:
      ha_prov = str(val_ha_prov).strip().lower() in [
          "sì",
          "si",
          "true",
          "1",
          "yes",
      ]

    ha_prov_str = "Sì" if ha_prov else "No"
    ha_prov_list.append(ha_prov_str)

    raw_perc = str(row.get("Perc_Provvigione", "")).strip().replace(",", ".")
    val_perc = pd.to_numeric(raw_perc, errors="coerce")

    if not ha_prov:
      val_perc = 0.0
    else:
      if pd.isna(val_perc) or val_perc == 0.0:
        val_perc = 20.0

    perc_list.append(str(val_perc))
    val_euro = row["Valore_num"] * (val_perc / 100.0) if ha_prov else 0.0
    prov_euro_list.append(str(val_euro))

    data_pag = str(row.get("Data_Pagamento", "")).strip()
    prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

    if prov_fatt and prov_fatt != "" and prov_fatt.lower() != "nan":
      if not data_pag or data_pag == "" or data_pag.lower() == "nan":
        df_el.at[idx, "Fattura_Pagamento_Provvigione"] = ""
        st.warning(
            f"Riga {idx+1}: Impossibile registrare la provvigione se il"
            " progetto non risulta pagato."
        )

  df_el["Ha_Provvigione"] = ha_prov_list
  df_el["Perc_Provvigione"] = perc_list
  df_el["Provvigione_Euro"] = prov_euro_list
  return df_el


def colora_righe(row):
  oggi = pd.Timestamp(datetime.today().date())
  num_fatt = str(row.get("Numero_Fattura", "")).strip()

  data_scad_raw = str(row.get("Data_Scadenza_Fattura", "")).strip()
  data_scad = pd.to_datetime(data_scad_raw, format="%d/%m/%Y", errors="coerce")
  if pd.isna(data_scad):
    data_scad = pd.to_datetime(data_scad_raw, errors="coerce")

  data_pag = str(row.get("Data_Pagamento", "")).strip()
  prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

  if prov_fatt and prov_fatt != "" and prov_fatt.lower() != "nan":
    return ["background-color: #e0f2fe"] * len(row)  # Azzurro
  if data_pag and data_pag != "" and data_pag.lower() != "nan":
    return ["background-color: #dcfce7"] * len(row)  # Verde
  if not num_fatt or num_fatt == "" or num_fatt.lower() == "nan":
    return ["background-color: #ffffff"] * len(row)  # Bianco
  if pd.notna(data_scad):
    if oggi > data_scad:
      return ["background-color: #fee2e2"] * len(row)  # Rosso
    else:
      return ["background-color: #fce7f3"] * len(row)  # Rosa
  return ["background-color: #ffffff"] * len(row)


# --- TITOLO ESATTO ---
st.title("Vaneblandy")

# --- MENU LATERALE A SCOMPARSA (CLICCANDO SUL PULSANTE ESPANDIBILE) ---
with st.sidebar:
  with st.expander("➕ Inserisci Nuovo Progetto", expanded=False):
    with st.form("form_nuovo_progetto", clear_on_submit=True):
      cli = st.text_input("Ragione Sociale Cliente")
      nom_p = st.text_input("Nome Progetto")
      val = st.number_input("Valore (€)", min_value=0.0, step=100.0)
      data_acq = st.date_input("Data di Acquisizione")

      ha_prov_toggle = st.toggle(
          "La manager (Luana) ha una provvigione?", value=True
      )
      perc_prov = st.number_input(
          "Provvigione (%)", min_value=0.0, max_value=100.0, step=1.0, value=20.0
      )

      # Tasto esplicito per confermare l'inserimento
      submitted = st.form_submit_button("Conferma Inserimento")
      if submitted:
        if cli and nom_p:
          nuovo_id = f"PRJ-{len(st.session_state.data)+1:03d}"
          data_acq_str = data_acq.strftime("%d/%m/%Y")
          nuova_riga = {
              "ID_Progetto": nuovo_id,
              "Cliente": cli,
              "Nome_Progetto": nom_p,
              "Valore": str(val),
              "Data_Acquisizione": data_acq_str,
              "Ha_Provvigione": "Sì" if ha_prov_toggle else "No",
              "Perc_Provvigione": str(perc_prov) if ha_prov_toggle else "0.0",
              "Provvigione_Euro": (
                  str(val * (perc_prov / 100.0)) if ha_prov_toggle else "0.0"
              ),
              "Data_Termine": "",
              "Data_Emissione_Fattura": "",
              "Numero_Fattura": "",
              "Data_Scadenza_Fattura": "",
              "Data_Pagamento": "",
              "Fattura_Pagamento_Provvigione": "",
          }
          st.session_state.data = pd.concat(
              [st.session_state.data, pd.DataFrame([nuova_riga])],
              ignore_index=True,
          )
          cols_to_save = [
              c
              for c in st.session_state.data.columns
              if c not in ["Valore_num", "Provvigione_Euro"]
          ]
          st.session_state.data[cols_to_save].to_excel(EXCEL_FILE, index=False)
          st.success("Progetto aggiunto con successo!")
          st.rerun()
        else:
          st.error("Inserisci almeno Cliente e Nome Progetto.")

# --- TABELLA SUBITO SOTTO IL TITOLO ---
edited_df = st.data_editor(
    st.session_state.data,
    num_rows="dynamic",
    use_container_width=True,
    disabled=["ID_Progetto"],
)

processed_df = elabora_e_valida(edited_df)

cols_to_save = [
    c for c in processed_df.columns if c not in ["Valore_num", "Provvigione_Euro"]
]
clean_saved_df = processed_df[cols_to_save]

if not clean_saved_df.equals(st.session_state.data):
  st.session_state.data = clean_saved_df
  st.session_state.data.to_excel(EXCEL_FILE, index=False)

styled_table = processed_df.style.apply(colora_righe, axis=1)
st.dataframe(styled_table, use_container_width=True, hide_index=True)
