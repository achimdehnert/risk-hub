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

logger = logging.getLogger(__name__)

# PDF-Bibliotheken (optional)
try:
    import PyPDF2  # noqa: F401

    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber  # noqa: F401

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


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

        # LLM-Fallback: bei niedriger Konfidenz fehlende Felder nachfüllen
        if result.parse_confidence < self.LLM_CONFIDENCE_THRESHOLD:
            out = self._llm_enrich(out)

        return out

    def _extract_text(self, pdf_file) -> str:
        """Extrahiert Text aus PDF."""
        # Versuche pdfplumber (bessere Qualität)
        if PDFPLUMBER_AVAILABLE:
            try:
                return self._extract_with_pdfplumber(pdf_file)
            except Exception:
                pass

        # Fallback zu PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                return self._extract_with_pypdf2(pdf_file)
            except Exception:
                pass

        # Kein PDF-Parser verfügbar
        return ""

    def _extract_with_pdfplumber(self, pdf_file) -> str:
        """Text-Extraktion mit pdfplumber."""
        import pdfplumber

        # Reset file pointer
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)

        text_parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        return "\n".join(text_parts)

    def _extract_with_pypdf2(self, pdf_file) -> str:
        """Text-Extraktion mit PyPDF2."""
        import PyPDF2

        # Reset file pointer
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)

        reader = PyPDF2.PdfReader(pdf_file)
        text_parts = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)

        return "\n".join(text_parts)

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

    def _llm_enrich(self, parse_result: dict) -> dict:
        """
        LLM-Fallback: füllt fehlende Felder via OpenAI gpt-4o-mini.

        Wird nur aufgerufen wenn parse_confidence < LLM_CONFIDENCE_THRESHOLD.
        Benötigt OPENAI_API_KEY in Django-Settings (decouple.config).
        """
        try:
            import openai
            from decouple import config as decouple_config

            api_key = decouple_config("OPENAI_API_KEY", default="")
            if not api_key:
                return parse_result

            sections = parse_result.get("_sections", {})
            sec1 = sections.get("01_Bezeichnung", "")[:1500]
            sec9 = next(
                (v for k, v in sections.items() if "09" in k or "Physik" in k),
                "",
            )[:2000]
            sec2 = next(
                (v for k, v in sections.items() if "02" in k or "Gefah" in k),
                "",
            )[:1000]

            context = f"ABSCHNITT 1:\n{sec1}\n\nABSCHNITT 2:\n{sec2}\n\nABSCHNITT 9:\n{sec9}"

            schema = {
                "product_name": "string|null",
                "manufacturer_name": "string|null",
                "cas_number": "string|null — CAS-Format XX-XX-X",
                "signal_word": "string|null — 'danger' oder 'warning'",
                "h_statements": "array of strings — e.g. ['H225','H319']",
                "flash_point_c": "number|null — Grad Celsius",
                "boiling_point_c": "number|null — Grad Celsius",
                "density_g_cm3": "number|null",
                "lower_explosion_limit": "number|null — Vol-%",
                "upper_explosion_limit": "number|null — Vol-%",
                "appearance": "string|null — z.B. 'flüssig', 'fest'",
            }

            prompt = (
                "Extrahiere aus folgendem SDS-Text (Sicherheitsdatenblatt) strukturierte Daten "
                "als JSON. Nur vorhandene Werte ausgeben, fehlende als null. "
                f"Schema: {json.dumps(schema, ensure_ascii=False)}\n\n"
                f"SDS-TEXT:\n{context}\n\n"
                "Antworte NUR mit gültigem JSON, keine Erklärungen."
            )

            client = openai.OpenAI(api_key=api_key, timeout=15.0)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=512,
                temperature=0,
            )

            llm_data = json.loads(response.choices[0].message.content)
            logger.info("LLM enrichment OK: %s fields", len(llm_data))

            # Nur fehlende Felder aus LLM übernehmen
            numeric_fields = {
                "flash_point_c", "boiling_point_c", "density_g_cm3",
                "lower_explosion_limit", "upper_explosion_limit",
            }
            str_fields = {
                "product_name", "manufacturer_name", "cas_number",
                "signal_word", "appearance",
            }
            for fld in numeric_fields | str_fields:
                if parse_result.get(fld) is None and llm_data.get(fld) is not None:
                    parse_result[fld] = llm_data[fld]

            if not parse_result.get("h_statements") and llm_data.get("h_statements"):
                parse_result["h_statements"] = llm_data["h_statements"]

            parse_result["_llm_enriched"] = True

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
