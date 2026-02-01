# src/substances/tests/test_sds_parser.py
"""Tests für SDS-Parser Service."""

import pytest

from substances.services.sds_parser import SdsParserService, parse_sds_text


class TestSdsParserService:
    """Tests für SdsParserService."""

    def test_parse_h_statements(self):
        """Test H-Sätze Erkennung."""
        text = """
        Gefahrenhinweise:
        H225 Flüssigkeit und Dampf leicht entzündbar
        H319 Verursacht schwere Augenreizung
        H336 Kann Schläfrigkeit und Benommenheit verursachen
        """
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert "H225" in result.h_statements
        assert "H319" in result.h_statements
        assert "H336" in result.h_statements
        assert len(result.h_statements) == 3

    def test_parse_p_statements(self):
        """Test P-Sätze Erkennung."""
        text = """
        Sicherheitshinweise:
        P210 Von Hitze, heißen Oberflächen, Funken, offenen 
             Flammen und anderen Zündquellen fernhalten.
        P233 Behälter dicht verschlossen halten.
        P305+P351+P338 Bei Kontakt mit den Augen: Einige Minuten 
                       lang behutsam mit Wasser spülen.
        """
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert "P210" in result.p_statements
        assert "P233" in result.p_statements
        assert "P305+P351+P338" in result.p_statements

    def test_parse_ghs_pictograms(self):
        """Test GHS-Piktogramm Erkennung."""
        text = """
        GHS-Kennzeichnung:
        GHS02 (Flamme)
        GHS07 (Ausrufezeichen)
        """
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert "GHS02" in result.pictograms
        assert "GHS07" in result.pictograms

    def test_parse_signal_word_danger(self):
        """Test Signalwort GEFAHR."""
        text = "Signalwort: Gefahr"
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.signal_word == "danger"

    def test_parse_signal_word_warning(self):
        """Test Signalwort ACHTUNG."""
        text = "Signalwort: Achtung"
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.signal_word == "warning"

    def test_parse_flash_point(self):
        """Test Flammpunkt Erkennung."""
        text = "Flammpunkt: -17 °C"
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.flash_point_c == 17  # Ohne Minus (absolut)

    def test_parse_flash_point_positive(self):
        """Test positiver Flammpunkt."""
        text = "Flammpunkt: 23°C"
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.flash_point_c == 23

    def test_parse_ignition_temperature(self):
        """Test Zündtemperatur Erkennung."""
        text = "Zündtemperatur: 465 °C"
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.ignition_temperature_c == 465

    def test_parse_explosion_limits(self):
        """Test Explosionsgrenzen Erkennung."""
        text = """
        Untere Explosionsgrenze (UEG): 2,5 Vol.%
        Obere Explosionsgrenze (OEG): 13,0 Vol.%
        """
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.lower_explosion_limit == 2.5
        assert result.upper_explosion_limit == 13.0

    def test_parse_lel_uel_format(self):
        """Test LEL/UEL Format."""
        text = """
        LEL: 1.5%
        UEL: 8.0%
        """
        parser = SdsParserService()
        result = parser._parse_text(text)

        assert result.lower_explosion_limit == 1.5
        assert result.upper_explosion_limit == 8.0

    def test_parse_empty_text(self):
        """Test leerer Text."""
        parser = SdsParserService()
        result = parser._parse_text("")

        assert result.signal_word == "none"
        assert result.h_statements == []
        assert result.p_statements == []
        assert result.pictograms == []

    def test_parse_sds_text_convenience(self):
        """Test convenience function."""
        text = """
        H225 Leicht entzündbar
        P210 Von Zündquellen fernhalten
        GHS02
        Gefahr
        Flammpunkt: 12°C
        """
        result = parse_sds_text(text)

        assert "H225" in result["h_statements"]
        assert "P210" in result["p_statements"]
        assert "GHS02" in result["pictograms"]
        assert result["signal_word"] == "danger"
        assert result["flash_point_c"] == 12


