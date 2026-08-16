"""
Funzioni di calcolo del simulatore. Nessuna dipendenza da Streamlit:
ogni funzione è pura (stesso input -> stesso output) e testabile in isolamento.
"""

from dataclasses import dataclass

import config


class ParametroNonValidoError(ValueError):
    """Sollevato quando un parametro di input è fuori dal dominio ammesso."""


@dataclass
class RisultatoAnnuale:
    canone_annuo: float
    imposta: float
    rendita_catastale_annua: float
    imu: float
    tari_stimata: float
    tari_nel_conto: float
    percentuale_manutenzione: float
    manutenzione: float
    flusso_cassa_netto_annuo: float
    rendimento_netto_sul_canone: float


@dataclass
class PuntoProiezione:
    anno: int
    patrimonio_immobile: float
    patrimonio_btp: float


def calcola_imposta(regime: str, canone_annuo: float, aliquota_marginale_irpef: float = 0.0,
                     addizionali: float = 0.0, aliquota_breve: float | None = None) -> float:
    if regime in ("libero", "concordato"):
        return canone_annuo * config.CEDOLARE_ALIQUOTE[regime]
    if regime == "irpef":
        imponibile = canone_annuo * (1 - config.IRPEF_DEDUZIONE_FORFETTARIA)
        return imponibile * (aliquota_marginale_irpef + addizionali)
    if regime == "breve":
        if aliquota_breve is None:
            raise ParametroNonValidoError("Per il regime 'breve' è richiesta l'aliquota cedolare (21% o 26%)")
        return canone_annuo * aliquota_breve
    raise ParametroNonValidoError(f"Regime fiscale non riconosciuto: {regime}")


def calcola_canone_annuo_lungo_termine(canone_mensile: float) -> float:
    return canone_mensile * 12


def calcola_canone_annuo_breve(
    canone_giornaliero: float, percentuale_occupazione: float, giorni_anno: int = config.GIORNI_ANNO,
) -> float:
    if not 0 <= percentuale_occupazione <= 1:
        raise ParametroNonValidoError("La percentuale di occupazione deve essere compresa tra 0 e 1")
    return canone_giornaliero * giorni_anno * percentuale_occupazione


def stima_rendita_catastale_annua(metratura: float, rendita_catastale_eur_mq: float) -> float:
    return metratura * rendita_catastale_eur_mq


def calcola_imu(rendita_catastale_annua: float, aliquota_comunale: float, regime: str) -> float:
    base = (
        rendita_catastale_annua
        * config.IMU_RIVALUTAZIONE_RENDITA
        * config.IMU_MOLTIPLICATORE_ABITAZIONE
    )
    imu_piena = base * aliquota_comunale
    riduzione = config.IMU_RIDUZIONE_CANONE_CONCORDATO if regime == "concordato" else 0.0
    return imu_piena * (1 - riduzione)


def calcola_tari(metratura: float, tari_eur_mq: float) -> float:
    return metratura * tari_eur_mq


def percentuale_manutenzione_per_anno_costruzione(anno_costruzione: int) -> float:
    for fascia in config.MANUTENZIONE_PER_DECENNIO:
        if anno_costruzione < fascia.soglia_anno:
            return fascia.percentuale_canone
    raise ParametroNonValidoError("Nessuna fascia di manutenzione trovata: controllare la configurazione")


def stima_valore_immobile(canone_annuo_lordo: float, rendimento_lordo_stima: float) -> float:
    if rendimento_lordo_stima <= 0:
        raise ParametroNonValidoError("Il rendimento lordo di riferimento deve essere positivo")
    return canone_annuo_lordo / rendimento_lordo_stima


def calcola_risultato_annuale(
    *, canone_annuo: float, metratura: float, anno_costruzione: int,
    aliquota_comunale_imu: float, regime: str,
    aliquota_marginale_irpef: float = 0.0, addizionali_irpef: float = 0.0,
    aliquota_breve: float | None = None,
    rendita_catastale_eur_mq: float = config.RENDITA_CATASTALE_EUR_MQ_DEFAULT,
    imu_override: float | None = None,
    tari_eur_mq: float = config.TARI_EUR_MQ_ANNO_DEFAULT,
    tari_override: float | None = None,
    tari_a_carico_proprietario: bool = False,
    percentuale_manutenzione_override: float | None = None,
) -> RisultatoAnnuale:
    imposta = calcola_imposta(regime, canone_annuo, aliquota_marginale_irpef, addizionali_irpef, aliquota_breve)

    rendita_catastale_annua = stima_rendita_catastale_annua(metratura, rendita_catastale_eur_mq)
    imu = imu_override if imu_override is not None else calcola_imu(
        rendita_catastale_annua, aliquota_comunale_imu, regime
    )

    tari_stimata = calcola_tari(metratura, tari_eur_mq)
    tari_effettiva = tari_override if tari_override is not None else tari_stimata
    tari_nel_conto = tari_effettiva if tari_a_carico_proprietario else 0.0

    percentuale_manutenzione = (
        percentuale_manutenzione_override
        if percentuale_manutenzione_override is not None
        else percentuale_manutenzione_per_anno_costruzione(anno_costruzione)
    )
    manutenzione = canone_annuo * percentuale_manutenzione

    flusso_cassa_netto_annuo = canone_annuo - imposta - imu - tari_nel_conto - manutenzione
    rendimento_netto_sul_canone = flusso_cassa_netto_annuo / canone_annuo if canone_annuo else 0.0

    return RisultatoAnnuale(
        canone_annuo=canone_annuo, imposta=imposta, rendita_catastale_annua=rendita_catastale_annua,
        imu=imu, tari_stimata=tari_stimata, tari_nel_conto=tari_nel_conto,
        percentuale_manutenzione=percentuale_manutenzione, manutenzione=manutenzione,
        flusso_cassa_netto_annuo=flusso_cassa_netto_annuo,
        rendimento_netto_sul_canone=rendimento_netto_sul_canone,
    )


