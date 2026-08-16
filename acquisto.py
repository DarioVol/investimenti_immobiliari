"""
Pagina "Acquisto e confronto": valuta se comprare un immobile (eventualmente a
mutuo, con notaio e arredo) e affittarlo è più conveniente che investire lo
stesso capitale proprio in BTP o in un indice azionario globale.
Entry point dell'app: home.py.
"""

import pandas as pd
import streamlit as st

import config
import calcolo
from formattazione import formatta_euro, formatta_percentuale


def render_sezione_acquisto() -> dict:
    st.subheader("Acquisto immobile")
    col1, col2 = st.columns(2)
    costo_immobile = col1.number_input("Prezzo di acquisto (€)", min_value=0, value=220000, step=5000)
    metratura = col2.number_input("Metratura (mq)", min_value=1, value=70, step=5)

    col1, col2 = st.columns(2)
    anno_costruzione = col1.number_input("Anno di costruzione", min_value=1900, max_value=2026, value=1985, step=1)
    tipo_comune = col2.selectbox("Tipo di comune (per IMU)", list(config.IMU_ALIQUOTA_PER_TIPO_COMUNE.keys()))

    return {
        "costo_immobile": costo_immobile,
        "metratura": metratura,
        "anno_costruzione": anno_costruzione,
        "aliquota_comunale_imu": config.IMU_ALIQUOTA_PER_TIPO_COMUNE[tipo_comune],
    }


def render_sezione_costi_accessori(costo_immobile: float) -> dict:
    st.subheader("Costi accessori")

    con_mutuo = st.checkbox("Mutuo", value=True)
    importo_mutuo = 0.0
    tasso_mutuo = config.MUTUO_TASSO_ANNUO_DEFAULT
    durata_mutuo = config.MUTUO_DURATA_ANNI_DEFAULT
    if con_mutuo:
        col1, col2, col3 = st.columns(3)
        percentuale_anticipo = col1.slider(
            "Anticipo (% sul prezzo)", min_value=0, max_value=100,
            value=int(config.MUTUO_PERCENTUALE_ANTICIPO_DEFAULT * 100),
        ) / 100
        tasso_mutuo = col2.number_input(
            "Tasso di interesse annuo (%)", min_value=0.0,
            value=config.MUTUO_TASSO_ANNUO_DEFAULT * 100, step=0.1,
        ) / 100
        durata_mutuo = col3.number_input(
            "Durata mutuo (anni)", min_value=1, max_value=40, value=config.MUTUO_DURATA_ANNI_DEFAULT, step=1,
        )
        anticipo = costo_immobile * percentuale_anticipo
        importo_mutuo = costo_immobile - anticipo
        st.caption(f"Anticipo: {formatta_euro(anticipo)} · Mutuo richiesto: {formatta_euro(importo_mutuo)}")
    else:
        anticipo = costo_immobile

    con_notaio = st.checkbox("Notaio e imposte d'atto", value=True)
    costo_notaio = 0.0
    if con_notaio:
        percentuale_notaio = st.number_input(
            "Notaio e imposte d'atto (% sul prezzo)", min_value=0.0,
            value=config.NOTAIO_PERCENTUALE_DEFAULT * 100, step=0.1,
        ) / 100
        costo_notaio = costo_immobile * percentuale_notaio
        st.caption(f"Costo stimato: {formatta_euro(costo_notaio)}")

    con_arredo = st.checkbox("Arredo", value=False)
    costo_arredo = 0.0
    if con_arredo:
        costo_arredo = st.number_input(
            "Costo arredo (€)", min_value=0.0, value=config.ARREDO_IMPORTO_DEFAULT, step=500.0,
        )

    capitale_proprio_iniziale = anticipo + costo_notaio + costo_arredo

    return {
        "importo_mutuo": importo_mutuo,
        "tasso_mutuo": tasso_mutuo,
        "durata_mutuo": int(durata_mutuo),
        "capitale_proprio_iniziale": capitale_proprio_iniziale,
    }