class TestSdsParserRealWorld:
    """Tests mit realistischen SDS-Auszügen."""

    def test_aceton_sds_excerpt(self):
        """Test Aceton SDS Auszug."""
        text = """
        ABSCHNITT 2: Mögliche Gefahren
        
        2.1 Einstufung des Stoffs oder Gemischs
        
        Einstufung gemäß Verordnung (EG) Nr. 1272/2008 (CLP)
        
        Entzündbare Flüssigkeiten, Kategorie 2
        H225 Flüssigkeit und Dampf leicht entzündbar.
        
        Schwere Augenschädigung/Augenreizung, Kategorie 2
        H319 Verursacht schwere Augenreizung.
        
        Spezifische Zielorgan-Toxizität (einmalige Exposition), Kategorie 3
        H336 Kann Schläfrigkeit und Benommenheit verursachen.
        
        2.2 Kennzeichnungselemente
        
        Kennzeichnung gemäß Verordnung (EG) Nr. 1272/2008 (CLP)
        
        Gefahrenpiktogramme: GHS02, GHS07
        
        Signalwort: Gefahr
        
        Gefahrenhinweise:
        H225 Flüssigkeit und Dampf leicht entzündbar.
        H319 Verursacht schwere Augenreizung.
        H336 Kann Schläfrigkeit und Benommenheit verursachen.
        
        Sicherheitshinweise:
        P210 Von Hitze, heißen Oberflächen, Funken, offenen Flammen 
             und anderen Zündquellen fernhalten. Nicht rauchen.
        P280 Schutzhandschuhe/Schutzkleidung/Augenschutz/Gesichtsschutz tragen.
        P305+P351+P338 BEI KONTAKT MIT DEN AUGEN: Einige Minuten lang 
                       behutsam mit Wasser spülen.
        
        ABSCHNITT 9: Physikalische und chemische Eigenschaften
        
        Flammpunkt: -17 °C
        Zündtemperatur: 465 °C
        Untere Explosionsgrenze: 2,5 Vol.%
        Obere Explosionsgrenze: 13,0 Vol.%
        Dampfdichte: 2,0 (Luft = 1)
        """
        result = parse_sds_text(text)

        # H-Sätze
        assert "H225" in result["h_statements"]
        assert "H319" in result["h_statements"]
        assert "H336" in result["h_statements"]

        # P-Sätze
        assert "P210" in result["p_statements"]
        assert "P280" in result["p_statements"]
        assert "P305+P351+P338" in result["p_statements"]

        # Piktogramme
        assert "GHS02" in result["pictograms"]
        assert "GHS07" in result["pictograms"]

        # Signalwort
        assert result["signal_word"] == "danger"

        # Physikalische Daten
        assert result["flash_point_c"] == 17
        assert result["ignition_temperature_c"] == 465
        assert result["lower_explosion_limit"] == 2.5
        assert result["upper_explosion_limit"] == 13.0

    def test_ethanol_sds_excerpt(self):
        """Test Ethanol SDS Auszug."""
        text = """
        Gefahrenhinweise:
        H225 Flüssigkeit und Dampf leicht entzündbar.
        
        Sicherheitshinweise:
        P210 Von Zündquellen fernhalten.
        P233 Behälter dicht verschlossen halten.
        P403+P235 An einem gut belüfteten Ort aufbewahren. Kühl halten.
        
        GHS-Kennzeichnung: GHS02
        Signalwort: Gefahr
        
        Physikalisch-chemische Eigenschaften:
        Flammpunkt: 12 °C (geschlossener Tiegel)
        Zündtemperatur: 400 °C
        Explosionsgrenzen: 3,1 - 27,7 Vol.-%
        """
        result = parse_sds_text(text)

        assert "H225" in result["h_statements"]
        assert "P210" in result["p_statements"]
        assert "P403+P235" in result["p_statements"]
        assert "GHS02" in result["pictograms"]
        assert result["signal_word"] == "danger"
        assert result["flash_point_c"] == 12
        assert result["ignition_temperature_c"] == 400
