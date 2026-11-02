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

  # Conversione valore numerico
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
        val_perc = 20.0  # Default 20%

    perc_list.append(str(val_perc))
    val_euro = row["Valore_num"] * (val_perc / 100.0) if ha_prov else 0.0
    prov_euro_list.append(str(val_euro))

    # Controllo coerenza pagamenti manager
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

  # Parsing data in formato italiano DD/MM/YYYY
  data_scad_raw = str(row.get("Data_Scadenza_Fattura", "")).strip()
  data_scad = pd.to_datetime(data_scad_raw, format="%d/%m/%Y", errors="coerce")
  if pd.isna(data_scad):
    data_scad = pd.to_datetime(data_scad_raw, errors="coerce")

  data_pag = str(row.get("Data_Pagamento", "")).strip()
  prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

  if prov_fatt and prov_fatt != "" and prov_fatt.lower() != "nan":
    return ["background-color: #e0f2fe"] * len(row)  # Azzurro
  if data_pag and data_pag != "" and data_pag.lower() !=