def render_sezione_canone() -> dict:
    st.subheader("Canone e tipologia di locazione")
    tipo_label = st.selectbox("Tipologia di locazione", list(config.TIPO_LOCAZIONE_LABELS.values()))
    tipo_locazione = next(k for k, v in config.TIPO_LOCAZIONE_LABELS.items() if v == tipo_label)

    if tipo_locazione == "lungo_termine":
        canone_mensile = st.number_input("Canone mensile (€)", min_value=0, value=800, step=50)
        canone_annuo = calcolo.calcola_canone_annuo_lungo_termine(canone_mensile)
    else:
        col1, col2 = st.columns(2)
        canone_giornaliero = col1.number_input(
            "Canone medio a notte (€)", min_value=0.0,
            value=config.AFFITTO_BREVE_CANONE_GIORNALIERO_DEFAULT, step=5.0,
        )
        percentuale_occupazione = col2.slider(
            "Giornate piene sull'anno (%)", min_value=0, max_value=100,
            value=int(config.AFFITTO_BREVE_PERCENTUALE_OCCUPAZIONE_DEFAULT * 100),
        ) / 100
        canone_annuo = calcolo.calcola_canone_annuo_breve(canone_giornaliero, percentuale_occupazione)
        st.caption(f"Canone annuo stimato: {formatta_euro(canone_annuo)}")

    return {"tipo_locazione": tipo_locazione, "canone_annuo": canone_annuo}


def render_sezione_fiscale(tipo_locazione: str) -> dict:
    st.subheader("Tassazione della locazione")

    if tipo_locazione == "breve":
        etichetta_aliquota = st.radio("Cedolare secca affitti brevi", list(config.CEDOLARE_BREVE_ALIQUOTE.keys()))
        return {
            "regime": "breve",
            "aliquota_breve": config.CEDOLARE_BREVE_ALIQUOTE[etichetta_aliquota],
            "aliquota_marginale_irpef": 0.0,
            "addizionali_irpef": 0.0,
        }

    regime_label = st.radio(
        "Regime fiscale",
        [v for k, v in config.REGIME_LABELS.items() if k in ("libero", "concordato", "irpef")],
    )
    regime = next(k for k, v in config.REGIME_LABELS.items() if v == regime_label)

    aliquota_marginale_irpef = 0.0
    addizionali_irpef = config.IRPEF_ADDIZIONALI_DEFAULT
    if regime == "irpef":
        col1, col2 = st.columns(2)
        etichetta_aliquota = col1.selectbox("Aliquota marginale IRPEF", list(config.IRPEF_ALIQUOTE_MARGINALI.keys()))
        aliquota_marginale_irpef = config.IRPEF_ALIQUOTE_MARGINALI[etichetta_aliquota]
        addizionali_irpef = col2.number_input(
            "Addizionali reg./com.", min_value=0.0, max_value=0.10,
            value=config.IRPEF_ADDIZIONALI_DEFAULT, step=0.001, format="%.3f",
        )

    return {
        "regime": regime,
        "aliquota_breve": None,
        "aliquota_marginale_irpef": aliquota_marginale_irpef,
        "addizionali_irpef": addizionali_irpef,
    }


def render_sezione_imu_tari(metratura: float, tipo_locazione: str) -> dict:
    st.subheader("IMU e TARI")
    col1, col2 = st.columns(2)
    rendita_catastale_eur_mq = col1.number_input(
        "Rendita catastale (€/mq/anno)", min_value=0.0,
        value=config.RENDITA_CATASTALE_EUR_MQ_DEFAULT, step=0.1,
    )
    tari_eur_mq = col2.number_input(
        "TARI (€/mq/anno)", min_value=0.0, value=config.TARI_EUR_MQ_ANNO_DEFAULT, step=0.1,
    )
    tari_a_carico_proprietario = st.checkbox(
        "TARI a carico del proprietario", value=(tipo_locazione == "breve"),
    )
    return {
        "rendita_catastale_eur_mq": rendita_catastale_eur_mq,
        "tari_eur_mq": tari_eur_mq,
        "tari_a_carico_proprietario": tari_a_carico_proprietario,
    }


