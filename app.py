from datetime import datetime
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Vaneblandy", layout="wide", initial_sidebar_state="collapsed"
)

# Colore barra laterale leggermente più scuro dello sfondo e pulizia spazi
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: #e6e9ef;
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

EXCEL_FILE = "dati_gestione.xlsx"

COLUMNS = [
    "ID_Progetto",
    "Cliente",
    "Nome_Progetto",
    "Valore",
    "Data_Acquisizione",
    "Ha_Provvigione",
    "Perc_Provvigione",
    "Provvigione_Euro",
    "Data_Termine",
    "Data_Emissione_Fattura",
    "Numero_Fattura",
    "Data_Scadenza_Fattura",
    "Data_Pagamento",
    "Fattura_Pagamento_Provvigione",
]


def parse_date(val):
  if pd.isna(val) or str(val).strip() in ["", "None", "NaT", "nan"]:
    return pd.NaT
  s = str(val).strip()
  for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
    try:
      return pd.to_datetime(s, format=fmt)
    except:
      pass
  return pd.to_datetime(s, dayfirst=True, errors="coerce")


def format_date_str(val):
  dt = parse_date(val)
  if pd.isna(dt):
    return ""
  return dt.strftime("%d-%m-%Y")


def carica_dati():
  if os.path.exists(EXCEL_FILE):
    df = pd.read_excel(EXCEL_FILE, dtype=str).fillna("")
    for col in COLUMNS:
      if col not in df.columns:
        df[col] = ""
    df = df[COLUMNS]
  else:
    df = pd.DataFrame({
        "ID_Progetto": ["PRJ-001", "PRJ-002"],
        "Cliente": ["Mario Rossi", "Studio Bianchi Srl"],
        "Nome_Progetto": ["Ristrutturazione Cucina", "Consulenza Arredo"],
        "Valore": [15000.0, 8500.0],
        "Data_Acquisizione": ["10-01-2026", "15-02-2026"],
        "Ha_Provvigione": [True, True],
        "Perc_Provvigione": [10.0, 20.0],
        "Provvigione_Euro": [1500.0, 1700.0],
        "Data_Termine": ["30-03-2026", "15-04-2026"],
        "Data_Emissione_Fattura": ["01-04-2026", ""],
        "Numero_Fattura": ["FAT-2026-01", ""],
        "Data_Scadenza_Fattura": ["01-05-2026", ""],
        "Data_Pagamento": ["", ""],
        "Fattura_Pagamento_Provvigione": ["", ""],
    })
    salva_dati(df)
  return normalizza_tipi(df)


def normalizza_tipi(df_in):
  df = df_in.copy()
  df["Valore"] = pd.to_numeric(
      df["Valore"].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0.0)
  df["Ha_Provvigione"] = df["Ha_Provvigione"].apply(
      lambda x: True
      if (
          x is True
          or str(x).strip().lower() in ["true", "1", "sì", "si", "vero", "yes"]
      )
      else False
  )
  df["Perc_Provvigione"] = pd.to_numeric(
      df["Perc_Provvigione"].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0.0)
  df["Provvigione_Euro"] = pd.to_numeric(
      df["Provvigione_Euro"].astype(str).str.replace(",", "."), errors="coerce"
  ).fillna(0.0)

  for d_col in [
      "Data_Acquisizione",
      "Data_Termine",
      "Data_Emissione_Fattura",
      "Data_Scadenza_Fattura",
      "Data_Pagamento",
  ]:
    df[d_col] = df[d_col].apply(parse_date)

  for s_col in [
      "ID_Progetto",
      "Cliente",
      "Nome_Progetto",
      "Numero_Fattura",
      "Fattura_Pagamento_Provvigione",
  ]:
    df[s_col] = (
        df[s_col].fillna("").astype(str).replace(["nan", "None", "NaT"], "")
    )

  return df


def salva_dati(df_in):
  df_save = df_in[COLUMNS].copy()
  for d_col in [
      "Data_Acquisizione",
      "Data_Termine",
      "Data_Emissione_Fattura",
      "Data_Scadenza_Fattura",
      "Data_Pagamento",
  ]:
    df_save[d_col] = df_save[d_col].apply(format_date_str)
  df_save.to_excel(EXCEL_FILE, index=False)


if "data" not in st.session_state:
  st.session_state.data = carica_dati()
if "editor_key" not in st.session_state:
  st.session_state.editor_key = 0
if "msg_errore" not in st.session_state:
  st.session_state.msg_errore = ""
if "riga_da_eliminare" not in st.session_state:
  st.session_state.riga_da_eliminare = None


