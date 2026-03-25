"""
GESTIS-based substance database for explosion protection calculations.

Quelle: GESTIS Stoffdatenbank, https://gestis.dguv.de/
Stand: 2026-03-01 (manuell geprueft)
Naechste Pruefung faellig: 2027-03-01
Aenderungsprotokoll: CHANGELOG.md -> "Substances"
"""

from dataclasses import dataclass


@dataclass
class SubstanceProperties:
    """Physical and safety properties of a flammable substance."""

    name: str
    cas_number: str = ""
    lower_explosion_limit: float = 0.0
    upper_explosion_limit: float = 0.0
    flash_point_c: float | None = None
    ignition_temperature_c: float | None = None
    temperature_class: str = ""
    explosion_group: str = ""
    vapor_density: float = 1.0
    molar_mass_g_mol: float = 0.0
    gestis_source: str = "GESTIS/DGUV"


SUBSTANCE_DATABASE: dict[str, SubstanceProperties] = {
    "aceton": SubstanceProperties(
        name="Aceton", cas_number="67-64-1",
        lower_explosion_limit=2.5, upper_explosion_limit=13.0,
        flash_point_c=-17.0, ignition_temperature_c=465.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=2.0, molar_mass_g_mol=58.08,
    ),
    "ethanol": SubstanceProperties(
        name="Ethanol", cas_number="64-17-5",
        lower_explosion_limit=3.1, upper_explosion_limit=27.7,
        flash_point_c=12.0, ignition_temperature_c=363.0,
        temperature_class="T2", explosion_group="IIB",
        vapor_density=1.6, molar_mass_g_mol=46.07,
    ),
    "methanol": SubstanceProperties(
        name="Methanol", cas_number="67-56-1",
        lower_explosion_limit=6.0, upper_explosion_limit=36.0,
        flash_point_c=11.0, ignition_temperature_c=440.0,
        temperature_class="T2", explosion_group="IIA",
        vapor_density=1.1, molar_mass_g_mol=32.04,
    ),
    "toluol": SubstanceProperties(
        name="Toluol", cas_number="108-88-3",
        lower_explosion_limit=1.1, upper_explosion_limit=7.1,
        flash_point_c=4.0, ignition_temperature_c=480.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=3.2, molar_mass_g_mol=92.14,
    ),
    "xylol": SubstanceProperties(
        name="Xylol", cas_number="1330-20-7",
        lower_explosion_limit=1.0, upper_explosion_limit=7.0,
        flash_point_c=25.0, ignition_temperature_c=463.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=3.7, molar_mass_g_mol=106.17,
    ),
    "benzin": SubstanceProperties(
        name="Benzin (Ottokraftstoff)", cas_number="86290-81-5",
        lower_explosion_limit=0.6, upper_explosion_limit=8.0,
        flash_point_c=-40.0, ignition_temperature_c=220.0,
        temperature_class="T3", explosion_group="IIA",
        vapor_density=3.5, molar_mass_g_mol=100.0,
    ),
    "diesel": SubstanceProperties(
        name="Dieselkraftstoff", cas_number="68476-34-6",
        lower_explosion_limit=0.6, upper_explosion_limit=6.5,
        flash_point_c=55.0, ignition_temperature_c=220.0,
        temperature_class="T3", explosion_group="IIA",
        vapor_density=4.5, molar_mass_g_mol=200.0,
    ),
    "wasserstoff": SubstanceProperties(
        name="Wasserstoff", cas_number="1333-74-0",
        lower_explosion_limit=4.0, upper_explosion_limit=77.0,
        flash_point_c=None, ignition_temperature_c=560.0,
        temperature_class="T1", explosion_group="IIC",
        vapor_density=0.07, molar_mass_g_mol=2.02,
    ),
    "methan": SubstanceProperties(
        name="Methan (Erdgas)", cas_number="74-82-8",
        lower_explosion_limit=4.4, upper_explosion_limit=17.0,
        flash_point_c=None, ignition_temperature_c=595.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=0.55, molar_mass_g_mol=16.04,
    ),
    "propan": SubstanceProperties(
        name="Propan", cas_number="74-98-6",
        lower_explosion_limit=1.7, upper_explosion_limit=10.9,
        flash_point_c=None, ignition_temperature_c=470.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=1.56, molar_mass_g_mol=44.10,
    ),
    "isopropanol": SubstanceProperties(
        name="Isopropanol (2-Propanol)", cas_number="67-63-0",
        lower_explosion_limit=2.0, upper_explosion_limit=12.7,
        flash_point_c=12.0, ignition_temperature_c=399.0,
        temperature_class="T2", explosion_group="IIA",
        vapor_density=2.1, molar_mass_g_mol=60.10,
    ),
    "butanol": SubstanceProperties(
        name="n-Butanol", cas_number="71-36-3",
        lower_explosion_limit=1.4, upper_explosion_limit=11.2,
        flash_point_c=29.0, ignition_temperature_c=343.0,
        temperature_class="T2", explosion_group="IIA",
        vapor_density=2.6, molar_mass_g_mol=74.12,
    ),
    "ethylacetat": SubstanceProperties(
        name="Ethylacetat", cas_number="141-78-6",
        lower_explosion_limit=2.0, upper_explosion_limit=11.5,
        flash_point_c=-4.0, ignition_temperature_c=426.0,
        temperature_class="T1", explosion_group="IIA",
        vapor_density=3.0, molar_mass_g_mol=88.11,
    ),
}

SUBSTANCE_ALIASES: dict[str, str] = {
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
    "ethyl alcohol": "ethanol",
    "isopropyl alcohol": "isopropanol",
}
