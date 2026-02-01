# substances/services/ex_integration.py
"""
Integration Service für Explosionsschutz-Modul.

Stellt Ex-Schutz-relevante Stoffdaten für das Explosionsschutz-Modul bereit.
"""

from typing import Optional
from uuid import UUID
from dataclasses import dataclass

from substances.models import Substance
from substances.services.substance_service import SubstanceService


@dataclass
class ExSubstanceData:
    """Ex-Schutz-relevante Stoffdaten für Zonenberechnung."""

    substance_id: UUID
    substance_name: str
    cas_number: Optional[str] = None

    # Physikalische Eigenschaften
    flash_point_c: Optional[float] = None
    ignition_temperature_c: Optional[float] = None
    lower_explosion_limit: Optional[float] = None  # Vol.%
    upper_explosion_limit: Optional[float] = None  # Vol.%
    vapor_density: Optional[float] = None  # Luft = 1

    # Klassifikation
    temperature_class: Optional[str] = None  # T1-T6
    explosion_group: Optional[str] = None    # IIA, IIB, IIC

    # SDS-Info
    sds_revision: Optional[int] = None
    sds_date: Optional[str] = None

    def get_required_equipment_category(self, zone_type: str) -> str:
        """
        Bestimmt die erforderliche Gerätekategorie für eine Zone.

        Args:
            zone_type: Zone-Typ (0, 1, 2, 20, 21, 22)

        Returns:
            Erforderliche ATEX-Kategorie (1, 2, 3)
        """
        gas_zones = {"0": "1", "1": "2", "2": "3"}
        dust_zones = {"20": "1", "21": "2", "22": "3"}

        if zone_type in gas_zones:
            return gas_zones[zone_type]
        elif zone_type in dust_zones:
            return dust_zones[zone_type]
        return "3"  # Default für non-ex

    def get_required_temperature_class(self) -> Optional[str]:
        """
        Bestimmt die erforderliche Temperaturklasse basierend auf
        der Zündtemperatur.

        Returns:
            Temperaturklasse T1-T6 oder None
        """
        if not self.ignition_temperature_c:
            return None

        t = self.ignition_temperature_c
        if t > 450:
            return "T1"
        elif t > 300:
            return "T2"
        elif t > 200:
            return "T3"
        elif t > 135:
            return "T4"
        elif t > 100:
            return "T5"
        else:
            return "T6"

    def is_flammable(self) -> bool:
        """Prüft ob der Stoff entzündbar ist."""
        if self.flash_point_c is not None and self.flash_point_c < 60:
            return True
        if self.lower_explosion_limit is not None:
            return True
        return False


