# src/substances/services/sds_parser.py
"""
SDS-PDF Parser Service mit OCR-Unterstützung.

Extrahiert relevante Informationen aus Sicherheitsdatenblättern:
- H-Sätze (Hazard Statements)
- P-Sätze (Precautionary Statements)
- GHS-Piktogramme
- Physikalische Eigenschaften (Flammpunkt, Zündtemperatur, etc.)
"""

import contextlib
import json
import logging
import re
from dataclasses import dataclass, field

from ingest.extractors.pdf import PDFExtractor

logger = logging.getLogger(__name__)

_pdf_extractor = PDFExtractor(ocr_fallback=True)


@dataclass
class SdsParseResult:
    """Ergebnis des SDS-Parsings."""

    product_name: str = ""
    manufacturer_name: str = ""
    revision_date: str = ""  # ISO format YYYY-MM-DD
    version_number: str = ""
    cas_number: str = ""
    signal_word: str = "none"
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    pictograms: list[str] = field(default_factory=list)
    flash_point_c: float | None = None
    ignition_temperature_c: float | None = None
    lower_explosion_limit: float | None = None
    upper_explosion_limit: float | None = None
    boiling_point_c: float | None = None
    vapor_pressure_hpa: float | None = None
    density_g_cm3: float | None = None
    ph_value: float | None = None
    viscosity_mm2_s: float | None = None
    wgk: str = ""
    storage_class: str = ""
    un_number: str = ""
    adr_class: str = ""
    water_solubility: str = ""
    appearance: str = ""
    parse_confidence: float = 0.0
    raw_text: str = ""
    sections: dict = field(default_factory=dict)


