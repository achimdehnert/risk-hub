# src/substances/services/sds_parser.py
"""
SDS-PDF Parser Service mit OCR-Unterstützung.

Extrahiert relevante Informationen aus Sicherheitsdatenblättern:
- H-Sätze (Hazard Statements)
- P-Sätze (Precautionary Statements)
- GHS-Piktogramme
- Physikalische Eigenschaften (Flammpunkt, Zündtemperatur, etc.)
"""

import re
import io
from typing import Optional
from dataclasses import dataclass, field

# PDF-Bibliotheken (optional)
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class SdsParseResult:
    """Ergebnis des SDS-Parsings."""

    signal_word: str = "none"
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    pictograms: list[str] = field(default_factory=list)
    flash_point_c: Optional[float] = None
    ignition_temperature_c: Optional[float] = None
    lower_explosion_limit: Optional[float] = None
    upper_explosion_limit: Optional[float] = None
    boiling_point_c: Optional[float] = None
    vapor_pressure_hpa: Optional[float] = None
    density_g_cm3: Optional[float] = None
    raw_text: str = ""


class SdsParserService:
    """Service zum Parsen von SDS-PDFs."""

    # Regex-Patterns für H-/P-Sätze
    H_PATTERN = re.compile(r'\b(H[0-9]{3}[A-Za-z]?)\b')
    P_PATTERN = re.compile(r'\b(P[0-9]{3}(?:\+P[0-9]{3})*)\b')

    # Regex für Piktogramme
    GHS_PATTERN = re.compile(r'\b(GHS0[1-9])\b', re.IGNORECASE)

    # Regex für physikalische Eigenschaften
    FLASH_POINT_PATTERN = re.compile(
        r'[Ff]lammpunkt[:\s]*([->]?\s*\d+(?:[.,]\d+)?)\s*°?C',
        re.IGNORECASE
    )
    IGNITION_TEMP_PATTERN = re.compile(
        r'[Zz]ünd(?:temperatur|punkt)[:\s]*([->]?\s*\d+(?:[.,]\d+)?)\s*°?C',
        re.IGNORECASE
    )
    LEL_PATTERN = re.compile(
        r'(?:UEG|LEL|[Uu]ntere\s+[Ee]xplosions(?:grenze)?)'
        r'(?:\s*\([^)]*\))?'  # optional (UEG) etc.
        r'[:\s]*(\d+(?:[.,]\d+)?)\s*(?:Vol[.\s]*%|%)',
        re.IGNORECASE
    )
    UEL_PATTERN = re.compile(
        r'(?:OEG|UEL|[Oo]bere\s+[Ee]xplosions(?:grenze)?)'
        r'(?:\s*\([^)]*\))?'  # optional (OEG) etc.
        r'[:\s]*(\d+(?:[.,]\d+)?)\s*(?:Vol[.\s]*%|%)',
        re.IGNORECASE
    )

    # Signalwörter
    SIGNAL_WORDS = {
        "gefahr": "danger",
        "danger": "danger",
        "achtung": "warning",
        "warning": "warning",
    }

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
            "signal_word": result.signal_word,
            "h_statements": result.h_statements,
            "p_statements": result.p_statements,
            "pictograms": result.pictograms,
            "flash_point_c": result.flash_point_c,
            "ignition_temperature_c": result.ignition_temperature_c,
            "lower_explosion_limit": result.lower_explosion_limit,
            "upper_explosion_limit": result.upper_explosion_limit,
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
        if hasattr(pdf_file, 'seek'):
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
        if hasattr(pdf_file, 'seek'):
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
        result.flash_point_c = self._extract_number(
            self.FLASH_POINT_PATTERN, text
        )
        result.ignition_temperature_c = self._extract_number(
            self.IGNITION_TEMP_PATTERN, text
        )
        result.lower_explosion_limit = self._extract_number(
            self.LEL_PATTERN, text
        )
        result.upper_explosion_limit = self._extract_number(
            self.UEL_PATTERN, text
        )

        return result

    def _extract_number(
        self,
        pattern: re.Pattern,
        text: str
    ) -> Optional[float]:
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