def render_sezione_confronto() -> dict:
    st.subheader("Confronto con investimento alternativo")
    col1, col2, col3 = st.columns(3)

    tipo_label = col1.selectbox(
        "Investimento alternativo", list(config.TIPO_INVESTIMENTO_ALTERNATIVO_LABELS.values()),
    )
    tipo_investimento = next(
        k for k, v in config.TIPO_INVESTIMENTO_ALTERNATIVO_LABELS.items() if v == tipo_label
    )

    rendimento_btp_lordo = config.BTP_RENDIMENTO_LORDO_DEFAULT
    rendimento_reale_azionario = config.AZIONARIO_RENDIMENTO_REALE_DEFAULT
    inflazione_attesa = config.INFLAZIONE_ATTESA_DEFAULT

    if tipo_investimento == "btp":
        rendimento_btp_lordo = col2.number_input(
            "Rendimento BTP lordo (%)", min_value=0.0,
            value=config.BTP_RENDIMENTO_LORDO_DEFAULT * 100, step=0.1,
        ) / 100
    else:
        rendimento_reale_azionario = col2.number_input(
            "Rendimento reale azionario, sopra inflazione (%)", min_value=0.0,
            value=config.AZIONARIO_RENDIMENTO_REALE_DEFAULT * 100, step=0.1,
        ) / 100
        inflazione_attesa = col3.number_input(
            "Inflazione attesa (%)", min_value=0.0,
            value=config.INFLAZIONE_ATTESA_DEFAULT * 100, step=0.1,
        ) / 100

    col1, col2 = st.columns(2)
    etichetta_rivalutazione = col1.selectbox(
        "Rivalutazione immobile", list(config.RIVALUTAZIONE_IMMOBILE_OPZIONI.keys()), index=2,
    )
    rivalutazione_immobile = config.RIVALUTAZIONE_IMMOBILE_OPZIONI[etichetta_rivalutazione]
    orizzonte_anni = col2.number_input(
        "Orizzonte (anni)", min_value=1, max_value=40, value=config.ORIZZONTE_ANNI_ACQUISTO_DEFAULT, step=1,
    )

    return {
        "tipo_investimento": tipo_investimento,
        "rendimento_btp_lordo": rendimento_btp_lordo,
        "rendimento_reale_azionario": rendimento_reale_azionario,
        "inflazione_attesa": inflazione_attesa,
        "rivalutazione_immobile": rivalutazione_immobile,
        "orizzonte_anni": int(orizzonte_anni),
    }