class SdsParserService:
    """Service zum Parsen von SDS-PDFs."""

    # Regex-Patterns für H-/P-Sätze
    H_PATTERN = re.compile(r"\b(H[0-9]{3}[A-Za-z]?)\b")
    P_PATTERN = re.compile(r"\b(P[0-9]{3}(?:\+P[0-9]{3})*)\b")

    # Regex für Piktogramme
    GHS_PATTERN = re.compile(r"\b(GHS0[1-9])\b", re.IGNORECASE)

    # ── Regex-Hilfsmuster: Dotted-Table-Format  ──
    # Wacker-Format: "Flammpunkt ........................ : 34 °C"
    # SEP = beliebig viele Punkte/Leerzeichen + optionaler Doppelpunkt
    _SEP = r"[.\s]{0,60}:?[.\s]{0,10}"

    # Physikalische Eigenschaften (mit Dotted-Table-Toleranz)
    FLASH_POINT_PATTERN = re.compile(
        r"(?:[Ff]lammpunkt|[Ff]lash\s*[Pp]oint)" + r"[.:\s]{0,60}" +
        r":?\s*([-><=]?\s*\d+(?:[.,]\d+)?)\s*°?\s*C",
        re.IGNORECASE,
    )
    BOILING_POINT_PATTERN = re.compile(
        r"(?:[Ss]iedepunkt|[Ss]iede(?:beginn|bereich)|[Bb]oiling\s*[Pp]oint)" + r"[.:\s]{0,60}" +
        r":?\s*([-><=]?\s*\d+(?:[.,]\d+)?)\s*°?\s*C",
        re.IGNORECASE,
    )
    DENSITY_PATTERN = re.compile(
        r"(?:[Dd]ichte|[Dd]ensity)[^:\n]*:?\s*([0-9]+[.,][0-9]+)\s*g/(?:cm[³3]|ml|L)",
        re.IGNORECASE,
    )
    VAPOR_PRESSURE_PATTERN = re.compile(
        r"(?:[Dd]ampfdruck|[Vv]apou?r?\s*[Pp]ressure)" + r"[.:\s]{0,60}" +
        r":?\s*([0-9]+[.,]?[0-9]*)\s*(?:hPa|mbar|Pa(?!s)|kPa)",
        re.IGNORECASE,
    )
    IGNITION_TEMP_PATTERN = re.compile(
        r"(?:[Zz]ünd(?:temperatur|punkt)|[Ss]elf[- ]?[Ii]gnition)" + r"[.:\s]{0,60}" +
        r":?\s*([->]?\s*\d+(?:[.,]\d+)?)\s*°?\s*C",
        re.IGNORECASE,
    )
    LEL_PATTERN = re.compile(
        r"(?:UEG|LEL|[Uu]ntere\s*[Ee]xplosions(?:grenze)?|[Ll]ower\s+[Ee]xplosion)" +
        r"[.:\s]{0,60}:?\s*(\d+(?:[.,]\d+)?)\s*(?:Vol[.-]?%|%[- ]?V)",
        re.IGNORECASE,
    )
    UEL_PATTERN = re.compile(
        r"(?:OEG|UEL|[Oo]bere\s*[Ee]xplosions(?:grenze)?|[Uu]pper\s+[Ee]xplosion)" +
        r"[.:\s]{0,60}:?\s*(\d+(?:[.,]\d+)?)\s*(?:Vol[.-]?%|%[- ]?V)",
        re.IGNORECASE,
    )
    VISCOSITY_PATTERN = re.compile(
        r"(?:[Vv]iskosität|[Vv]iscosity)" + r"[.:\s(A-Za-z)]{0,80}" +
        r":?\s*([0-9]+[.,]?[0-9]*)\s*(?:mm²/s|mPa[\s·\*]?s|cSt|cP)",
        re.IGNORECASE,
    )
    PH_PATTERN = re.compile(
        r"\bpH(?:[- ]?[Ww]ert)?" + r"[.:\s]{0,40}" +
        r":?\s*([0-9]+(?:[.,][0-9]+)?(?:\s*[-–]\s*[0-9]+(?:[.,][0-9]+)?)?)",
        re.IGNORECASE,
    )
    WATER_SOLUBILITY_PATTERN = re.compile(
        r"(?:[Ll]öslichkeit\s+in\s+Wasser|[Ww]ater\s+[Ss]olubility|[Ww]assermischbarkeit)"
        + r"[.:\s]{0,60}:?\s*([^\n]{3,80})",
        re.IGNORECASE,
    )
    STORAGE_CLASS_PATTERN = re.compile(
        r"(?:[Ll]agerklasse|[Ss]torage\s+[Cc]lass)[^:\n]{0,60}:\s*(\d+[A-Z]?(?:\.\d+[A-Z]?)?)",
        re.IGNORECASE,
    )
    WGK_PATTERN = re.compile(
        r"(?:WGK|[Ww]assergefährdungsklasse)" + r"[.:\s]{0,40}" +
        r":?\s*(\d)",
        re.IGNORECASE,
    )
    UN_NUMBER_PATTERN = re.compile(
        r"(?:UN[-.\s]*(?:Nr\.?[.:\s]{0,20})?|14\.1[^:]*:[.\s]*)" +
        r"(\d{4})\b",
        re.IGNORECASE,
    )
    ADR_CLASS_PATTERN = re.compile(
        r"(?:ADR[/\s]*Klasse|Gefahrgutklasse|[Tt]ransportgefahrenklasse)[.:\s]{0,40}:?\s*([0-9][A-Z]?(?:\.[0-9])?)",
        re.IGNORECASE,
    )

    # Abschnitts-Erkennung
    SECTION_PATTERN = re.compile(
        r"(?:^|\n)(?:ABSCHNITT|Abschnitt|SECTION|Section)\s*(\d{1,2})[:\s]",
        re.IGNORECASE,
    )
    SECTION_TITLES = {
        1: "Bezeichnung", 2: "Gefahren", 3: "Zusammensetzung",
        4: "Erste-Hilfe", 5: "Brandschutzmassnahmen", 6: "Freisetzung",
        7: "Handhabung+Lagerung", 8: "Exposition+PSA", 9: "Physik+Chemie",
        10: "Stabilitaet", 11: "Toxikologie", 12: "Umwelt",
        13: "Entsorgung", 14: "Transport", 15: "Rechtsvorschriften", 16: "Sonstiges",
    }

    # Signalwörter
    SIGNAL_WORDS = {
        "gefahr": "danger",
        "danger": "danger",
        "achtung": "warning",
        "warning": "warning",
    }

    # Metadata patterns (Section 1 + header/footer)
    PRODUCT_NAME_PATTERN = re.compile(
        r"(?:Handelsname|Produktname|Produktbezeichnung|Trade\s*name|Product\s*name)"
        r"[:\s]+([^\n]{3,80})",
        re.IGNORECASE,
    )
    MANUFACTURER_PATTERN = re.compile(
        r"(?:Hersteller|Firma|Company|Manufacturer|Supplier"
        r"|(?<!Quelle )Lieferant)\b"
        r"[ \t]*:?[ \t]*([^\n]{3,80})",
        re.IGNORECASE,
    )
    ADRESSE_COMPANY_PATTERN = re.compile(
        r"(?:^|\n)Adresse\s*\n([^\n]{3,120})",
    )
    REVISION_DATE_PATTERN = re.compile(
        r"(?:Überarbeitet\s+am|Revisionsdatum|Revision\s*date|Datum\s*der\s*Überarbeitung"
        r"|Ausgabedatum|Issue\s*date|Druckdatum|erstelltam)"
        r"[:\s]*(\d{1,2})[.\/](\d{1,2})[.\/](\d{2,4})",
        re.IGNORECASE,
    )
    REVISION_DATE_ISO_PATTERN = re.compile(
        r"(?:Überarbeitet\s+am|Revisionsdatum|Revision\s*date|Datum\s*der\s*Überarbeitung"
        r"|Ausgabedatum|Issue\s*date)"
        r"[:\s]*(\d{4})-(\d{2})-(\d{2})",
        re.IGNORECASE,
    )
    VERSION_PATTERN = re.compile(
        r"(?:Version|Fassung)[:\s]*(\d+(?:\.\d+)*)",
        re.IGNORECASE,
    )
    CAS_PATTERN = re.compile(
        r"(?:CAS)[- ]?(?:Nr\.?|Nummer|Number|No\.?)?[:\s]*(\d{2,7}-\d{2}-\d)",
        re.IGNORECASE,
    )

    LLM_CONFIDENCE_THRESHOLD = 0.6

    def parse_pdf(self, pdf_file) -> dict:
        """
        Parst ein SDS-PDF und extrahiert relevante Informationen.

        Args:
            pdf_file: Django UploadedFile oder file-like object

        Returns:
            dict mit extrahierten Daten
        """
        text = self._extract_text(pdf_file)
        result = self._parse_text(text)

        out = {
            "product_name": result.product_name,
            "manufacturer_name": result.manufacturer_name,
            "revision_date": result.revision_date,
            "version_number": result.version_number,
            "cas_number": result.cas_number,
            "signal_word": result.signal_word,
            "h_statements": result.h_statements,
            "p_statements": result.p_statements,
            "pictograms": result.pictograms,
            "flash_point_c": result.flash_point_c,
            "ignition_temperature_c": result.ignition_temperature_c,
            "lower_explosion_limit": result.lower_explosion_limit,
            "upper_explosion_limit": result.upper_explosion_limit,
            "boiling_point_c": result.boiling_point_c,
            "vapor_pressure_hpa": result.vapor_pressure_hpa,
            "density_g_cm3": result.density_g_cm3,
            "viscosity_mm2_s": result.viscosity_mm2_s,
            "ph_value": result.ph_value,
            "storage_class": result.storage_class,
            "wgk": result.wgk,
            "un_number": result.un_number,
            "adr_class": result.adr_class,
            "water_solubility": result.water_solubility,
            "appearance": result.appearance,
            "parse_confidence": result.parse_confidence,
            "_raw_text": result.raw_text,
            "_sections": result.sections,
        }

        # LLM-Anreicherung: bei niedriger Konfidenz ODER fehlenden Schlüsselfeldern
        _missing_critical = not out.get("product_name") or out.get("flash_point_c") is None
        if result.parse_confidence < self.LLM_CONFIDENCE_THRESHOLD or _missing_critical:
            out = self._llm_enrich(out)

        return out

    def _extract_text(self, pdf_file) -> str:
        """Extrahiert Text aus PDF via iil-ingest PDFExtractor."""
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        data = pdf_file.read()
        content = _pdf_extractor.extract(data)
        for err in content.extraction_errors:
            logger.warning("PDF extraction: %s", err)
        text = content.text
        # CID-kodierter Text (font nicht eingebettet): OCR erzwingen
        if text and text.count("(cid:") / max(len(text), 1) > 0.01:
            logger.info("CID-encoded PDF detected — forcing OCR fallback")
            try:
                from ingest.extractors.ocr import ocr_pdf_bytes
                ocr_text = ocr_pdf_bytes(data)
                if ocr_text.strip():
                    return ocr_text
            except Exception as ocr_exc:
                logger.warning("OCR fallback failed: %s", ocr_exc)
        return text

    def _parse_text(self, text: str) -> SdsParseResult:
        """Parst extrahierten Text."""
        result = SdsParseResult(raw_text=text)

        if not text:
            return result

        # Abschnitte extrahieren (100% Rohtext pro Sektion)
        result.sections = self._extract_sections(text)

        # H-Sätze finden
        h_matches = self.H_PATTERN.findall(text)
        result.h_statements = sorted(set(h_matches))

        # P-Sätze finden
        p_matches = self.P_PATTERN.findall(text)
        result.p_statements = sorted(set(p_matches))

        # GHS-Piktogramme finden
        ghs_matches = self.GHS_PATTERN.findall(text)
        result.pictograms = sorted(set(g.upper() for g in ghs_matches))

        # Signalwort finden
        text_lower = text.lower()
        for word, signal in self.SIGNAL_WORDS.items():
            if word in text_lower:
                result.signal_word = signal
                break

        # Physikalische Eigenschaften extrahieren
        result.flash_point_c = self._extract_number(self.FLASH_POINT_PATTERN, text)
        result.boiling_point_c = self._extract_number(self.BOILING_POINT_PATTERN, text)
        result.density_g_cm3 = self._extract_number(self.DENSITY_PATTERN, text)
        result.vapor_pressure_hpa = self._extract_number(self.VAPOR_PRESSURE_PATTERN, text)
        result.ph_value = self._extract_number(self.PH_PATTERN, text)
        result.ignition_temperature_c = self._extract_number(self.IGNITION_TEMP_PATTERN, text)
        result.lower_explosion_limit = self._extract_number(self.LEL_PATTERN, text)
        result.upper_explosion_limit = self._extract_number(self.UEL_PATTERN, text)

        # Viskosität + weitere physikalische
        result.viscosity_mm2_s = self._extract_number(self.VISCOSITY_PATTERN, text)

        # Transport + Lagerung
        un_match = self.UN_NUMBER_PATTERN.search(text)
        if un_match:
            result.un_number = f"UN {un_match.group(1)}"
        result.adr_class = self._extract_string(self.ADR_CLASS_PATTERN, text)
        result.storage_class = self._extract_string(self.STORAGE_CLASS_PATTERN, text)
        result.wgk = self._extract_string(self.WGK_PATTERN, text)
        ws_match = self.WATER_SOLUBILITY_PATTERN.search(text)
        if ws_match:
            result.water_solubility = ws_match.group(1).strip()[:120]

        # Aussehen / Appearance (handles both ': flüssig' and '\nflüssig')
        appearance_pat = re.compile(
            r"\bAggregatzustand[^\n:]*(?::[.\s]*|\s*\n\s*)([A-Za-zäöüßÄÖÜ]+)",
        )
        ap_m = appearance_pat.search(text)
        if ap_m:
            result.appearance = ap_m.group(1).strip()

        # Fallback: EU-Tabellenformat ('Eigenschaft\nWert X unit') aus Abschnitt 9
        sec9 = result.sections.get("09_Physik+Chemie", "")
        if sec9:
            if result.flash_point_c is None:
                result.flash_point_c = self._extract_number_wert(
                    r"[Ff]lammpunkt|[Ff]lash\s*[Pp]oint", sec9)
            if result.boiling_point_c is None:
                result.boiling_point_c = self._extract_number_wert(
                    r"[Ss]iedepunkt|[Ss]iede(?:beginn|bereich)|[Bb]oiling\s*[Pp]oint", sec9)
            if result.density_g_cm3 is None:
                result.density_g_cm3 = self._extract_number_wert(
                    r"[Dd]ichte|[Dd]ensity", sec9)
            if result.ignition_temperature_c is None:
                result.ignition_temperature_c = self._extract_number_wert(
                    r"[Zz]ünd(?:temperatur|punkt)|[Ss]elf[- ]?[Ii]gnition", sec9)
            if result.lower_explosion_limit is None:
                result.lower_explosion_limit = self._extract_number_wert(
                    r"[Uu]ntere\s*[Ee]xplosions|\bLEL\b|\bUEG\b", sec9)
            if result.upper_explosion_limit is None:
                result.upper_explosion_limit = self._extract_number_wert(
                    r"[Oo]bere\s*[Ee]xplosions|\bUEL\b|\bOEG\b", sec9)
            if result.vapor_pressure_hpa is None:
                result.vapor_pressure_hpa = self._extract_number_wert(
                    r"[Dd]ampfdruck|[Vv]apou?r?\s*[Pp]ressure", sec9)
            if result.ph_value is None:
                result.ph_value = self._extract_number_wert(
                    r"pH(?:[- ]?[Ww]ert)?", sec9)
            if result.density_g_cm3 is None:
                result.density_g_cm3 = self._extract_number_wert(
                    r"[Rr]elative\s*[Dd]ichte|[Ss]pezifisches\s*[Gg]ewicht", sec9)

            # Zweispalten-OCR-Fallback: Labels und Werte getrennt extrahieren
            col_data = self._parse_sec9_columns(sec9)
            if col_data.get("flash_point_c") is not None and result.flash_point_c is None:
                result.flash_point_c = col_data["flash_point_c"]
            if col_data.get("boiling_point_c") is not None and result.boiling_point_c is None:
                result.boiling_point_c = col_data["boiling_point_c"]
            if col_data.get("ignition_temperature_c") is not None and result.ignition_temperature_c is None:
                result.ignition_temperature_c = col_data["ignition_temperature_c"]
            if col_data.get("lower_explosion_limit") is not None and result.lower_explosion_limit is None:
                result.lower_explosion_limit = col_data["lower_explosion_limit"]
            if col_data.get("upper_explosion_limit") is not None and result.upper_explosion_limit is None:
                result.upper_explosion_limit = col_data["upper_explosion_limit"]
            if col_data.get("vapor_pressure_hpa") is not None and result.vapor_pressure_hpa is None:
                result.vapor_pressure_hpa = col_data["vapor_pressure_hpa"]
            if col_data.get("density_g_cm3") is not None and result.density_g_cm3 is None:
                result.density_g_cm3 = col_data["density_g_cm3"]

        # Metadaten extrahieren (Abschnitt 1 + Header)
        result.product_name = self._extract_string(
            self.PRODUCT_NAME_PATTERN,
            text,
        )
        result.manufacturer_name = self._extract_string(
            self.MANUFACTURER_PATTERN,
            text,
        )
        # Fallback: Firmenname aus 'Adresse\n<Name>' in Abschnitt 1
        if not result.manufacturer_name:
            sec1 = result.sections.get("01_Bezeichnung", "")
            cm = self.ADRESSE_COMPANY_PATTERN.search(sec1)
            if cm:
                result.manufacturer_name = cm.group(1).strip()[:120]
        result.version_number = self._extract_string(
            self.VERSION_PATTERN,
            text,
        )

        # CAS-Nummer
        cas_match = self.CAS_PATTERN.search(text)
        if cas_match:
            result.cas_number = cas_match.group(1)

        # Revisionsdatum — zuerst ISO, dann DD.MM.YYYY
        iso_match = self.REVISION_DATE_ISO_PATTERN.search(text)
        if iso_match:
            year, month, day = iso_match.groups()
            with contextlib.suppress(ValueError):
                result.revision_date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        else:
            date_match = self.REVISION_DATE_PATTERN.search(text)
            if date_match:
                day, month, year = date_match.groups()
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                with contextlib.suppress(ValueError):
                    result.revision_date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

        # Konfidenz berechnen
        result.parse_confidence = self._compute_confidence(result)

        return result

    def _extract_string(
        self,
        pattern: re.Pattern,
        text: str,
    ) -> str:
        """Extrahiert einen String aus Text mittels Regex."""
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    def _compute_confidence(self, result: SdsParseResult) -> float:
        """Berechnet Parser-Konfidenz basierend auf extrahierten Feldern."""
        score = 0.0
        checks = 0
        if result.product_name:
            score += 1.0
        checks += 1
        if result.manufacturer_name:
            score += 1.0
        checks += 1
        if result.cas_number:
            score += 1.0
        checks += 1
        if result.revision_date:
            score += 1.0
        checks += 1
        if result.signal_word != "none":
            score += 0.5
        checks += 0.5
        if result.h_statements:
            score += 0.5
        checks += 0.5
        return round(score / checks, 2) if checks else 0.0

    def _extract_number(self, pattern: re.Pattern, text: str) -> float | None:
        """Extrahiert eine Zahl aus Text mittels Regex."""
        match = pattern.search(text)
        if match:
            try:
                value_str = match.group(1).replace(",", ".").replace(" ", "")
                # Entferne Pfeil/Vergleichs-Präfixe, aber NICHT das Minus-Vorzeichen
                value_str = re.sub(r'^(?:->|>=|<=|[><])', '', value_str)
                return float(value_str)
            except (ValueError, IndexError):
                pass
        return None

    def _extract_number_wert(self, label_regex: str, text: str) -> float | None:
        """Extrahiert numerischen Wert aus EU-Tabellenformat 'Eigenschaft\nWert X unit'."""
        pat = re.compile(
            r"(?:^|\n)(?:" + label_regex + r")[^\n]{0,30}\n"
            r"(?:[^\n]{0,80}\n){0,3}?"
            r"Wert\s+([^\n]+)",
            re.IGNORECASE,
        )
        m = pat.search(text)
        if not m:
            return None
        val_str = m.group(1).strip()
        num_m = re.search(r"(-?\d+(?:[.,]\d+)?)", val_str)
        if num_m:
            with contextlib.suppress(ValueError):
                return float(num_m.group(1).replace(",", "."))
        return None

    def _parse_sec9_columns(self, sec9: str) -> dict:
        """
        Zweispalten-OCR-Format: Labels ('g) Flammpunkt:') und Werte ('4°C') erscheinen
        in getrennten Blöcken. Ordnet Werte den Labels über Reihenfolge zu.
        """
        # Labels in Reihenfolge erkennen (GHS-SDS Abschnitt 9 Buchstabenformat)
        label_order = [
            ("appearance",           r"[Aa]ggregatzustand|[Aa]ppearance|[Aa]ussehen"),
            ("odor",                 r"[Gg]eruch\b|[Oo]dou?r\b"),
            ("odor_threshold",       r"[Gg]eruchsschwelle|[Oo]dou?r\s*[Tt]hreshold"),
            ("ph_value",             r"\bpH(?:[- ]?[Ww]ert)?\b"),
            ("melting_point_c",      r"[Ss]chmelz|[Mm]elting"),
            ("boiling_point_c",      r"[Ss]iede(?:beginn|bereich|punkt)|[Bb]oiling"),
            ("flash_point_c",        r"[Ff]lammpunkt|[Ff]lash\s*[Pp]oint"),
            ("evaporation_rate",     r"[Vv]erdampfung|[Ee]vaporation"),
            ("flammability",         r"[Ee]ntz[üu]ndbar|[Ff]lammab"),
            ("lower_explosion_limit",r"[Uu]ntere\s*[Ee]xplosion|[Ll]ower\s*[Ee]xplosion|\bLEL\b|\bUEG\b"),
            ("upper_explosion_limit",r"[Oo]bere\s*[Ee]xplosion|[Uu]pper\s*[Ee]xplosion|\bUEL\b|\bOEG\b"),
            ("vapor_pressure_hpa",   r"[Dd]ampfdruck|[Vv]apou?r?\s*[Pp]ressure"),
            ("vapor_density",        r"[Dd]ampfdichte|[Vv]apou?r?\s*[Dd]ensity"),
            ("density_g_cm3",        r"[Rr]elative\s*[Dd]ichte|[Dd]ichte\b|[Dd]ensity\b"),
            ("water_solubility",     r"[Ww]asser(?:löslichkeit|mischbar)|[Ww]ater\s*[Ss]olubil"),
            ("partition_coeff",      r"[Vv]erteilungskoeff|[Pp]artition"),
            ("ignition_temperature_c",r"[Ss]elbstentzündung|[Ss]elf.?[Ii]gnition|[Zz]ündtemperatur"),
            ("decomp_temp",          r"[Zz]ersetzung|[Dd]ecomposit"),
            ("viscosity_mm2_s",      r"[Vv]iskosit|[Vv]iscosit"),
        ]

        # Positionen der Labels im Text
        label_positions = []
        for key, pattern in label_order:
            m = re.search(pattern, sec9)
            if m:
                label_positions.append((m.start(), key))
        label_positions.sort()
        ordered_keys = [k for _, k in label_positions]

        # Werte-Block: numerische Werte mit Einheiten aus dem hinteren Teil des Texts
        # Suche nach dem Punkt wo die Werte beginnen (nach dem letzten Label)
        last_label_end = 0
        for pos, _ in label_positions:
            if pos > last_label_end:
                last_label_end = pos

        value_block = sec9[last_label_end:]

        # Alle Wert-Tokens extrahieren — Klammerwerte wie (20 °C) / (1013 hPa) ausschließen
        value_pat = re.compile(
            r"(-?\d+(?:[.,]\d+)?)\s*"
            r"(°\s*C|hPa|mbar|kPa|g/cm[³3]?|g/ml|%\s*\(v/v\)|Vol[.-]?%|%|mPa[\s·*]?s|mm²/s|mg/l|g/L)",
            re.IGNORECASE,
        )
        value_tokens = []
        for m in value_pat.finditer(value_block):
            # Klammerwerte überspringen: "(" direkt vor der Zahl (Messbedingung, kein Hauptwert)
            preceding = value_block[max(0, m.start() - 3):m.start()].strip()
            if preceding.endswith("("):
                continue
            value_tokens.append((m.start(), m.group(1), m.group(2).strip()))

        result: dict = {}

        def _num(val_str: str) -> float | None:
            with contextlib.suppress(ValueError):
                return float(val_str.replace(",", "."))
            return None

        # Für jeden Key mit Label: nächsten passenden Wert suchen
        unit_map = {
            "boiling_point_c":        ["°c"],
            "flash_point_c":          ["°c"],
            "melting_point_c":        ["°c"],
            "ignition_temperature_c": ["°c"],
            "lower_explosion_limit":  ["%", "vol"],
            "upper_explosion_limit":  ["%", "vol"],
            "vapor_pressure_hpa":     ["hpa", "mbar", "kpa"],
            "density_g_cm3":          ["g/cm", "g/ml"],
            "viscosity_mm2_s":        ["mm²/s", "mpa"],
        }

        used_indices: set[int] = set()

        for idx, key in enumerate(ordered_keys):
            if key not in unit_map:
                continue
            expected_units = unit_map[key]
            # Suche den ersten ungenutzten Token mit passender Einheit
            for ti, (tpos, tval, tunit) in enumerate(value_tokens):
                if ti in used_indices:
                    continue
                tunit_low = tunit.lower()
                if any(u in tunit_low for u in expected_units):
                    v = _num(tval)
                    if v is not None:
                        result[key] = v
                        used_indices.add(ti)
                        break

        return result

    # JSON-Schema für LLM Structured Output (alle relevanten SDS-Felder)
    _LLM_SCHEMA = {
        "product_name": "string|null — Produktname aus Abschnitt 1",
        "manufacturer_name": "string|null — Hersteller/Lieferant aus Abschnitt 1",
        "cas_number": "string|null — CAS-Format XX-XX-X, aus Abschnitt 1 oder 3",
        "revision_date": "string|null — ISO-Format YYYY-MM-DD, aus Abschnitt 1",
        "version_number": "string|null — Versionsnummer des SDB",
        "signal_word": "'danger'|'warning'|null — Signalwort aus Abschnitt 2",
        "h_statements": "array[string] — H-Sätze z.B. ['H225','H319'], aus Abschnitt 2/3",
        "p_statements": "array[string] — P-Sätze z.B. ['P210','P260'], aus Abschnitt 2",
        "pictograms": "array[string] — GHS-Piktogramme z.B. ['GHS02','GHS07'], aus Abschnitt 2",
        "flash_point_c": "number|null — Flammpunkt in °C, aus Abschnitt 9",
        "ignition_temperature_c": "number|null — Zündtemperatur in °C, aus Abschnitt 9",
        "boiling_point_c": "number|null — Siedepunkt in °C, aus Abschnitt 9",
        "lower_explosion_limit": "number|null — UEG/LEL in Vol-%, aus Abschnitt 9",
        "upper_explosion_limit": "number|null — OEG/UEL in Vol-%, aus Abschnitt 9",
        "vapor_pressure_hpa": "number|null — Dampfdruck in hPa, aus Abschnitt 9",
        "density_g_cm3": "number|null — Dichte in g/cm³, aus Abschnitt 9",
        "ph_value": "number|null — pH-Wert, aus Abschnitt 9",
        "viscosity_mm2_s": "number|null — Viskosität in mm²/s, aus Abschnitt 9",
        "water_solubility": "string|null — Löslichkeit in Wasser z.B. 'vollständig', aus Abschnitt 9",
        "appearance": "string|null — Aggregatzustand z.B. 'flüssig', 'fest', aus Abschnitt 9",
        "wgk": "string|null — Wassergefährdungsklasse 1/2/3, aus Abschnitt 15",
        "storage_class": "string|null — Lagerklasse nach TRGS 510 z.B. '3', '6.1A', aus Abschnitt 15",
        "un_number": "string|null — UN-Nummer z.B. 'UN 1294', aus Abschnitt 14",
        "adr_class": "string|null — ADR-Gefahrgutklasse z.B. '3', '6.1', aus Abschnitt 14",
    }

    def _llm_enrich(self, parse_result: dict) -> dict:
        """
        LLM-Anreicherung via aifw.sync_completion (action_code=substance_import).

        Extrahiert fehlende Felder aus allen 16 SDS-Abschnitten.
        Wird aufgerufen wenn parse_confidence < LLM_CONFIDENCE_THRESHOLD.
        Regex-extrahierte Werte haben immer Vorrang (LLM füllt nur leere Felder).
        """
        try:
            from aifw import sync_completion

            sections = parse_result.get("_sections", {})

            # Alle relevanten Abschnitte für maximale Extraktion
            def _sec(keys: list[str], max_chars: int = 2000) -> str:
                for k in keys:
                    for sk, sv in sections.items():
                        if k in sk:
                            return sv[:max_chars]
                return ""

            sec1 = _sec(["01_", "01 ", "01:"], 2000)   # Bezeichnung
            sec2 = _sec(["02_", "02 ", "02:"], 1500)   # Gefahren
            sec3 = _sec(["03_", "03 ", "03:"], 1000)   # Zusammensetzung
            sec9 = _sec(["09_", "09 ", "09:"], 2500)   # Physik+Chemie
            sec14 = _sec(["14_", "14 ", "14:"], 1000)  # Transport
            sec15 = _sec(["15_", "15 ", "15:"], 1000)  # Rechtsvorschriften

            # Fallback: vollständiger Text wenn keine Abschnitte erkannt
            if not any([sec1, sec2, sec9]):
                raw = parse_result.get("_raw_text", "")
                context = raw[:8000]
            else:
                context = (
                    f"ABSCHNITT 1 (Bezeichnung):\n{sec1}\n\n"
                    f"ABSCHNITT 2 (Gefahren):\n{sec2}\n\n"
                    f"ABSCHNITT 3 (Zusammensetzung/CAS):\n{sec3}\n\n"
                    f"ABSCHNITT 9 (Physikalisch-chemische Eigenschaften):\n{sec9}\n\n"
                    f"ABSCHNITT 14 (Transport):\n{sec14}\n\n"
                    f"ABSCHNITT 15 (Rechtsvorschriften/WGK/Lagerklasse):\n{sec15}"
                )

            prompt = (
                "Du bist ein Experte für Sicherheitsdatenblätter (SDS/MSDS) nach GHS/REACH.\n"
                "Extrahiere aus dem folgenden SDS-Text alle verfügbaren Daten als JSON.\n"
                "Regeln:\n"
                "- Fehlende Werte als null ausgeben\n"
                "- Zahlen immer als number (nicht string)\n"
                "- H-/P-Sätze als Array ['H225', 'H319', ...]\n"
                "- Datum immer als ISO YYYY-MM-DD\n"
                "- signal_word: nur 'danger' oder 'warning' (deutsch: Gefahr→danger, Achtung→warning)\n"
                "- Antworte NUR mit gültigem JSON, keine Erklärungen\n\n"
                f"JSON-Schema:\n{json.dumps(self._LLM_SCHEMA, ensure_ascii=False, indent=2)}\n\n"
                f"SDS-TEXT:\n{context}"
            )

            llm_result = sync_completion(
                action_code="substance_import",
                messages=[{"role": "user", "content": prompt}],
            )

            if not llm_result.success:
                logger.warning("LLM enrichment failed: %s", llm_result.error)
                return parse_result

            llm_data = llm_result.as_json()
            if not llm_data:
                logger.warning("LLM returned no valid JSON")
                return parse_result

            logger.info(
                "LLM enrichment OK: %s fields extracted (model=%s, tokens=%s)",
                len([v for v in llm_data.values() if v is not None]),
                llm_result.model,
                llm_result.total_tokens,
            )

            # Nur leere Felder aus LLM übernehmen — Regex-Werte haben Vorrang
            _numeric = {
                "flash_point_c", "ignition_temperature_c", "boiling_point_c",
                "lower_explosion_limit", "upper_explosion_limit",
                "vapor_pressure_hpa", "density_g_cm3", "ph_value", "viscosity_mm2_s",
            }
            _strings = {
                "product_name", "manufacturer_name", "cas_number", "revision_date",
                "version_number", "signal_word", "appearance", "water_solubility",
                "wgk", "storage_class", "un_number", "adr_class",
            }
            _lists = {"h_statements", "p_statements", "pictograms"}

            for fld in _numeric | _strings:
                if not parse_result.get(fld) and llm_data.get(fld) is not None:
                    parse_result[fld] = llm_data[fld]

            for fld in _lists:
                if not parse_result.get(fld) and llm_data.get(fld):
                    parse_result[fld] = llm_data[fld]

            parse_result["_llm_enriched"] = True
            parse_result["_llm_model"] = llm_result.model

        except Exception as exc:
            logger.warning("LLM enrichment failed: %s", exc)

        return parse_result

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extrahiert alle 16 SDS-Abschnitte als Rohtext-Dict."""
        sections: dict[str, str] = {}
        splits = list(self.SECTION_PATTERN.finditer(text))
        for i, match in enumerate(splits):
            num = int(match.group(1))
            start = match.start()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            key = f"{num:02d}_{self.SECTION_TITLES.get(num, 'Abschnitt')}"
            sections[key] = text[start:end].strip()
        return sections


def parse_sds_text(text: str) -> dict:
    """
    Convenience-Funktion zum direkten Parsen von Text.

    Args:
        text: Roher Text aus SDS

    Returns:
        dict mit extrahierten Daten
    """
    parser = SdsParserService()
    result = parser._parse_text(text)
    return {
        "signal_word": result.signal_word,
        "h_statements": result.h_statements,
        "p_statements": result.p_statements,
        "pictograms": result.pictograms,
        "flash_point_c": result.flash_point_c,
        "ignition_temperature_c": result.ignition_temperature_c,
        "lower_explosion_limit": result.lower_explosion_limit,
        "upper_explosion_limit": result.upper_explosion_limit,
    }
