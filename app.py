from datetime import datetime
import os

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Vaneblandy", layout="wide", initial_sidebar_state="collapsed"
)

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
EXCEL_TMP = "dati_gestione.tmp.xlsx"

PERC_DEFAULT = 20.0  # percentuale proposta quando si attiva la provvigione

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

DATE_COLS = [
    "Data_Acquisizione",
    "Data_Termine",
    "Data_Emissione_Fattura",
    "Data_Scadenza_Fattura",
    "Data_Pagamento",
]

STR_COLS = [
    "ID_Progetto",
    "Cliente",
    "Nome_Progetto",
    "Numero_Fattura",
    "Fattura_Pagamento_Provvigione",
]

NUM_COLS = ["Valore", "Perc_Provvigione", "Provvigione_Euro"]


# ---------------------------------------------------------------- utilità dati
def parse_date(val):
    if pd.isna(val) or str(val).strip() in ["", "None", "NaT", "nan"]:
        return pd.NaT
    if isinstance(val, (pd.Timestamp, datetime)):
        return pd.Timestamp(val).normalize()
    s = str(val).strip()
    for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return pd.to_datetime(s, format=fmt).normalize()
        except ValueError:
            pass
    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    return dt.normalize() if pd.notna(dt) else pd.NaT


def format_date_str(val):
    dt = parse_date(val)
    return "" if pd.isna(dt) else dt.strftime("%d-%m-%Y")


def _to_num(series, decimals):
    return (
        pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")
        .fillna(0.0)
        .round(decimals)
    )


def normalizza_tipi(df_in):
    df = df_in.copy()
    df["Valore"] = _to_num(df["Valore"], 2)
    df["Perc_Provvigione"] = _to_num(df["Perc_Provvigione"], 1)
    df["Provvigione_Euro"] = _to_num(df["Provvigione_Euro"], 2)

    df["Ha_Provvigione"] = df["Ha_Provvigione"].apply(
        lambda x: x is True
        or str(x).strip().lower() in ["true", "1", "sì", "si", "vero", "yes"]
    ).astype(bool)

    for d_col in DATE_COLS:
        df[d_col] = pd.to_datetime(df[d_col].apply(parse_date))

    for s_col in STR_COLS:
        df[s_col] = (
            df[s_col]
            .fillna("")
            .astype(str)
            .replace(["nan", "None", "NaT"], "")
            .str.strip()
        )
    return df


def salva_dati(df_in):
    """Scrive su file temporaneo e poi sostituisce l'originale.
    Restituisce (ok, messaggio_errore)."""
    try:
        df_save = df_in[COLUMNS].copy()
        for d_col in DATE_COLS:
            df_save[d_col] = df_save[d_col].apply(format_date_str)
        df_save.to_excel(EXCEL_TMP, index=False)
        os.replace(EXCEL_TMP, EXCEL_FILE)
        return True, ""
    except Exception as exc:  # file aperto in Excel, disco pieno, ecc.
        return False, f"Salvataggio non riuscito ({exc}). Chiudi il file Excel e riprova."


def carica_dati():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, dtype=str).fillna("")
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[COLUMNS]
    else:
        df = pd.DataFrame({c: [] for c in COLUMNS})
    return normalizza_tipi(df)


def df_uguali(df1, df2):
    if len(df1) != len(df2):
        return False
    for col in COLUMNS:
        if col in DATE_COLS:
            if df1[col].apply(format_date_str).tolist() != df2[col].apply(format_date_str).tolist():
                return False
        elif col in NUM_COLS:
            if df1[col].round(2).tolist() != df2[col].round(2).tolist():
                return False
        elif df1[col].tolist() != df2[col].tolist():
            return False
    return True


def calcola_stato(row, oggi):
    num_fatt = str(row["Numero_Fattura"]).strip()
    if str(row["Fattura_Pagamento_Provvigione"]).strip() != "":
        return "🔵 Provvigione fatturata"
    if pd.notna(row["Data_Pagamento"]):
        return "🟢 Pagata"
    if num_fatt == "":
        return "⚪ Senza fattura"
    if pd.notna(row["Data_Scadenza_Fattura"]) and oggi > row["Data_Scadenza_Fattura"]:
        return "🔴 Scaduta"
    return "🟠 Da incassare"


# ----------------------------------------------------------------------- stato
if "data" not in st.session_state:
    st.session_state.data = carica_dati()
if "editor_key" not in st.session_state:
    st.session_state.editor_key = 0
if "msg_errore" not in st.session_state:
    st.session_state.msg_errore = ""


def mostra_errore(msg):
    st.session_state.msg_errore = msg