def main() -> None:
    st.title("Acquisto: comprare per affittare vs investire il capitale")
    st.caption(
        "Confronta l'acquisto di un immobile da mettere a reddito con l'investimento dello stesso "
        "capitale proprio in BTP o in un indice azionario globale."
    )

    dati_acquisto = render_sezione_acquisto()
    dati_costi = render_sezione_costi_accessori(dati_acquisto["costo_immobile"])
    dati_canone = render_sezione_canone()
    dati_fiscali = render_sezione_fiscale(dati_canone["tipo_locazione"])
    dati_imu_tari = render_sezione_imu_tari(dati_acquisto["metratura"], dati_canone["tipo_locazione"])
    dati_confronto = render_sezione_confronto()

    percentuale_manutenzione = calcolo.percentuale_manutenzione_per_anno_costruzione(
        dati_acquisto["anno_costruzione"]
    )

    risultato_locazione = calcolo.calcola_risultato_annuale(
        canone_annuo=dati_canone["canone_annuo"],
        metratura=dati_acquisto["metratura"],
        anno_costruzione=dati_acquisto["anno_costruzione"],
        aliquota_comunale_imu=dati_acquisto["aliquota_comunale_imu"],
        regime=dati_fiscali["regime"],
        aliquota_marginale_irpef=dati_fiscali["aliquota_marginale_irpef"],
        addizionali_irpef=dati_fiscali["addizionali_irpef"],
        aliquota_breve=dati_fiscali["aliquota_breve"],
        rendita_catastale_eur_mq=dati_imu_tari["rendita_catastale_eur_mq"],
        tari_eur_mq=dati_imu_tari["tari_eur_mq"],
        tari_a_carico_proprietario=dati_imu_tari["tari_a_carico_proprietario"],
        percentuale_manutenzione_override=percentuale_manutenzione,
    )

    piano_ammortamento = calcolo.piano_ammortamento_mutuo(
        dati_costi["importo_mutuo"], dati_costi["tasso_mutuo"], dati_costi["durata_mutuo"],
    )
    rata_annua = calcolo.rata_mutuo_annua(
        dati_costi["importo_mutuo"], dati_costi["tasso_mutuo"], dati_costi["durata_mutuo"],
    ) if dati_costi["importo_mutuo"] > 0 else 0.0

    st.subheader("Flusso di cassa annuo")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Affitto netto (tasse, IMU, TARI, manutenzione)", formatta_euro(risultato_locazione.flusso_cassa_netto_annuo))
    col2.metric("Rata mutuo", f"-{formatta_euro(rata_annua)}")
    flusso_cassa_con_mutuo = risultato_locazione.flusso_cassa_netto_annuo - rata_annua
    col3.metric("Flusso di cassa netto/anno", formatta_euro(flusso_cassa_con_mutuo))
    col4.metric("Capitale proprio investito", formatta_euro(dati_costi["capitale_proprio_iniziale"]))

    rendimento_alternativo_netto = calcolo.rendimento_investimento_alternativo_netto(
        dati_confronto["tipo_investimento"], dati_confronto["rendimento_btp_lordo"],
        dati_confronto["rendimento_reale_azionario"], dati_confronto["inflazione_attesa"],
    )

    serie = calcolo.simula_proiezione_acquisto(
        valore_immobile_iniziale=dati_acquisto["costo_immobile"],
        capitale_proprio_iniziale=dati_costi["capitale_proprio_iniziale"],
        rivalutazione_immobile=dati_confronto["rivalutazione_immobile"],
        flusso_cassa_locazione_netto_annuo=risultato_locazione.flusso_cassa_netto_annuo,
        piano_ammortamento=piano_ammortamento,
        importo_mutuo=dati_costi["importo_mutuo"],
        rendimento_alternativo_netto=rendimento_alternativo_netto,
        orizzonte_anni=dati_confronto["orizzonte_anni"],
    )

    st.subheader("Proiezione patrimoniale")
    etichetta_alternativa = config.TIPO_INVESTIMENTO_ALTERNATIVO_LABELS[dati_confronto["tipo_investimento"]]
    df = pd.DataFrame(
        {
            "Anno": [p.anno for p in serie],
            "Immobile (netto da mutuo + affitti)": [p.patrimonio_immobiliare for p in serie],
            etichetta_alternativa: [p.patrimonio_alternativo for p in serie],
        }
    ).set_index("Anno")
    st.line_chart(df)

    ultimo = serie[-1]
    differenza = ultimo.patrimonio_immobiliare - ultimo.patrimonio_alternativo
    vincitore = "immobile avanti di" if differenza >= 0 else f"{etichetta_alternativa} avanti di"
    st.write(
        f"Dopo {dati_confronto['orizzonte_anni']} anni, a parità di capitale proprio iniziale "
        f"({formatta_euro(dati_costi['capitale_proprio_iniziale'])}): "
        f"immobile {formatta_euro(ultimo.patrimonio_immobiliare)} "
        f"vs {etichetta_alternativa} {formatta_euro(ultimo.patrimonio_alternativo)} — "
        f"**{vincitore} {formatta_euro(abs(differenza))}**"
    )

    st.caption(
        "Il confronto usa come base di partenza lo stesso capitale proprio (anticipo + notaio + arredo, "
        "se selezionati): il resto del prezzo, se a mutuo, è capitale di terzi e non capitale investito "
        "in alternativa. Notaio e arredo sono trattati come costi non rivalutabili. "
        "Stima indicativa, non sostituisce una consulenza fiscale, notarile o finanziaria."
    )


main()
