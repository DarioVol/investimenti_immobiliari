"""
Pagina "Affitto": guadagno netto di un immobile locato e confronto con un BTP.
Entry point dell'app: home.py (vedi lì per l'esecuzione locale e il deploy).
"""

import pandas as pd
import streamlit as st

import config
import calcolo
from formattazione import formatta_euro, formatta_percentuale


def render_sezione_immobile() -> dict:
    st.subheader("Immobile")
    col1, col2, col3 = st.columns(3)
    metratura = col1.number_input("Metratura (mq)", min_value=1, value=70, step=5)
    anno_costruzione = col2.number_input("Anno di costruzione", min_value=1900, max_value=2026, value=1985, step=1)
    tipo_comune = col3.selectbox("Tipo di comune (per IMU)", list(config.IMU_ALIQUOTA_PER_TIPO_COMUNE.keys()))
    return {
        "metratura": metratura,
        "anno_costruzione": anno_costruzione,
        "aliquota_comunale_imu": config.IMU_ALIQUOTA_PER_TIPO_COMUNE[tipo_comune],
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
    st.subheader("Tassazione")

    if tipo_locazione == "breve":
        etichetta_aliquota = st.radio("Cedolare secca affitti brevi", list(config.CEDOLARE_BREVE_ALIQUOTE.keys()))
        st.caption(
            "Affitto breve: cedolare secca 21% sul primo immobile individuato dal contribuente, "
            "26% dal secondo immobile locato in questa modalità in poi."
        )
        return {
            "regime": "breve",
            "aliquota_breve": config.CEDOLARE_BREVE_ALIQUOTE[etichetta_aliquota],
            "aliquota_marginale_irpef": 0.0,
            "addizionali_irpef": 0.0,
        }

    regime_label = st.radio(
        "Regime fiscale",
        [v for k, v in config.REGIME_LABELS.items() if k != "breve" and k in ("libero", "concordato", "irpef")],
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

    st.caption(
        "Cedolare secca: 21% canone libero, 10% canone concordato (aliquote 2026). "
        "IRPEF ordinaria: deduzione forfettaria 5% sul reddito fondiario, poi aliquota marginale + addizionali."
    )
    return {
        "regime": regime,
        "aliquota_breve": None,
        "aliquota_marginale_irpef": aliquota_marginale_irpef,
        "addizionali_irpef": addizionali_irpef,
    }


def render_sezione_imu_tari(tipo_locazione: str) -> dict:
    st.subheader("IMU e TARI")
    col1, col2, col3, col4 = st.columns(4)

    rendita_catastale_eur_mq = col1.number_input(
        "Rendita catastale (€/mq/anno)", min_value=0.0,
        value=config.RENDITA_CATASTALE_EUR_MQ_DEFAULT, step=0.1,
    )
    imu_override_raw = col2.text_input("IMU annua — override (€, vuoto = stima)")

    tari_eur_mq = col3.number_input(
        "TARI (€/mq/anno)", min_value=0.0, value=config.TARI_EUR_MQ_ANNO_DEFAULT, step=0.1,
    )
    tari_override_raw = col4.text_input("TARI — override (€, vuoto = stima)")

    # Nell'affitto breve la TARI è quasi sempre a carico del proprietario (l'ospite non risiede).
    default_tari_proprietario = tipo_locazione == "breve"
    tari_a_carico_proprietario = st.checkbox(
        "TARI a carico del proprietario (di norma è a carico dell'inquilino, tranne che negli affitti brevi)",
        value=default_tari_proprietario,
    )

    return {
        "rendita_catastale_eur_mq": rendita_catastale_eur_mq,
        "imu_override": float(imu_override_raw) if imu_override_raw.strip() else None,
        "tari_eur_mq": tari_eur_mq,
        "tari_override": float(tari_override_raw) if tari_override_raw.strip() else None,
        "tari_a_carico_proprietario": tari_a_carico_proprietario,
    }


def render_sezione_manutenzione(anno_costruzione: int) -> dict:
    st.subheader("Manutenzione straordinaria")
    percentuale_stimata = calcolo.percentuale_manutenzione_per_anno_costruzione(anno_costruzione)
    col1, col2 = st.columns(2)
    col1.metric("Stima da anno di costruzione", formatta_percentuale(percentuale_stimata))
    override_raw = col2.text_input("Override manuale (% del canone, vuoto = stima)")
    percentuale_override = float(override_raw) / 100 if override_raw.strip() else None
    return {"percentuale_manutenzione_override": percentuale_override}


def render_risultato(risultato: calcolo.RisultatoAnnuale) -> None:
    st.subheader("Guadagno netto annuo")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Canone lordo", formatta_euro(risultato.canone_annuo))
    col2.metric("Imposta", f"-{formatta_euro(risultato.imposta)}")
    col3.metric("IMU", f"-{formatta_euro(risultato.imu)}")
    col4.metric("Manutenzione", f"-{formatta_euro(risultato.manutenzione)}")

    st.markdown(
        f"### {formatta_euro(risultato.flusso_cassa_netto_annuo)} netto/anno "
        f"· {formatta_percentuale(risultato.rendimento_netto_sul_canone)} del canone"
    )


def render_comparatore_btp(risultato: calcolo.RisultatoAnnuale, regime: str) -> None:
    st.subheader("Confronto con investimento in BTP")
    st.caption(
        "Inserisci direttamente il valore di mercato che attribuisci all'immobile. "
        "Il simulatore calcola da questo valore il rendimento lordo e netto della locazione, "
        "senza ricavare il prezzo da un rendimento teorico di zona."
    )
    col1, col2, col3, col4 = st.columns(4)
    valore_immobile = col1.number_input(
        "Valore immobile (€)", min_value=1_000.0, value=150_000.0, step=5_000.0,
        help="Valore di mercato stimato o prezzo che vuoi usare come base del confronto."
    )
    rendimento_btp = col2.number_input(
        "Rendimento BTP lordo (%)", min_value=0.0,
        value=config.BTP_RENDIMENTO_LORDO_DEFAULT * 100, step=0.1,
    ) / 100
    etichetta_rivalutazione = col3.selectbox(
        "Rivalutazione immobile", list(config.RIVALUTAZIONE_IMMOBILE_OPZIONI.keys()), index=2,
    )
    rivalutazione_immobile = config.RIVALUTAZIONE_IMMOBILE_OPZIONI[etichetta_rivalutazione]
    orizzonte_anni = col4.number_input(
        "Orizzonte (anni)", min_value=1, max_value=40, value=config.ORIZZONTE_ANNI_DEFAULT, step=1,
    )

    rendimento_lordo_sul_valore = risultato.canone_annuo / valore_immobile if valore_immobile else 0.0
    rendimento_netto_sul_valore = (
        risultato.flusso_cassa_netto_annuo / valore_immobile if valore_immobile else 0.0
    )
    rendimento_btp_netto = rendimento_btp * (1 - config.BTP_TASSAZIONE_RENDIMENTO)

    m1, m2, m3 = st.columns(3)
    m1.metric("Rendimento lordo immobile", formatta_percentuale(rendimento_lordo_sul_valore))
    m2.metric("Rendimento netto immobile", formatta_percentuale(rendimento_netto_sul_valore))
    m3.metric("Rendimento BTP netto", formatta_percentuale(rendimento_btp_netto))
    st.caption(
        "Rendimento lordo immobile = canone annuo / valore immobile. "
        "Rendimento netto immobile = flusso di cassa annuo dopo imposte, IMU, TARI eventualmente a carico del proprietario "
        "e manutenzione stimata / valore immobile. Il rendimento BTP è mostrato al netto della tassazione del 12,5%."
    )

    serie, _ = calcolo.simula_proiezione(
        valore_iniziale=valore_immobile,
        flusso_cassa_netto_annuo=risultato.flusso_cassa_netto_annuo,
        rivalutazione_immobile=rivalutazione_immobile,
        rendimento_btp_lordo=rendimento_btp,
        orizzonte_anni=int(orizzonte_anni),
    )

    df = pd.DataFrame(
        {
            "Anno": [p.anno for p in serie],
            "Immobile (capitale + affitti netti)": [p.patrimonio_immobile for p in serie],
            "BTP (capitale reinvestito)": [p.patrimonio_btp for p in serie],
        }
    ).set_index("Anno")
    st.line_chart(df)

    ultimo = serie[-1]
    differenza = ultimo.patrimonio_immobile - ultimo.patrimonio_btp
    vincitore = "immobile avanti di" if differenza >= 0 else "BTP avanti di"
    st.write(
        f"Dopo {int(orizzonte_anni)} anni: immobile {formatta_euro(ultimo.patrimonio_immobile)} "
        f"vs BTP {formatta_euro(ultimo.patrimonio_btp)} — **{vincitore} {formatta_euro(abs(differenza))}**"
    )
    st.info(
        "Il confronto è semplificato: non incorpora automaticamente costi di acquisto/vendita, periodi di sfitto, "
        "morosità, assicurazioni, spese condominiali non ribaltabili, lavori eccezionali, variazioni normative, "
        "liquidità e rischio dei due investimenti. La rivalutazione dell'immobile è un'ipotesi, non una previsione."
    )


def main() -> None:
    st.title("Affitto: guadagno netto e confronto con BTP")
    st.caption(
        "Stima il guadagno netto di un immobile affittato e confrontalo con un BTP. "
        "Tutti i valori stimati sono indicativi e sovrascrivibili."
    )
    st.warning(
        "Simulatore a scopo informativo: i risultati sono stime basate sulle ipotesi inserite e non costituiscono "
        "consulenza fiscale, finanziaria, immobiliare o legale. Verifica dati catastali, aliquote comunali, "
        "inquadramento del contratto e fiscalità applicabile con fonti ufficiali o professionisti qualificati."
    )

    dati_immobile = render_sezione_immobile()
    dati_canone = render_sezione_canone()
    dati_fiscali = render_sezione_fiscale(dati_canone["tipo_locazione"])
    dati_imu_tari = render_sezione_imu_tari(dati_canone["tipo_locazione"])
    dati_manutenzione = render_sezione_manutenzione(dati_immobile["anno_costruzione"])

    risultato = calcolo.calcola_risultato_annuale(
        canone_annuo=dati_canone["canone_annuo"],
        metratura=dati_immobile["metratura"],
        anno_costruzione=dati_immobile["anno_costruzione"],
        aliquota_comunale_imu=dati_immobile["aliquota_comunale_imu"],
        regime=dati_fiscali["regime"],
        aliquota_marginale_irpef=dati_fiscali["aliquota_marginale_irpef"],
        addizionali_irpef=dati_fiscali["addizionali_irpef"],
        aliquota_breve=dati_fiscali["aliquota_breve"],
        rendita_catastale_eur_mq=dati_imu_tari["rendita_catastale_eur_mq"],
        imu_override=dati_imu_tari["imu_override"],
        tari_eur_mq=dati_imu_tari["tari_eur_mq"],
        tari_override=dati_imu_tari["tari_override"],
        tari_a_carico_proprietario=dati_imu_tari["tari_a_carico_proprietario"],
        percentuale_manutenzione_override=dati_manutenzione["percentuale_manutenzione_override"],
    )

    render_risultato(risultato)
    render_comparatore_btp(risultato, dati_fiscali["regime"])

    st.caption(
        "Strumento di stima indicativa, non sostituisce una consulenza fiscale o un CTU. "
        "Aliquote IMU, TARI, rendita catastale e rendimento di riferimento vanno verificate "
        "sul proprio Comune e sulla propria visura catastale."
    )


if __name__ == "__main__":
    main()
