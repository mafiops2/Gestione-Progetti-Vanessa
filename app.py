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


def normalizza_tipi(df_in):
    df = df_in.copy()
    df["Valore"] = (
        pd.to_numeric(
            df["Valore"].astype(str).str.replace(",", "."), errors="coerce"
        )
        .fillna(0.0)
        .round(2)
    )
    df["Ha_Provvigione"] = df["Ha_Provvigione"].apply(
        lambda x: True
        if (
            x is True
            or str(x).strip().lower() in ["true", "1", "sì", "si", "vero", "yes"]
        )
        else False
    )
    df["Perc_Provvigione"] = (
        pd.to_numeric(
            df["Perc_Provvigione"].astype(str).str.replace(",", "."),
            errors="coerce",
        )
        .fillna(0.0)
        .round(1)
    )
    df["Provvigione_Euro"] = (
        pd.to_numeric(
            df["Provvigione_Euro"].astype(str).str.replace(",", "."),
            errors="coerce",
        )
        .fillna(0.0)
        .round(2)
    )

    for d_col in DATE_COLS:
        df[d_col] = df[d_col].apply(parse_date)

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
    df_save = df_in[COLUMNS].copy()
    for d_col in DATE_COLS:
        df_save[d_col] = df_save[d_col].apply(format_date_str)
    df_save.to_excel(EXCEL_FILE, index=False)


def carica_dati():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, dtype=str).fillna("")
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[COLUMNS]
    else:
        df = pd.DataFrame(
            {
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
            }
        )
        salva_dati(df)
    return normalizza_tipi(df)


def df_uguali(df1, df2):
    if len(df1) != len(df2):
        return False
    for col in COLUMNS:
        if col in DATE_COLS:
            s1 = df1[col].apply(format_date_str).tolist()
            s2 = df2[col].apply(format_date_str).tolist()
            if s1 != s2:
                return False
        elif col in ["Valore", "Perc_Provvigione", "Provvigione_Euro"]:
            s1 = df1[col].round(2).tolist()
            s2 = df2[col].round(2).tolist()
            if s1 != s2:
                return False
        else:
            s1 = df1[col].tolist()
            s2 = df2[col].tolist()
            if s1 != s2:
                return False
    return True


if "data" not in st.session_state:
    st.session_state.data = carica_dati()
if "editor_key" not in st.session_state:
    st.session_state.editor_key = 0
if "msg_errore" not in st.session_state:
    st.session_state.msg_errore = ""
if "riga_da_eliminare" not in st.session_state:
    st.session_state.riga_da_eliminare = None


@st.dialog("Conferma eliminazione")
def conferma_eliminazione_dialog(idx):
    riga = st.session_state.data.loc[idx]
    st.write(
        f"Vuoi eliminare definitivamente il progetto **{riga['Nome_Progetto']}** "
        f"del cliente **{riga['Cliente']}** ({riga['ID_Progetto']})?"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Conferma elimina", type="primary", use_container_width=True):
            st.session_state.data = st.session_state.data.drop(index=idx).reset_index(
                drop=True
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
                eff_euro = (
                    round(val * (eff_perc / 100.0), 2) if ha_prov_toggle else 0.0
                )

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

                st.session_state.data = pd.concat(
                    [df_curr, nuova_riga], ignore_index=True
                )
                salva_dati(st.session_state.data)
                st.session_state.editor_key += 1
                st.rerun()
            else:
                st.error(
                    "Compila tutti i campi obbligatori (Cliente, Progetto, "
                    "Data Acquisizione e Data Termine)."
                )

st.title("Vaneblandy")

if st.session_state.msg_errore:
    st.toast(st.session_state.msg_errore, icon="⚠️")
    st.session_state.msg_errore = ""
