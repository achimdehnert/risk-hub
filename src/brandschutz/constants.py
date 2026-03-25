# src/brandschutz/constants.py
"""
Brandschutz- und Explosionsschutz-Konstanten mit Norm-Version und Quelle.

Migriert aus nl2cad-brandschutz.constants + nl2cad-core.constants.
Jede Konstante trägt Norm, Paragraf und Versionsdatum.
"""

# ---------------------------------------------------------------------------
# DXF/IFC Layer-Keywords (migriert aus nl2cad-core.constants)
# ---------------------------------------------------------------------------

FLUCHTWEG_KEYWORDS: tuple[str, ...] = (
    "flucht",
    "rettung",
    "escape",
    "notweg",
    "fluchtweg",
    "rettungsweg",
    "emergency",
)

NOTAUSGANG_KEYWORDS: tuple[str, ...] = (
    "notausgang",
    "emergency exit",
    "notaus",
    "ausgang_not",
)

BRANDABSCHNITT_KEYWORDS: tuple[str, ...] = (
    "brand",
    "brandwand",
    "brandschutz",
    "fire",
    "feuerwand",
    "brandabschnitt",
    "brandschutzwand",
)

LOESCHEINRICHTUNG_KEYWORDS: tuple[str, ...] = (
    "feuerlöscher",
    "hydrant",
    "sprinkler",
    "lösch",
    "fire extinguisher",
    "löscher",
)

BRANDSCHUTZTUER_KEYWORDS: tuple[str, ...] = (
    "t30",
    "t60",
    "t90",
    "t120",
    "brandschutztür",
    "brandschutztuer",
    "feuerschutztür",
)

FEUERWIDERSTANDSKLASSEN: tuple[str, ...] = (
    "F30",
    "F60",
    "F90",
    "F120",
    "F180",
    "REI30",
    "REI60",
    "REI90",
    "REI120",
    "EI30",
    "EI60",
    "EI90",
    "EI120",
    "E30",
    "E60",
    "E90",
    "R30",
    "R60",
    "R90",
)

# ---------------------------------------------------------------------------
# Norm-Versionen (W-01: explizit versioniert)
# ---------------------------------------------------------------------------

ASR_A23_VERSION: str = "ASR-A2.3-2022"
MBO_VERSION: str = "MBO-2016"
DIN4102_VERSION: str = "DIN-4102-1998"
EN13501_VERSION: str = "EN-13501-2019"
EN60079_10_1_VERSION: str = "EN-60079-10-1-2016"
TRBS2152_VERSION: str = "TRBS-2152-2012"
BETRSICHV_VERSION: str = "BetrSichV-2015"

# ---------------------------------------------------------------------------
# ASR A2.3 — Fluchtweg-Grenzwerte (§ 4 + § 5, Ausgabe 2022)
# ---------------------------------------------------------------------------

MAX_FLUCHTWEG_LAENGE_M: float = 35.0
MAX_FLUCHTWEG_LAENGE_MIT_ABZWEIG_M: float = 60.0
MIN_BREITE_STANDARD_M: float = 0.875
MIN_BREITE_AB_5_PERSONEN_M: float = 1.0
MIN_BREITE_AB_20_PERSONEN_M: float = 1.2
MIN_TUERBREITE_M: float = 0.78
MAX_FLUCHTWEG_VERSAMMLUNGSSTAETTE_M: float = 30.0

# ---------------------------------------------------------------------------
# MBO § 2 Abs. 3 — Gebäudehöhen für Gebäudeklassen (Fassung 2016)
# ---------------------------------------------------------------------------

MBO_GK123_MAX_OKFF_M: float = 7.0
MBO_GK4_MAX_OKFF_M: float = 13.0
MBO_HOCHHAUS_MIN_OKFF_M: float = 22.0
MBO_GK12_MAX_NE_FLAECHE_M2: float = 400.0
MBO_GK4_MAX_NE_FLAECHE_M2: float = 400.0
MBO_GK12_MAX_NE_ANZAHL: int = 2
MBO_ANLEITERN_MAX_UKFF_M: float = 8.0
MBO_AUSSENTREPPE_MIN_BREITE_M: float = 1.2

# ---------------------------------------------------------------------------
# DIN 4102 / EN 13501 — Feuerwiderstandsklassen
# ---------------------------------------------------------------------------

FEUERWIDERSTANDSKLASSEN_DIN4102: tuple[str, ...] = (
    "F30", "F60", "F90", "F120", "F180",
)

FEUERWIDERSTANDSKLASSEN_EN13501: tuple[str, ...] = (
    "REI30", "REI60", "REI90", "REI120",
    "EI30", "EI60", "EI90", "EI120",
    "E30", "E60", "E90",
    "R30", "R60", "R90",
)

ALLE_FEUERWIDERSTANDSKLASSEN: frozenset[str] = frozenset(
    FEUERWIDERSTANDSKLASSEN_DIN4102 + FEUERWIDERSTANDSKLASSEN_EN13501
)

BRANDSCHUTZTUER_KLASSEN: tuple[str, ...] = (
    "T30", "T60", "T90", "T120",
    "EI230", "EI260", "EI290",
)

# ---------------------------------------------------------------------------
# EN 60079-10-1 Tabelle 1 — Zonenausdehnung (vereinfacht)
# ---------------------------------------------------------------------------

EX_ZONENAUSDEHNUNG: dict[tuple[str, str], tuple[str, float]] = {
    ("K", "K1"): ("Zone 0", 0.5),
    ("K", "K2"): ("Zone 0", 1.0),
    ("K", "K3"): ("Zone 0", 3.0),
    ("P", "K1"): ("Zone 1", 0.5),
    ("P", "K2"): ("Zone 1", 1.0),
    ("P", "K3"): ("Zone 1", 3.0),
    ("S", "K1"): ("Zone 2", 1.0),
    ("S", "K2"): ("Zone 2", 2.0),
    ("S", "K3"): ("Zone 2", 5.0),
    ("K_STAUB", "K1"): ("Zone 20", 0.5),
    ("K_STAUB", "K2"): ("Zone 20", 1.0),
    ("K_STAUB", "K3"): ("Zone 20", 3.0),
    ("P_STAUB", "K1"): ("Zone 21", 0.5),
    ("P_STAUB", "K2"): ("Zone 21", 1.0),
    ("P_STAUB", "K3"): ("Zone 21", 3.0),
    ("S_STAUB", "K1"): ("Zone 22", 1.0),
    ("S_STAUB", "K2"): ("Zone 22", 2.0),
    ("S_STAUB", "K3"): ("Zone 22", 5.0),
}

ATEX_ZONE_ZU_GERAETEKATEGORIE: dict[str, str] = {
    "Zone 0": "KAT1",
    "Zone 1": "KAT2",
    "Zone 2": "KAT3",
    "Zone 20": "KAT1",
    "Zone 21": "KAT2",
    "Zone 22": "KAT3",
}

# ---------------------------------------------------------------------------
# BetrSichV § 6 Abs. 9 — ESD-Pflichtfelder
# ---------------------------------------------------------------------------

ESD_PFLICHTFELDER: tuple[str, ...] = (
    "betrieb_name",
    "erstellungsdatum",
    "erstellt_von",
    "naechste_pruefung",
    "gefaehrdungsbeurteilung",
    "explosionsfaehige_atmosphaere_moeglich",
)