@st.dialog("Conferma eliminazione")
def conferma_eliminazione_dialog(idx):
    riga = st.session_state.data.loc[idx]
    st.write(
        f"Vuoi eliminare definitivamente il progetto **{riga['Nome_Progetto']}** "
        f"del cliente **{riga['Cliente']}** ({riga['ID_Progetto']})?"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Conferma elimina", type="primary", width="stretch"):
            nuovo = st.session_state.data.drop(index=idx).reset_index(drop=True)
            ok, err = salva_dati(nuovo)
            if ok:
                st.session_state.data = nuovo
                st.session_state.editor_key += 1
            else:
                mostra_errore(err)
            st.rerun()
    with col2:
        if st.button("Annulla", width="stretch"):
            st.rerun()


# --------------------------------------------------------------------- sidebar
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
            "Provvigione (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            value=PERC_DEFAULT,
        )

        submitted = st.form_submit_button("Inserisci in tabella")
        if submitted:
            if not (cli.strip() and nom_p.strip()):
                st.error("Compila Cliente e Nome Progetto.")
            elif data_term < data_acq:
                st.error("La data di termine non può precedere quella di acquisizione.")
            elif val <= 0:
                st.error("Il valore del progetto deve essere maggiore di zero.")
            else:
                df_curr = st.session_state.data
                existing_nums = [
                    int(str(i).split("-")[1])
                    for i in df_curr["ID_Progetto"]
                    if "-" in str(i) and str(i).split("-")[1].isdigit()
                ]
                nuovo_id = f"PRJ-{max(existing_nums, default=0) + 1:03d}"

                eff_perc = perc_prov if ha_prov_toggle else 0.0
                eff_euro = round(val * eff_perc / 100.0, 2)

                nuova_riga = pd.DataFrame(
                    [
                        {
                            "ID_Progetto": nuovo_id,
                            "Cliente": cli.strip(),
                            "Nome_Progetto": nom_p.strip(),
                            "Valore": float(val),
                            "Data_Acquisizione": pd.Timestamp(data_acq).normalize(),
                            "Ha_Provvigione": bool(ha_prov_toggle),
                            "Perc_Provvigione": float(eff_perc),
                            "Provvigione_Euro": float(eff_euro),
                            "Data_Termine": pd.Timestamp(data_term).normalize(),
                            "Data_Emissione_Fattura": pd.NaT,
                            "Numero_Fattura": "",
                            "Data_Scadenza_Fattura": pd.NaT,
                            "Data_Pagamento": pd.NaT,
                            "Fattura_Pagamento_Provvigione": "",
                        }
                    ]
                )
                nuovo = normalizza_tipi(pd.concat([df_curr, nuova_riga], ignore_index=True))
                ok, err = salva_dati(nuovo)
                if ok:
                    st.session_state.data = nuovo
                    st.session_state.editor_key += 1
                    st.rerun()
                else:
                    st.error(err)

# --------------------------------------------------------------------- tabella
st.title("Vaneblandy")

if st.session_state.msg_errore:
    st.toast(st.session_state.msg_errore, icon="⚠️")
    st.session_state.msg_errore = ""

oggi = pd.Timestamp(datetime.today().date())
df_display = st.session_state.data.copy()
df_display.insert(0, "Stato", df_display.apply(lambda r: calcola_stato(r, oggi), axis=1))

st.caption(
    "🔵 provvigione fatturata · 🟢 pagata · 🔴 scaduta · 🟠 da incassare · ⚪ senza fattura"
)

column_cfg = {
    "Stato": st.column_config.TextColumn("Stato", disabled=True, width="medium"),
    "ID_Progetto": st.column_config.TextColumn("ID", disabled=True),
    "Cliente": st.column_config.TextColumn("Cliente"),
    "Nome_Progetto": st.column_config.TextColumn("Progetto"),
    "Valore": st.column_config.NumberColumn("Valore (€)", format="%.2f"),
    "Data_Acquisizione": st.column_config.DateColumn("Data Acq.", format="DD-MM-YYYY"),
    "Ha_Provvigione": st.column_config.CheckboxColumn("Provvigione"),
    "Perc_Provvigione": st.column_config.NumberColumn("Provv. %", format="%.1f"),
    "Provvigione_Euro": st.column_config.NumberColumn(
        "Valore Provv. (€)", format="%.2f", disabled=True
    ),
    "Data_Termine": st.column_config.DateColumn("Data Termine", format="DD-MM-YYYY"),
    "Data_Emissione_Fattura": st.column_config.DateColumn("Data Fattura", format="DD-MM-YYYY"),
    "Numero_Fattura": st.column_config.TextColumn("N. Fattura"),
    "Data_Scadenza_Fattura": st.column_config.DateColumn("Scadenza Fatt.", format="DD-MM-YYYY"),
    "Data_Pagamento": st.column_config.DateColumn("Data Pagamento", format="DD-MM-YYYY"),
    "Fattura_Pagamento_Provvigione": st.column_config.TextColumn("Fatt. Provv. Manager"),
}

edited_df = st.data_editor(
    df_display,
    column_config=column_cfg,
    column_order=["Stato"] + COLUMNS,
    width="stretch",
    height=600,
    hide_index=True,
    num_rows="fixed",
    key=f"tabella_{st.session_state.editor_key}",
)

# ------------------------------------------------- validazione delle modifiche
old_df = st.session_state.data
edited = edited_df.drop(columns=["Stato"]).copy()
messaggi = []

