"""
Configurazione del simulatore.

Fonti: normativa cedolare secca 2026 (21% canone libero, 10% canone concordato),
IMU 2026 (aliquota base 0.86%, range comunale legale 0.4%-1.06%, riduzione 25%
per canone concordato), tassazione rendite titoli di Stato 12.5%.
I valori di TARI, rendita catastale al mq, rendimento lordo di riferimento e
percentuali di manutenzione straordinaria sono stime indicative ("spannometriche"):
vanno trattate come punto di partenza, sovrascrivibile dall'utente nell'interfaccia.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FasciaManutenzione:
    soglia_anno: float  # esclusivo: l'anno di costruzione deve essere < soglia_anno
    percentuale_canone: float
    etichetta: str


CEDOLARE_ALIQUOTE = {
    "libero": 0.21,
    "concordato": 0.10,
}

REGIME_LABELS = {
    "libero": "Cedolare secca - canone libero (21%)",
    "concordato": "Cedolare secca - canone concordato (10%)",
    "irpef": "IRPEF ordinaria (aliquota marginale)",
}

IRPEF_DEDUZIONE_FORFETTARIA = 0.05  # abbattimento forfettario sul reddito fondiario

IRPEF_ALIQUOTE_MARGINALI = {
    "23% (fino a 28.000 €)": 0.23,
    "35% (28.001 - 50.000 €)": 0.35,
    "43% (oltre 50.000 €)": 0.43,
}

IRPEF_ADDIZIONALI_DEFAULT = 0.02  # media regionale + comunale, indicativa

IMU_MOLTIPLICATORE_ABITAZIONE = 160
IMU_RIVALUTAZIONE_RENDITA = 1.05
IMU_RIDUZIONE_CANONE_CONCORDATO = 0.25  # riduzione IMU per contratti a canone concordato

IMU_ALIQUOTA_PER_TIPO_COMUNE = {
    "Piccolo comune (~0.86%)": 0.0086,
    "Città media (~0.96%)": 0.0096,
    "Grande città/metropoli (~1.06%)": 0.0106,
}

RENDITA_CATASTALE_EUR_MQ_DEFAULT = 3.5  # stima grezza, varia molto per comune/microzona

TARI_EUR_MQ_ANNO_DEFAULT = 2.2  # range tipico osservato: 1.5-3.5 €/mq/anno

MANUTENZIONE_PER_DECENNIO = (
    FasciaManutenzione(1960, 0.15, "Prima del 1960"),
    FasciaManutenzione(1980, 0.10, "1960 - 1979"),
    FasciaManutenzione(2000, 0.07, "1980 - 1999"),
    FasciaManutenzione(2010, 0.05, "2000 - 2009"),
    FasciaManutenzione(float("inf"), 0.03, "2010 in poi"),
)

RENDIMENTO_LORDO_STIMA_VALORE_DEFAULT = 0.05  # riferimento per stimare il valore immobile dal canone

RIVALUTAZIONE_IMMOBILE_OPZIONI = {
    "Zona in declino (-1%/anno)": -0.01,
    "Stabile (0%/anno)": 0.0,
    "Crescita moderata (+1%/anno)": 0.01,
    "Crescita media grande città (+2%/anno)": 0.02,
    "Zona di pregio / alta crescita (+3%/anno)": 0.03,
}

BTP_TASSAZIONE_RENDIMENTO = 0.125  # aliquota agevolata titoli di Stato

BTP_RENDIMENTO_LORDO_DEFAULT = 0.035

ORIZZONTE_ANNI_DEFAULT = 20

TIPO_LOCAZIONE_LABELS = {
    "lungo_termine": "Locazione lungo termine (canone mensile)",
    "breve": "Affitto breve (turistico)",
}

CEDOLARE_BREVE_ALIQUOTE = {
    "Primo immobile (21%)": 0.21,
    "Dal secondo immobile in poi (26%)": 0.26,
}

GIORNI_ANNO = 365
AFFITTO_BREVE_CANONE_GIORNALIERO_DEFAULT = 90.0
AFFITTO_BREVE_PERCENTUALE_OCCUPAZIONE_DEFAULT = 0.55

MUTUO_PERCENTUALE_ANTICIPO_DEFAULT = 0.20
MUTUO_TASSO_ANNUO_DEFAULT = 0.035
MUTUO_DURATA_ANNI_DEFAULT = 25

NOTAIO_PERCENTUALE_DEFAULT = 0.03

ARREDO_IMPORTO_DEFAULT = 12000.0

TIPO_INVESTIMENTO_ALTERNATIVO_LABELS = {
    "btp": "BTP",
    "azionario_globale": "Azionario globale (indice diversificato)",
}

AZIONARIO_RENDIMENTO_REALE_DEFAULT = 0.05
AZIONARIO_TASSAZIONE_PLUSVALENZE = 0.26
INFLAZIONE_ATTESA_DEFAULT = 0.02

ORIZZONTE_ANNI_ACQUISTO_DEFAULT = 20
