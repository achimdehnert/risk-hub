# src/explosionsschutz/schemas.py
"""
Pydantic Schemas für Explosionsschutz-Modul (v5)

- ZoneExtent: JSON-Schema für Zonenausdehnung
- Command DTOs für Service Layer
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator
import math


class ZoneExtent(BaseModel):
    """
    JSON Schema für Zonenausdehnung nach IEC 60079-10-1.
    
    Unterstützt verschiedene geometrische Formen:
    - sphere: Kugelförmige Zone (z.B. um Füllstutzen)
    - cylinder: Zylindrische Zone (z.B. über Wannen)
    - box: Quaderförmige Zone (z.B. Räume)
    - custom: Freiform mit Beschreibung
    """
    
    shape: Literal["sphere", "cylinder", "box", "custom"]
    
    # Für sphere
    radius_m: Optional[float] = Field(
        None, ge=0, description="Radius in Metern"
    )
    
    # Für cylinder
    diameter_m: Optional[float] = Field(
        None, ge=0, description="Durchmesser in Metern"
    )
    height_m: Optional[float] = Field(
        None, ge=0, description="Höhe in Metern"
    )
    
    # Für box
    length_m: Optional[float] = Field(
        None, ge=0, description="Länge in Metern"
    )
    width_m: Optional[float] = Field(
        None, ge=0, description="Breite in Metern"
    )
    depth_m: Optional[float] = Field(
        None, ge=0, description="Tiefe in Metern"
    )
    
    # Für alle
    origin_description: Optional[str] = Field(
        None,
        description="Beschreibung des Ursprungspunkts"
    )
    reference_drawing: Optional[str] = Field(
        None,
        description="Referenz auf technische Zeichnung"
    )
    
    # Für custom
    custom_description: Optional[str] = Field(
        None,
        description="Freitextbeschreibung für komplexe Geometrien"
    )
    
    @model_validator(mode="after")
    def validate_shape_fields(self):
        """Validiert, dass die richtigen Felder für die Shape gesetzt sind"""
        if self.shape == "sphere":
            if self.radius_m is None:
                raise ValueError("radius_m erforderlich für shape='sphere'")
        elif self.shape == "cylinder":
            if self.diameter_m is None or self.height_m is None:
                raise ValueError(
                    "diameter_m und height_m erforderlich für shape='cylinder'"
                )
        elif self.shape == "box":
            if not all([self.length_m, self.width_m, self.depth_m]):
                raise ValueError(
                    "length_m, width_m, depth_m erforderlich für shape='box'"
                )
        elif self.shape == "custom":
            if not self.custom_description:
                raise ValueError(
                    "custom_description erforderlich für shape='custom'"
                )
        return self
    
    @property
    def volume_m3(self) -> Optional[float]:
        """Berechnet das Volumen der Zone in m³"""
        if self.shape == "sphere" and self.radius_m:
            return (4 / 3) * math.pi * (self.radius_m ** 3)
        elif self.shape == "cylinder" and self.diameter_m and self.height_m:
            return math.pi * ((self.diameter_m / 2) ** 2) * self.height_m
        elif self.shape == "box" and self.length_m and self.width_m and self.depth_m:
            return self.length_m * self.width_m * self.depth_m
        return None
