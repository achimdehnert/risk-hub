"""Norm version constants and ATEX classification data."""

NORM_TRGS_721 = "TRGS 721:2017-09"
NORM_TRGS_722 = "TRGS 722:2012-08"
NORM_EN_1127_1 = "EN 1127-1:2019"
NORM_IEC_60079_10_1 = "IEC 60079-10-1:2015"
NORM_ATEX = "ATEX 2014/34/EU"
NORM_IEC_60079_0 = "IEC 60079-0:2017"

ATEX_CATEGORIES_GAS: list[str] = ["1G", "2G", "3G"]
ATEX_CATEGORIES_DUST: list[str] = ["1D", "2D", "3D"]
TEMPERATURE_CLASSES: list[str] = ["T1", "T2", "T3", "T4", "T5", "T6"]
EXPLOSION_GROUPS_GAS: list[str] = ["IIA", "IIB", "IIC"]
EXPLOSION_GROUPS_DUST: list[str] = ["IIIA", "IIIB", "IIIC"]

SAFETY_FACTORS: dict[str, float] = {
    "jet": 5.0,
    "pool": 3.0,
    "diffuse": 10.0,
}