# --- FINESTRA DI DIALOGO PER CONFERMA ELIMINAZIONE ---
@st.dialog("Conferma eliminazione")
def conferma_eliminazione_dialog(idx):
  riga = st.session_state.data.loc[idx]
  st.write(
      f"Sei sicuro di voler eliminare il progetto **{riga['Nome_Progetto']}**"
      f" del cliente **{riga['Cliente']}** ({riga['ID_Progetto']})?"
  )
  col1, col2 = st.columns(2)
  with col1:
    if st.button(
        "Conferma elimina", type="primary", use_container_width=True
    ):
      st.session_state.data = (
          st.session_state.data.drop(index=idx).reset_index(drop=True)
      )
      salva_dati(st.session_state.data)
      st.session_state.riga_da_eliminare = None
      st.session_state.editor_key += 1
      st.rerun()
  with col2:
    if st.button("Annulla", use_container_width=True):
      st.session_state.riga_da_eliminare = None
      st.session_state.editor_key += 1
      st.rerun()


# --- MENU LATERALE A SCOMPARSA: "Nuovo progetto" ---
with st.sidebar:
  st.header("Nuovo progetto")
  with st.form("form_nuovo_progetto", clear_on_submit=True):
    cli = st.text_input("Ragione Sociale Cliente")
    nom_p = st.text_input("Nome Progetto")
    val = st.number_input("Valore (€)", min_value=0.0, step=100.0)
    data_acq = st.date_input(
        "Data di Acquisizione", value=datetime.today(), format="DD-MM-YYYY"
    )
    data_term = st.date_input(
        "Data di Termine", value=datetime.today(), format="DD-MM-YYYY"
    )
    ha_prov_toggle = st.toggle("Ha Provvigione", value=True)
    perc_prov = st.number_input(
        "Provvigione (%)", min_value=0.0, max_value=100.0, step=1.0, value=20.0
    )

    submitted = st.form_submit_button("Inserisci in tabella")
    if submitted:
      if cli.strip() and nom_p.strip() and data_acq and data_term:
        df_curr = st.session_state.data
        existing_nums = [
            int(str(i).split("-")[1])
            for i in df_curr["ID_Progetto"]
            if "-" in str(i) and str(i).split("-")[1].isdigit()
        ]
        next_num = max(existing_nums, default=0) + 1
        nuovo_id = f"PRJ-{next_num:03d}"

        eff_perc = perc_prov if ha_prov_toggle else 0.0
        eff_euro = round(val * (eff_perc / 100.0), 2) if ha_prov_toggle else 0.0

        nuova_riga = pd.DataFrame([{
            "ID_Progetto": nuovo_id,
            "Cliente": cli.strip(),
            "Nome_Progetto": nom_p.strip(),
            "Valore": float(val),
            "Data_Acquisizione": pd.to_datetime(data_acq),
            "Ha_Provvigione": bool(ha_prov_toggle),
            "Perc_Provvigione": float(eff_perc),
            "Provvigione_Euro": float(eff_euro),
            "Data_Termine": pd.to_datetime(data_term),
            "Data_Emissione_Fattura": pd.NaT,
            "Numero_Fattura": "",
            "Data_Scadenza_Fattura": pd.NaT,
            "Data_Pagamento": pd.NaT,
            "Fattura_Pagamento_Provvigione": "",
        }])

        st.session_state.data = pd.concat(
            [df_curr, nuova_riga], ignore_index=True
        )
        salva_dati(st.session_state.data)
        st.session_state.editor_key += 1
        st.rerun()
      else:
        st.error(
            "Compila tutti i campi obbligatori (Cliente, Progetto, Data"
            " Acquisizione e Data Termine)."
        )

# --- TITOLO E UNICA TABELLA SOTTOSTANTE ---
st.title("Vaneblandy")

if st.session_state.msg_errore:
  st.toast(st.session_state.msg_errore, icon="⚠️")
  st.session_state.msg_errore = ""

# Posizioniamo la colonna "Elimina" come PRIMA colonna a sinistra
df_display = st.session_state.data.copy()
df_display.insert(0, "Elimina", False)


def colora_righe(row):
  oggi = pd.Timestamp(datetime.today().date())
  num_fatt = str(row.get("Numero_Fattura", "")).strip()
  data_scad = row.get("Data_Scadenza_Fattura", pd.NaT)
  data_pag = row.get("Data_Pagamento", pd.NaT)
  prov_fatt = str(row.get("Fattura_Pagamento_Provvigione", "")).strip()

  if prov_fatt != "":
    color = "#e0f2fe"  # Azzurro: fattura provvigione manager presente
  elif pd.notna(data_pag):
    color = "#dcfce7"  # Verde: fattura pagata
  elif num_fatt == "":
    color = "#ffffff"  # Bianco: nessuna fattura
  elif pd.notna(data_scad) and oggi > pd.Timestamp(data_scad):
    color = "#fee2e2"  # Rosso: non pagata e scadenza superata
  else:
    color = "#fce7f3"  # Rosa: non pagata e scadenza non superata

  return [f"background-color: {color}; color: #000000"] * len(row)


styled_df = df_display.style.apply(colora_righe, axis=1)