def simula_proiezione(
    *, valore_iniziale: float, flusso_cassa_netto_annuo: float, rivalutazione_immobile: float,
    rendimento_btp_lordo: float, orizzonte_anni: int,
) -> tuple[list[PuntoProiezione], float]:
    if orizzonte_anni < 1:
        raise ParametroNonValidoError("L'orizzonte temporale deve essere di almeno 1 anno")

    rendimento_btp_netto = rendimento_btp_lordo * (1 - config.BTP_TASSAZIONE_RENDIMENTO)

    serie: list[PuntoProiezione] = []
    valore_immobile_corrente = valore_iniziale
    cassa_cumulata_immobile = 0.0
    capitale_btp = valore_iniziale

    for anno in range(orizzonte_anni + 1):
        if anno > 0:
            valore_immobile_corrente *= 1 + rivalutazione_immobile
            cassa_cumulata_immobile += flusso_cassa_netto_annuo
            capitale_btp *= 1 + rendimento_btp_netto
        serie.append(PuntoProiezione(
            anno=anno,
            patrimonio_immobile=round(valore_immobile_corrente + cassa_cumulata_immobile),
            patrimonio_btp=round(capitale_btp),
        ))

    return serie, rendimento_btp_netto


@dataclass
class RataMutuo:
    anno: int
    rata: float
    interessi: float
    quota_capitale: float
    debito_residuo: float


@dataclass
class PuntoProiezioneAcquisto:
    anno: int
    patrimonio_immobiliare: float
    patrimonio_alternativo: float


def rata_mutuo_annua(importo_mutuo: float, tasso_annuo: float, durata_anni: int) -> float:
    if durata_anni <= 0:
        raise ParametroNonValidoError("La durata del mutuo deve essere di almeno 1 anno")
    if importo_mutuo <= 0:
        return 0.0
    if tasso_annuo == 0:
        return importo_mutuo / durata_anni
    fattore = (1 + tasso_annuo) ** durata_anni
    return importo_mutuo * (tasso_annuo * fattore) / (fattore - 1)


def piano_ammortamento_mutuo(importo_mutuo: float, tasso_annuo: float, durata_anni: int) -> list[RataMutuo]:
    if importo_mutuo <= 0:
        return []
    rata = rata_mutuo_annua(importo_mutuo, tasso_annuo, durata_anni)
    debito_residuo = importo_mutuo
    piano: list[RataMutuo] = []
    for anno in range(1, durata_anni + 1):
        interessi = debito_residuo * tasso_annuo
        quota_capitale = min(rata - interessi, debito_residuo)
        debito_residuo = max(0.0, debito_residuo - quota_capitale)
        piano.append(RataMutuo(
            anno=anno, rata=rata, interessi=interessi,
            quota_capitale=quota_capitale, debito_residuo=debito_residuo,
        ))
    return piano


def rendimento_investimento_alternativo_netto(
    tipo_investimento: str, rendimento_btp_lordo: float,
    rendimento_reale_azionario: float, inflazione_attesa: float,
) -> float:
    if tipo_investimento == "btp":
        return rendimento_btp_lordo * (1 - config.BTP_TASSAZIONE_RENDIMENTO)
    if tipo_investimento == "azionario_globale":
        rendimento_nominale = (1 + rendimento_reale_azionario) * (1 + inflazione_attesa) - 1
        return rendimento_nominale * (1 - config.AZIONARIO_TASSAZIONE_PLUSVALENZE)
    raise ParametroNonValidoError(f"Tipo di investimento alternativo non riconosciuto: {tipo_investimento}")


def simula_proiezione_acquisto(
    *, valore_immobile_iniziale: float, capitale_proprio_iniziale: float,
    rivalutazione_immobile: float, flusso_cassa_locazione_netto_annuo: float,
    piano_ammortamento: list[RataMutuo], importo_mutuo: float,
    rendimento_alternativo_netto: float, orizzonte_anni: int,
) -> list[PuntoProiezioneAcquisto]:
    if orizzonte_anni < 1:
        raise ParametroNonValidoError("L'orizzonte temporale deve essere di almeno 1 anno")

    debito_per_anno = {rata.anno: rata.debito_residuo for rata in piano_ammortamento}
    rata_per_anno = {rata.anno: rata.rata for rata in piano_ammortamento}

    serie: list[PuntoProiezioneAcquisto] = []
    valore_immobile_corrente = valore_immobile_iniziale
    debito_residuo_corrente = importo_mutuo
    cassa_cumulata = 0.0
    capitale_alternativo = capitale_proprio_iniziale

    for anno in range(orizzonte_anni + 1):
        if anno > 0:
            valore_immobile_corrente *= 1 + rivalutazione_immobile
            rata_anno = rata_per_anno.get(anno, 0.0)
            cassa_cumulata += flusso_cassa_locazione_netto_annuo - rata_anno
            debito_residuo_corrente = debito_per_anno.get(anno, 0.0)
            capitale_alternativo *= 1 + rendimento_alternativo_netto
        patrimonio_immobiliare = valore_immobile_corrente - debito_residuo_corrente + cassa_cumulata
        serie.append(PuntoProiezioneAcquisto(
            anno=anno,
            patrimonio_immobiliare=round(patrimonio_immobiliare),
            patrimonio_alternativo=round(capitale_alternativo),
        ))

    return serie
