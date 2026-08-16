"""
Simulatore immobiliare — entry point.

Esecuzione locale:  streamlit run home.py
Deploy come webapp: stesso codice, nessuna modifica richiesta
(Streamlit Community Cloud, oppure container su Cloud Run).
"""

import streamlit as st

st.set_page_config(page_title="Simulatore immobiliare", layout="wide")

st.sidebar.info(
    "I risultati sono stime indicative basate sui dati inseriti e sulle assunzioni del modello. "
    "Non costituiscono consulenza fiscale, finanziaria, immobiliare o legale."
)

pagina_affitto = st.Page("affitto.py", title="Affitto", icon="🏠", default=True)
pagina_acquisto = st.Page("acquisto.py", title="Acquisto e confronto", icon="🏦")

navigazione = st.navigation([pagina_affitto, pagina_acquisto])
navigazione.run()