column_cfg = {
    "Elimina": st.column_config.CheckboxColumn("🗑️", width="small"),
    "ID_Progetto": st.column_config.TextColumn("ID", disabled=True),
    "Cliente": st.column_config.TextColumn("Cliente"),
    "Nome_Progetto": st.column_config.TextColumn("Progetto"),
    "Valore": st.column_config.NumberColumn("Valore (€)", format="%.2f"),
    "Data_Acquisizione": st.column_config.DateColumn(
        "Data Acq.", format="DD-MM-YYYY"
    ),
    "Ha_Provvigione": st.column_config.CheckboxColumn("Ha_Provvigione"),
    "Perc_Provvigione": st.column_config.NumberColumn("Provv. %", format="%.1f"),
    "Provvigione_Euro": st.column_config.NumberColumn(
        "Valore Provv. (€)", format="%.2f", disabled=True
    ),
    "Data_Termine": st.column_config.DateColumn(
        "Data Termine", format="DD-MM-YYYY"
    ),
    "Data_Emissione_Fattura": st.column_config.DateColumn(
        "Data Fattura", format="DD-MM-YYYY"
    ),
    "Numero_Fattura": st.column_config.TextColumn("N. Fattura"),
    "Data_Scadenza_Fattura": st.column_config.DateColumn(
        "Scadenza Fatt.", format="DD-MM-YYYY"
    ),
    "Data_Pagamento": st.column_config.DateColumn(
        "Data Pagamento", format="DD-MM-YYYY"
    ),
    "Fattura_Pagamento_Provvigione": st.column_config.TextColumn(
        "Fatt. Provv. Luana"
    ),
}

# Ordine esplicito delle colonne con "Elimina" al primo posto
column_order = ["Elimina"] + COLUMNS

# UNICA TABELLA A SCHERMO
edited_df = st.data_editor(
    styled_df,
    column_config=column_cfg,
    column_order=column_order,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key=f"tabella_{st.session_state.editor_key}",
)

# 1. Gestione richiesta di eliminazione sulla prima colonna con finestra di conferma
if edited_df["Elimina"].any():
  idx_to_del = edited_df[edited_df["Elimina"]].index[0]
  st.session_state.riga_da_eliminare = idx_to_del

if st.session_state.riga_da_eliminare is not None:
  conferma_eliminazione_dialog(st.session_state.riga_da_eliminare)

# 2. Gestione modifiche, calcoli automatici e blocchi sulle provvigioni
df_clean = normalizza_tipi(edited_df.drop(columns=["Elimina"]))
old_df = st.session_state.data

modificato = False
errore_rilevato = False

for idx in df_clean.index:
  row = df_clean.loc[idx]
  old_row = old_df.loc[idx]

  ha_prov = bool(row["Ha_Provvigione"])
  old_ha_prov = bool(old_row["Ha_Provvigione"])
  perc = float(row["Perc_Provvigione"])
  valore = float(row["Valore"])

  # Se tolgo la provvigione va a 0; se la rimetto va di default a 20%
  if not ha_prov:
    if perc != 0.0:
      df_clean.at[idx, "Perc_Provvigione"] = 0.0
      perc = 0.0
      modificato = True
  else:
    if not old_ha_prov or perc == 0.0:
      df_clean.at[idx, "Perc_Provvigione"] = 20.0
      perc = 20.0
      modificato = True

  # Calcolo automatico valore provvigione
  nuovo_euro = round(valore * (perc / 100.0), 2) if ha_prov else 0.0
  if float(row["Provvigione_Euro"]) != nuovo_euro:
    df_clean.at[idx, "Provvigione_Euro"] = nuovo_euro
    modificato = True

  # Regole incrociate Pagamento Progetto <-> Fattura Provvigione Manager
  data_pag = row["Data_Pagamento"]
  old_data_pag = old_row["Data_Pagamento"]
  prov_fatt = str(row["Fattura_Pagamento_Provvigione"]).strip()
  old_prov_fatt = str(old_row["Fattura_Pagamento_Provvigione"]).strip()

  if prov_fatt != "" and pd.isna(data_pag):
    if old_prov_fatt != "" and pd.notna(old_data_pag):
      df_clean.at[idx, "Data_Pagamento"] = old_data_pag
      st.session_state.msg_errore = (
          "Non puoi rimuovere la data di pagamento se è presente la fattura"
          " provvigione della manager."
      )
      errore_rilevato = True
    else:
      df_clean.at[idx, "Fattura_Pagamento_Provvigione"] = ""
      st.session_state.msg_errore = (
          "La manager non può fatturare la provvigione su un progetto non"
          " ancora pagato."
      )
      errore_rilevato = True

if st.session_state.riga_da_eliminare is None and (
    modificato
    or errore_rilevato
    or not df_clean.astype(str).equals(old_df.astype(str))
):
  st.session_state.data = df_clean
  salva_dati(df_clean)
  st.session_state.editor_key += 1
  st.rerun()
