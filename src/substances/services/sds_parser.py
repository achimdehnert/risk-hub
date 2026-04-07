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
import re
from dataclasses import dataclass, field

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
    parse_confidence: float = 0.0
    raw_text: str = ""


class SdsParserService:
    """Service zum Parsen von SDS-PDFs."""

    # Regex-Patterns für H-/P-Sätze
    H_PATTERN = re.compile(r"\b(H[0-9]{3}[A-Za-z]?)\b")
    P_PATTERN = re.compile(r"\b(P[0-9]{3}(?:\+P[0-9]{3})*)\b")

    # Regex für Piktogramme
    GHS_PATTERN = re.compile(r"\b(GHS0[1-9])\b", re.IGNORECASE)

    # Regex für physikalische Eigenschaften
    FLASH_POINT_PATTERN = re.compile(
        r"[Ff]lammpunkt[:\s]*([->]?\s*\d+(?:[.,]\d+)?)\s*°?C", re.IGNORECASE
    )
    IGNITION_TEMP_PATTERN = re.compile(
        r"[Zz]ünd(?:temperatur|punkt)[:\s]*([->]?\s*\d+(?:[.,]\d+)?)\s*°?C", re.IGNORECASE
    )
    LEL_PATTERN = re.compile(
        r"(?:UEG|LEL|[Uu]ntere\s+[Ee]xplosions(?:grenze)?)"
        r"(?:\s*\([^)]*\))?"  # optional (UEG) etc.
        r"[:\s]*(\d+(?:[.,]\d+)?)\s*(?:Vol[.\s]*%|%)",
        re.IGNORECASE,
    )
    UEL_PATTERN = re.compile(
        r"(?:OEG|UEL|[Oo]bere\s+[Ee]xplosions(?:grenze)?)"
        r"(?:\s*\([^)]*\))?"  # optional (OEG) etc.
        r"[:\s]*(\d+(?:[.,]\d+)?)\s*(?:Vol[.\s]*%|%)",
        re.IGNORECASE,
    )

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
        r"(?:Hersteller|Lieferant|Firma|Company|Manufacturer|Supplier)"
        r"[:\s]+([^\n]{3,80})",
        re.IGNORECASE,
    )
    REVISION_DATE_PATTERN = re.compile(
        r"(?:Überarbeitet\s+am|Revisionsdatum|Revision\s*date|Datum\s*der\s*Überarbeitung)"
        r"[:\s]*(\d{1,2})[./](\d{1,2})[./](\d{2,4})",
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

        return {
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
            "parse_confidence": result.parse_confidence,
        }

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
        result.ignition_temperature_c = self._extract_number(self.IGNITION_TEMP_PATTERN, text)
        result.lower_explosion_limit = self._extract_number(self.LEL_PATTERN, text)
        result.upper_explosion_limit = self._extract_number(self.UEL_PATTERN, text)

        # Metadaten extrahieren (Abschnitt 1 + Header)
        result.product_name = self._extract_string(
            self.PRODUCT_NAME_PATTERN,
            text,
        )
        result.manufacturer_name = self._extract_string(
            self.MANUFACTURER_PATTERN,
            text,
        )
        result.version_number = self._extract_string(
            self.VERSION_PATTERN,
            text,
        )

        # CAS-Nummer
        cas_match = self.CAS_PATTERN.search(text)
        if cas_match:
            result.cas_number = cas_match.group(1)

        # Revisionsdatum
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
                # Ersetze Komma durch Punkt, entferne Leerzeichen
                value_str = match.group(1).replace(",", ".").replace(" ", "")
                # Entferne führendes Minus/Pfeil bei Bereichen
                value_str = value_str.lstrip("-").lstrip(">").lstrip("<")
                return float(value_str)
            except (ValueError, IndexError):
                pass
        return None


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