class ExIntegrationService:
    """
    Service zur Integration von Stoffdaten in das Explosionsschutz-Modul.
    """

    @staticmethod
    def get_ex_data(
        substance_id: UUID,
        tenant_id: UUID
    ) -> Optional[ExSubstanceData]:
        """
        Holt Ex-Schutz-relevante Stoffdaten.

        Args:
            substance_id: UUID des Gefahrstoffs
            tenant_id: Tenant-ID

        Returns:
            ExSubstanceData oder None wenn nicht gefunden
        """
        substance = SubstanceService.get_by_id(substance_id, tenant_id)
        if not substance:
            return None

        data = SubstanceService.get_ex_relevant_data(substance)

        return ExSubstanceData(
            substance_id=substance.id,
            substance_name=data["substance_name"],
            cas_number=data["cas_number"],
            flash_point_c=data["flash_point_c"],
            ignition_temperature_c=data["ignition_temperature_c"],
            lower_explosion_limit=data["lower_explosion_limit"],
            upper_explosion_limit=data["upper_explosion_limit"],
            vapor_density=data["vapor_density"],
            temperature_class=data["temperature_class"],
            explosion_group=data["explosion_group"],
            sds_revision=data["sds_revision"],
            sds_date=data["sds_date"],
        )

    @staticmethod
    def get_ex_data_by_cas(
        cas_number: str,
        tenant_id: UUID
    ) -> Optional[ExSubstanceData]:
        """
        Holt Ex-Schutz-relevante Stoffdaten nach CAS-Nummer.

        Args:
            cas_number: CAS-Nummer (z.B. "67-64-1")
            tenant_id: Tenant-ID

        Returns:
            ExSubstanceData oder None wenn nicht gefunden
        """
        substance = SubstanceService.get_by_cas(cas_number, tenant_id)
        if not substance:
            return None

        return ExIntegrationService.get_ex_data(substance.id, tenant_id)

    @staticmethod
    def search_flammable_substances(
        query: str,
        tenant_id: UUID,
        limit: int = 20
    ) -> list[ExSubstanceData]:
        """
        Sucht nur entzündbare Gefahrstoffe (relevant für Ex-Schutz).

        Args:
            query: Suchbegriff
            tenant_id: Tenant-ID
            limit: Max. Anzahl Ergebnisse

        Returns:
            Liste von ExSubstanceData
        """
        substances = SubstanceService.search(query, tenant_id, limit * 2)

        results = []
        for substance in substances:
            ex_data = ExIntegrationService.get_ex_data(
                substance.id, tenant_id
            )
            if ex_data and ex_data.is_flammable():
                results.append(ex_data)
                if len(results) >= limit:
                    break

        return results

    @staticmethod
    def validate_equipment_for_substance(
        substance_id: UUID,
        tenant_id: UUID,
        equipment_marking: str,
        zone_type: str
    ) -> dict:
        """
        Validiert ob ein Gerät für einen Stoff in einer Zone geeignet ist.

        Args:
            substance_id: UUID des Gefahrstoffs
            tenant_id: Tenant-ID
            equipment_marking: ATEX-Kennzeichnung (z.B. "II 2G Ex db IIB T4")
            zone_type: Zone-Typ (0, 1, 2, 20, 21, 22)

        Returns:
            dict mit Validierungsergebnis
        """
        ex_data = ExIntegrationService.get_ex_data(substance_id, tenant_id)
        if not ex_data:
            return {
                "valid": False,
                "error": "Gefahrstoff nicht gefunden",
            }

        required_category = ex_data.get_required_equipment_category(zone_type)
        required_temp_class = ex_data.get_required_temperature_class()

        # Parse equipment marking (vereinfacht)
        issues = []

        # Kategorie prüfen
        if f" {required_category}G" not in equipment_marking and \
           f" {required_category}D" not in equipment_marking:
            # Prüfe ob höhere Kategorie vorhanden
            for cat in ["1", "2", "3"]:
                if int(cat) < int(required_category):
                    if f" {cat}G" in equipment_marking or \
                       f" {cat}D" in equipment_marking:
                        break
            else:
                issues.append(
                    f"Kategorie {required_category} oder höher erforderlich"
                )

        # Temperaturklasse prüfen
        # T6 ist die niedrigste Zündtemp (<85°C), T1 die höchste (>450°C)
        # Geräte mit niedrigerer Temp-Klasse (T6<T5<T4<T3<T2<T1) sind sicherer
        if required_temp_class:
            temp_order = ["T6", "T5", "T4", "T3", "T2", "T1"]
            req_idx = temp_order.index(required_temp_class)
            # Alle Klassen bis inkl. der erforderlichen sind akzeptabel
            acceptable_classes = temp_order[:req_idx + 1]
            found = any(t in equipment_marking for t in acceptable_classes)
            if not found:
                issues.append(
                    f"Temperaturklasse {required_temp_class} oder niedriger "
                    f"erforderlich (Zündtemp. {ex_data.ignition_temperature_c}°C)"
                )

        # Explosionsgruppe prüfen
        if ex_data.explosion_group:
            group_order = ["IIC", "IIB", "IIA"]
            if ex_data.explosion_group in group_order:
                req_idx = group_order.index(ex_data.explosion_group)
                found = False
                for g in group_order[:req_idx + 1]:
                    if g in equipment_marking:
                        found = True
                        break
                if not found:
                    issues.append(
                        f"Explosionsgruppe {ex_data.explosion_group} oder "
                        f"höher erforderlich"
                    )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "substance_name": ex_data.substance_name,
            "required_category": required_category,
            "required_temp_class": required_temp_class,
            "explosion_group": ex_data.explosion_group,
        }
