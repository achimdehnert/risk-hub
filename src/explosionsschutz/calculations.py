# src/explosionsschutz/calculations.py
"""
Explosionsschutz Berechnungstools

Migriert von expert_hub (bfagent).
Implementiert Berechnungen nach:
- TRGS 721: Zonenberechnung
- TRGS 722: Lüftungseffektivität
- ATEX 2014/34/EU: Equipment-Eignungsprüfung
"""

import math
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from decimal import Decimal


# =============================================================================
# STOFFDATEN (Pydantic-kompatibel)
# =============================================================================

@dataclass
class SubstanceProperties:
    """Stoffeigenschaften für Explosionsschutz."""
    
    name: str
    cas_number: str = ""
    lower_explosion_limit: float = 0.0  # UEG in Vol-%
    upper_explosion_limit: float = 0.0  # OEG in Vol-%
    flash_point_c: Optional[float] = None
    ignition_temperature_c: Optional[float] = None
    temperature_class: str = ""  # T1-T6
    explosion_group: str = ""  # IIA, IIB, IIC
    vapor_density: float = 1.0  # rel. zu Luft
    molar_mass: float = 0.0  # g/mol
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary."""
        return {
            "name": self.name,
            "cas_number": self.cas_number,
            "lower_explosion_limit": self.lower_explosion_limit,
            "upper_explosion_limit": self.upper_explosion_limit,
            "flash_point_c": self.flash_point_c,
            "ignition_temperature_c": self.ignition_temperature_c,
            "temperature_class": self.temperature_class,
            "explosion_group": self.explosion_group,
            "vapor_density": self.vapor_density,
            "molar_mass": self.molar_mass,
        }


# =============================================================================
# STOFFDATENBANK (GESTIS-basiert)
# =============================================================================

SUBSTANCE_DATABASE: Dict[str, SubstanceProperties] = {
    # Lösungsmittel
    "aceton": SubstanceProperties(
        name="Aceton",
        cas_number="67-64-1",
        lower_explosion_limit=2.5,
        upper_explosion_limit=13.0,
        flash_point_c=-17,
        ignition_temperature_c=465,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=2.0,
        molar_mass=58.08
    ),
    "ethanol": SubstanceProperties(
        name="Ethanol",
        cas_number="64-17-5",
        lower_explosion_limit=3.1,
        upper_explosion_limit=27.7,
        flash_point_c=12,
        ignition_temperature_c=363,
        temperature_class="T2",
        explosion_group="IIB",
        vapor_density=1.6,
        molar_mass=46.07
    ),
    "methanol": SubstanceProperties(
        name="Methanol",
        cas_number="67-56-1",
        lower_explosion_limit=6.0,
        upper_explosion_limit=36.0,
        flash_point_c=11,
        ignition_temperature_c=440,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=1.1,
        molar_mass=32.04
    ),
    "toluol": SubstanceProperties(
        name="Toluol",
        cas_number="108-88-3",
        lower_explosion_limit=1.1,
        upper_explosion_limit=7.1,
        flash_point_c=4,
        ignition_temperature_c=480,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.2,
        molar_mass=92.14
    ),
    "xylol": SubstanceProperties(
        name="Xylol",
        cas_number="1330-20-7",
        lower_explosion_limit=1.0,
        upper_explosion_limit=7.0,
        flash_point_c=25,
        ignition_temperature_c=463,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.7,
        molar_mass=106.17
    ),
    "benzin": SubstanceProperties(
        name="Benzin (Ottokraftstoff)",
        cas_number="86290-81-5",
        lower_explosion_limit=0.6,
        upper_explosion_limit=8.0,
        flash_point_c=-40,
        ignition_temperature_c=220,
        temperature_class="T3",
        explosion_group="IIA",
        vapor_density=3.5,
        molar_mass=100.0
    ),
    "diesel": SubstanceProperties(
        name="Dieselkraftstoff",
        cas_number="68476-34-6",
        lower_explosion_limit=0.6,
        upper_explosion_limit=6.5,
        flash_point_c=55,
        ignition_temperature_c=220,
        temperature_class="T3",
        explosion_group="IIA",
        vapor_density=4.5,
        molar_mass=200.0
    ),
    "wasserstoff": SubstanceProperties(
        name="Wasserstoff",
        cas_number="1333-74-0",
        lower_explosion_limit=4.0,
        upper_explosion_limit=77.0,
        flash_point_c=None,
        ignition_temperature_c=560,
        temperature_class="T1",
        explosion_group="IIC",
        vapor_density=0.07,
        molar_mass=2.02
    ),
    "methan": SubstanceProperties(
        name="Methan (Erdgas)",
        cas_number="74-82-8",
        lower_explosion_limit=4.4,
        upper_explosion_limit=17.0,
        flash_point_c=None,
        ignition_temperature_c=595,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=0.55,
        molar_mass=16.04
    ),
    "propan": SubstanceProperties(
        name="Propan",
        cas_number="74-98-6",
        lower_explosion_limit=1.7,
        upper_explosion_limit=10.9,
        flash_point_c=None,
        ignition_temperature_c=470,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=1.56,
        molar_mass=44.10
    ),
    "isopropanol": SubstanceProperties(
        name="Isopropanol (2-Propanol)",
        cas_number="67-63-0",
        lower_explosion_limit=2.0,
        upper_explosion_limit=12.7,
        flash_point_c=12,
        ignition_temperature_c=399,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=2.1,
        molar_mass=60.10
    ),
    "butanol": SubstanceProperties(
        name="n-Butanol",
        cas_number="71-36-3",
        lower_explosion_limit=1.4,
        upper_explosion_limit=11.2,
        flash_point_c=29,
        ignition_temperature_c=343,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=2.6,
        molar_mass=74.12
    ),
    "ethylacetat": SubstanceProperties(
        name="Ethylacetat",
        cas_number="141-78-6",
        lower_explosion_limit=2.0,
        upper_explosion_limit=11.5,
        flash_point_c=-4,
        ignition_temperature_c=426,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.0,
        molar_mass=88.11
    ),
}

# Aliase für Stoffsuche
SUBSTANCE_ALIASES: Dict[str, str] = {
    "acetone": "aceton",
    "toluene": "toluol",
    "xylene": "xylol",
    "gasoline": "benzin",
    "petrol": "benzin",
    "hydrogen": "wasserstoff",
    "methane": "methan",
    "propane": "propan",
    "2-propanol": "isopropanol",
    "ipa": "isopropanol",
    "n-butanol": "butanol",
    "ethyl acetate": "ethylacetat",
    "erdgas": "methan",
    "natural gas": "methan",
}


def get_substance_properties(substance_name: str) -> Dict[str, Any]:
    """
    Holt Stoffeigenschaften aus der Datenbank.
    
    Args:
        substance_name: Name des Stoffes (deutsch oder englisch)
        
    Returns:
        Dict mit Stoffeigenschaften oder Fehlermeldung
    """
    key = substance_name.lower().strip()
    
    if key in SUBSTANCE_ALIASES:
        key = SUBSTANCE_ALIASES[key]
    
    if key in SUBSTANCE_DATABASE:
        substance = SUBSTANCE_DATABASE[key]
        return {
            "success": True,
            "substance": substance.to_dict(),
            "source": "GESTIS-basiert"
        }
    
    # Fuzzy search
    matches = [k for k in SUBSTANCE_DATABASE.keys() if key in k or k in key]
    if matches:
        return {
            "success": False,
            "error": f"Stoff '{substance_name}' nicht gefunden",
            "suggestions": matches,
        }
    
    return {
        "success": False,
        "error": f"Stoff '{substance_name}' nicht in Datenbank",
        "available_substances": list(SUBSTANCE_DATABASE.keys())
    }


def list_substances() -> List[Dict[str, Any]]:
    """Listet alle verfügbaren Stoffe."""
    return [
        {"key": key, **substance.to_dict()}
        for key, substance in SUBSTANCE_DATABASE.items()
    ]


# =============================================================================
# ZONENBERECHNUNG (TRGS 721)
# =============================================================================

def calculate_zone_extent(
    release_rate_kg_s: float,
    ventilation_rate_m3_s: float,
    lel_percent: float = 1.5,
    substance_name: Optional[str] = None,
    room_volume_m3: Optional[float] = None,
    release_type: str = "jet"
) -> Dict[str, Any]:
    """
    Berechnet die Zonenausdehnung nach TRGS 721.
    
    Args:
        release_rate_kg_s: Freisetzungsrate in kg/s
        ventilation_rate_m3_s: Luftvolumenstrom in m³/s
        lel_percent: Untere Explosionsgrenze in Vol-% (default 1.5)
        substance_name: Optional - Stoffname für automatische LEL
        room_volume_m3: Optional - Raumvolumen für Verdünnungsberechnung
        release_type: "jet" (Strahl), "pool" (Pfütze), "diffuse" (diffus)
        
    Returns:
        Dict mit berechneter Zonenausdehnung und Klassifizierung
    """
    # Stoffdaten holen wenn angegeben
    if substance_name:
        substance_data = get_substance_properties(substance_name)
        if substance_data.get("success"):
            lel_percent = substance_data["substance"]["lower_explosion_limit"]
    
    # Sicherheitsfaktoren nach TRGS 721
    SAFETY_FACTORS = {
        "jet": 5.0,
        "pool": 3.0,
        "diffuse": 10.0
    }
    safety_factor = SAFETY_FACTORS.get(release_type, 5.0)
    
    if ventilation_rate_m3_s > 0:
        dilution_factor = ventilation_rate_m3_s / (release_rate_kg_s + 0.0001)
        lel_fraction = lel_percent / 100.0
        zone_volume_m3 = (release_rate_kg_s / lel_fraction) * safety_factor
        zone_radius_m = (zone_volume_m3 * 3 / (4 * math.pi)) ** (1/3)
        
        if dilution_factor >= 1000:
            zone_type = "2"
            zone_description = "Zone 2: Selten und nur kurzzeitig g.e.A."
        elif dilution_factor >= 100:
            zone_type = "1"
            zone_description = "Zone 1: Gelegentlich im Normalbetrieb g.e.A."
        else:
            zone_type = "0"
            zone_description = "Zone 0: Ständig oder langzeitig g.e.A."
    else:
        zone_volume_m3 = room_volume_m3 if room_volume_m3 else float('inf')
        zone_radius_m = float('inf')
        dilution_factor = 0
        zone_type = "0"
        zone_description = "Zone 0: Keine Lüftung - gesamter Raum"
    
    # Luftwechselrate
    if room_volume_m3 and ventilation_rate_m3_s > 0:
        air_changes = (ventilation_rate_m3_s * 3600) / room_volume_m3
        if air_changes >= 12:
            ventilation_class = "hoch"
        elif air_changes >= 4:
            ventilation_class = "mittel"
        else:
            ventilation_class = "gering"
    else:
        air_changes = 0
        ventilation_class = "keine"
    
    return {
        "success": True,
        "zone_volume_m3": round(zone_volume_m3, 2) if zone_volume_m3 != float('inf') else None,
        "zone_radius_m": round(zone_radius_m, 2) if zone_radius_m != float('inf') else None,
        "dilution_factor": round(dilution_factor, 2),
        "zone_type": zone_type,
        "zone_description": zone_description,
        "ventilation": {
            "air_changes_per_hour": round(air_changes, 1),
            "classification": ventilation_class
        },
        "input_parameters": {
            "release_rate_kg_s": release_rate_kg_s,
            "ventilation_rate_m3_s": ventilation_rate_m3_s,
            "lel_percent": lel_percent,
            "release_type": release_type,
            "safety_factor": safety_factor
        },
        "calculation_basis": "TRGS 721 Anhang 1",
    }


# =============================================================================
# LÜFTUNGSANALYSE (TRGS 722)
# =============================================================================

def analyze_ventilation_effectiveness(
    room_volume_m3: float,
    air_flow_m3_h: float,
    ventilation_type: str = "technisch",
    has_ex_zone: bool = True
) -> Dict[str, Any]:
    """
    Analysiert die Lüftungseffektivität nach TRGS 722.
    
    Args:
        room_volume_m3: Raumvolumen in m³
        air_flow_m3_h: Luftvolumenstrom in m³/h
        ventilation_type: "technisch", "natürlich", "keine"
        has_ex_zone: Ob Ex-Zone vorhanden ist
        
    Returns:
        Dict mit Lüftungsanalyse
    """
    air_changes = air_flow_m3_h / room_volume_m3 if room_volume_m3 > 0 else 0
    
    if ventilation_type == "technisch":
        if air_changes >= 12:
            effectiveness = "hoch"
            can_reduce_zone = True
            recommendation = "Lüftung ausreichend für Zonenreduzierung"
        elif air_changes >= 6:
            effectiveness = "mittel"
            can_reduce_zone = has_ex_zone
            recommendation = "Zonenverkleinerung möglich"
        else:
            effectiveness = "gering"
            can_reduce_zone = False
            recommendation = "Lüftung erhöhen auf mind. 6 LW/h"
    elif ventilation_type == "natürlich":
        effectiveness = "variabel"
        can_reduce_zone = False
        recommendation = "Keine Anrechnung für Zonenreduzierung nach TRGS 722"
    else:
        effectiveness = "keine"
        can_reduce_zone = False
        recommendation = "Technische Lüftung erforderlich"
    
    return {
        "success": True,
        "room_volume_m3": room_volume_m3,
        "air_flow_m3_h": air_flow_m3_h,
        "air_changes_per_hour": round(air_changes, 1),
        "ventilation_type": ventilation_type,
        "effectiveness": effectiveness,
        "can_reduce_zone": can_reduce_zone,
        "recommendation": recommendation,
        "reference": "TRGS 722"
    }


# =============================================================================
# EQUIPMENT-EIGNUNGSPRÜFUNG (ATEX)
# =============================================================================

def check_equipment_suitability(
    ex_marking: str,
    zone: str
) -> Dict[str, Any]:
    """
    Prüft ob ein Gerät für eine Ex-Zone geeignet ist.
    
    Args:
        ex_marking: Ex-Kennzeichnung (z.B. "II 2G Ex d IIB T4")
        zone: Zielzone (z.B. "1", "Zone 1", "21")
        
    Returns:
        Dict mit Eignungsprüfung
    """
    # Zone normalisieren
    zone_normalized = zone.strip().lower().replace("zone", "").strip()
    
    # Kategorie-Mapping nach ATEX
    zone_requirements = {
        "0": {"min_category": "1G", "allowed": ["1G"]},
        "1": {"min_category": "2G", "allowed": ["1G", "2G"]},
        "2": {"min_category": "3G", "allowed": ["1G", "2G", "3G"]},
        "20": {"min_category": "1D", "allowed": ["1D"]},
        "21": {"min_category": "2D", "allowed": ["1D", "2D"]},
        "22": {"min_category": "3D", "allowed": ["1D", "2D", "3D"]},
    }
    
    if zone_normalized not in zone_requirements:
        return {
            "success": False,
            "error": f"Unbekannte Zone: {zone}",
            "valid_zones": list(zone_requirements.keys())
        }
    
    requirements = zone_requirements[zone_normalized]
    marking_upper = ex_marking.upper()
    
    # Kategorie extrahieren
    detected_category = None
    for cat in ["1G", "2G", "3G", "1D", "2D", "3D"]:
        if cat in marking_upper:
            detected_category = cat
            break
    
    # Temperaturklasse extrahieren
    temp_class = None
    for tc in ["T6", "T5", "T4", "T3", "T2", "T1"]:
        if tc in marking_upper:
            temp_class = tc
            break
    
    # Explosionsgruppe extrahieren
    exp_group = None
    for eg in ["IIC", "IIB", "IIA"]:
        if eg in marking_upper:
            exp_group = eg
            break
    
    # Eignung prüfen
    is_suitable = detected_category in requirements["allowed"] if detected_category else False
    
    issues = []
    recommendations = []
    
    if not detected_category:
        issues.append("Keine Gerätekategorie erkannt")
        recommendations.append(f"Erforderlich: {requirements['allowed']}")
    elif not is_suitable:
        issues.append(f"Kategorie {detected_category} nicht für Zone {zone_normalized} geeignet")
        recommendations.append(f"Min. Kategorie {requirements['min_category']} erforderlich")
    
    if not temp_class:
        issues.append("Keine Temperaturklasse erkannt")
    
    if not exp_group:
        issues.append("Keine Explosionsgruppe erkannt")
    
    return {
        "success": True,
        "equipment_marking": ex_marking,
        "target_zone": zone_normalized,
        "detected": {
            "category": detected_category,
            "temperature_class": temp_class,
            "explosion_group": exp_group
        },
        "requirements": requirements,
        "is_suitable": is_suitable and len(issues) == 0,
        "issues": issues,
        "recommendations": recommendations,
        "reference": "ATEX 2014/34/EU"
    }