# 1) campi obbligatori / numerici svuotati: si ripristina il valore precedente
for idx in edited.index:
    for col, nome in [("Valore", "Il valore"), ("Perc_Provvigione", "La percentuale")]:
        if pd.isna(edited.at[idx, col]):
            edited.at[idx, col] = old_df.at[idx, col]
            messaggi.append(f"{nome} non può essere vuoto ({old_df.at[idx, 'ID_Progetto']}).")
    for col, nome in [("Cliente", "Il cliente"), ("Nome_Progetto", "Il nome progetto")]:
        if str(edited.at[idx, col]).strip() in ["", "None", "nan"]:
            edited.at[idx, col] = old_df.at[idx, col]
            messaggi.append(f"{nome} non può essere vuoto ({old_df.at[idx, 'ID_Progetto']}).")

df_clean = normalizza_tipi(edited)
modificato = False

for idx in df_clean.index:
    old_row = old_df.loc[idx]

    # 2) coerenza tra le date
    row = df_clean.loc[idx]
    if pd.notna(row["Data_Acquisizione"]) and pd.notna(row["Data_Termine"]):
        if row["Data_Termine"] < row["Data_Acquisizione"]:
            df_clean.at[idx, "Data_Termine"] = old_row["Data_Termine"]
            messaggi.append("La data di termine non può precedere quella di acquisizione.")
    if pd.notna(row["Data_Emissione_Fattura"]) and pd.notna(row["Data_Scadenza_Fattura"]):
        if row["Data_Scadenza_Fattura"] < row["Data_Emissione_Fattura"]:
            df_clean.at[idx, "Data_Scadenza_Fattura"] = old_row["Data_Scadenza_Fattura"]
            messaggi.append("La scadenza non può precedere la data di emissione della fattura.")

    row = df_clean.loc[idx]
    if pd.notna(row["Data_Pagamento"]) and row["Numero_Fattura"] == "":
        df_clean.at[idx, "Data_Pagamento"] = old_row["Data_Pagamento"]
        messaggi.append("Per registrare il pagamento serve prima il numero di fattura.")

    # 3) provvigione
    row = df_clean.loc[idx]
    ha_prov = bool(row["Ha_Provvigione"])
    old_ha_prov = bool(old_row["Ha_Provvigione"])
    perc = float(row["Perc_Provvigione"])
    valore = float(row["Valore"])

    if not ha_prov:
        if perc != 0.0:
            df_clean.at[idx, "Perc_Provvigione"] = 0.0
            perc = 0.0
            modificato = True
    elif not old_ha_prov and perc == 0.0:
        # attivata ora: propongo la percentuale di default
        df_clean.at[idx, "Perc_Provvigione"] = PERC_DEFAULT
        perc = PERC_DEFAULT
        modificato = True

    nuovo_euro = round(valore * perc / 100.0, 2) if ha_prov else 0.0
    if float(row["Provvigione_Euro"]) != nuovo_euro:
        df_clean.at[idx, "Provvigione_Euro"] = nuovo_euro
        modificato = True

    # 4) fattura provvigione vs pagamento
    row = df_clean.loc[idx]
    data_pag = row["Data_Pagamento"]
    old_data_pag = old_row["Data_Pagamento"]
    prov_fatt = str(row["Fattura_Pagamento_Provvigione"]).strip()
    old_prov_fatt = str(old_row["Fattura_Pagamento_Provvigione"]).strip()

    if prov_fatt != "" and pd.isna(data_pag):
        if old_prov_fatt != "" and pd.notna(old_data_pag):
            df_clean.at[idx, "Data_Pagamento"] = old_data_pag
            messaggi.append(
                "Non puoi rimuovere la data di pagamento se è presente "
                "la fattura provvigione della manager."
            )
        else:
            df_clean.at[idx, "Fattura_Pagamento_Provvigione"] = ""
            messaggi.append(
                "La manager non può fatturare la provvigione su un "
                "progetto non ancora pagato."
            )

# ------------------------------------------------------------------- salvataggio
errori = bool(messaggi)
if modificato or errori or not df_uguali(df_clean, old_df):
    ok, err = salva_dati(df_clean)
    if ok:
        st.session_state.data = df_clean
    else:
        messaggi.append(err)
    if messaggi:
        mostra_errore(" · ".join(dict.fromkeys(messaggi)))  # senza duplicati
    if modificato or errori or not ok:
        st.session_state.editor_key += 1
    st.rerun()

# ------------------------------------------------------------------ eliminazione
if not st.session_state.data.empty:
    st.divider()
    with st.expander("Elimina un progetto"):
        opzioni = {
            idx: f"{r['ID_Progetto']} — {r['Cliente']} — {r['Nome_Progetto']}"
            for idx, r in st.session_state.data.iterrows()
        }
        scelta = st.selectbox(
            "Progetto da eliminare",
            options=list(opzioni.keys()),
            format_func=lambda i: opzioni[i],
            index=None,
            placeholder="Seleziona un progetto...",
        )
        if st.button("🗑️ Elimina selezionato", disabled=scelta is None):
            conferma_eliminazione_dialog(scelta)
