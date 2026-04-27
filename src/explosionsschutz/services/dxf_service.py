"""
explosionsschutz.services.dxf_service
=======================================
Service Layer für DXF/DWG-Upload und Analyse.

Kein ezdxf in Views! Alle CAD-Operationen laufen durch diesen Service.
Kombiniert nl2cad-core (Parser + Analyzer + Quality) mit DWG-Converter.

Architektur:
    View → dxf_service.DXFService → nl2cad.core.analyzers.DXFAnalyzer
                                  → nl2cad.core.quality.DXFQualityChecker
                                  → nl2cad.core.parsers.dwg_converter.ODAFileConverter
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DXFUploadResult:
    """
    Ergebnis eines DXF/DWG-Uploads.

    Enthält alle Daten die View und Template benötigen —
    kein direkter nl2cad-Import in template_views.py nötig.
    """

    success: bool = False
    error: str = ""

    # Analyse-Daten für JSON-Speicherung im Model
    analysis_json: dict = field(default_factory=dict)

    # Quality-Report für Nutzer-Feedback
    is_empty: bool = False           # DXF hat Entities aber keine Räume
    has_no_entities: bool = False    # DXF ist komplett leer
    rooms_count: int = 0
    total_area_m2: float = 0.0
    layers_count: int = 0
    dxf_version: str = ""
    plan_type: str = "unknown"

    # Diagnose-Hinweise für den Nutzer bei 0 Räumen
    parse_hints: list[str] = field(default_factory=list)
    quality_issues: list[dict] = field(default_factory=list)

    # DWG-Konverter Status
    was_dwg: bool = False
    dwg_converter_used: str = ""


class DXFService:
    """
    Service für DXF/DWG-Upload-Verarbeitung.

    Usage:
        service = DXFService()
        result = service.process_upload(raw_bytes, "grundriss.dxf")

        if not result.success:
            return render(request, template, {"error": result.error})

        area.dxf_analysis_json = result.analysis_json
        area.save()
    """

    def process_upload(
        self, raw_bytes: bytes, filename: str
    ) -> DXFUploadResult:
        """
        Verarbeitet DXF/DWG-Upload komplett.

        1. DWG → DXF konvertieren (wenn nötig)
        2. Leere DXF erkennen (0 Entities)
        3. DXF analysieren (Parser + Classifier + Quality)
        4. Ergebnis strukturiert zurückgeben

        Args:
            raw_bytes: Rohe Datei-Bytes aus Request
            filename: Dateiname (für Format-Erkennung und Logging)

        Returns:
            DXFUploadResult mit allen Analyse-Daten und Fehlermeldungen
        """
        result = DXFUploadResult()
        fname_lower = filename.lower()

        # 1. DWG → DXF Konvertierung
        if fname_lower.endswith(".dwg"):
            result.was_dwg = True
            try:
                raw_bytes, converter_name = self._convert_dwg(raw_bytes, filename)
                result.dwg_converter_used = converter_name
                filename = Path(filename).stem + ".dxf"
                logger.info("[DXFService] DWG→DXF: %s via %s", filename, converter_name)
            except RuntimeError as exc:
                result.error = str(exc)
                return result

        # 2. Leere DXF erkennen (Entities im Modellraum zählen)
        entity_count, entity_stats = self._count_entities(raw_bytes)
        if entity_count == 0:
            result.has_no_entities = True
            result.error = (
                "Die DXF-Datei enthält keine Zeichnungselemente im Modellraum. "
                "Möglicherweise liegt die Geometrie im Paper Space. "
                "Bitte eine DXF mit gezeichneten Raumpolygonen hochladen."
            )
            return result

        # 3. DXF analysieren
        try:
            analysis = self._analyze(raw_bytes, filename)
        except Exception as exc:
            logger.warning("[DXFService] Analyse-Fehler: %s", exc, exc_info=True)
            result.error = f"DXF konnte nicht analysiert werden: {exc}"
            return result

        # 4. Ergebnis befüllen
        result.success = True
        result.rooms_count = analysis.rooms_count
        result.total_area_m2 = analysis.total_area_m2
        result.layers_count = analysis.layer_count
        result.dxf_version = analysis.dxf_version
        result.plan_type = analysis.plan_type
        result.is_empty = analysis.rooms_count == 0 and analysis.layer_count > 0
        result.parse_hints = analysis.quality.parse_hints
        result.quality_issues = [i for i in analysis.quality.to_dict().get("issues", [])]
        result.analysis_json = analysis.to_dict()

        logger.info(
            "[DXFService] %s: %d Räume, %.1f m², Plantyp=%s",
            filename, result.rooms_count, result.total_area_m2, result.plan_type,
        )
        return result

    def _convert_dwg(self, dwg_bytes: bytes, filename: str) -> tuple[bytes, str]:
        """Konvertiert DWG → DXF, gibt (dxf_bytes, converter_name) zurück."""
        from nl2cad.core.parsers.dwg_converter import get_best_available_converter
        converter = get_best_available_converter()
        if not converter.is_available():
            raise RuntimeError(
                "DWG-Konvertierung nicht verfügbar. "
                "Bitte DXF-Datei hochladen oder ODA File Converter installieren."
            )
        dxf_bytes = converter.convert(dwg_bytes, filename)
        return dxf_bytes, converter.name

    def _count_entities(self, raw_bytes: bytes) -> tuple[int, dict[str, int]]:
        """Zählt Entities im Modellraum ohne vollständige Analyse."""
        try:
            import io
            import ezdxf
            doc = ezdxf.read(io.StringIO(raw_bytes.decode("latin-1")))
            stats: dict[str, int] = {}
            for entity in doc.modelspace():
                try:
                    etype = entity.dxftype()
                    stats[etype] = stats.get(etype, 0) + 1
                except Exception:
                    pass
            return sum(stats.values()), stats
        except Exception as exc:
            logger.debug("[DXFService] entity_count skip: %s", exc)
            return -1, {}  # -1 = Fehler, trotzdem weitermachen

    def _analyze(self, raw_bytes: bytes, filename: str):
        """Führt vollständige Analyse mit DXFAnalyzer durch."""
        from nl2cad.core.analyzers.dxf_analyzer import DXFAnalyzer
        analyzer = DXFAnalyzer()
        return analyzer.analyze_bytes(raw_bytes, filename)


def reconstruct_dxf_model(analysis: dict):
    """
    Rekonstruiert ein DXFModel-Objekt aus gecachtem dxf_analysis_json.

    Wird von Template-Views und API-Endpunkten genutzt um
    on-demand Analysen (ExZonen, Brandschutz, Mengen) durchzuführen
    ohne die DXF-Datei erneut parsen zu müssen.
    """
    from nl2cad.core.models.dxf import DXFLayer, DXFModel, DXFRoom, Point2D

    model = DXFModel(
        source_file=analysis.get("source_file", ""),
        dxf_version=analysis.get("dxf_version", ""),
    )
    for r in analysis.get("rooms", []):
        vertices = [Point2D(v["x"], v["y"]) for v in r.get("vertices", [])]
        room = DXFRoom(
            name=r.get("name", ""),
            layer=r.get("layer", ""),
            area_m2=float(r.get("area_m2", 0)),
            perimeter_m=float(r.get("perimeter_m", 0)),
            vertices=vertices,
            din277_code=r.get("din277_code", ""),
        )
        if vertices:
            room.position = Point2D(
                sum(v.x for v in vertices) / len(vertices),
                sum(v.y for v in vertices) / len(vertices),
            )
        model.rooms.append(room)
    for layer in analysis.get("layers", []):
        model.layers.append(DXFLayer(
            name=layer.get("name", ""),
            color=layer.get("color", 7),
            classified_as=layer.get("classified_as", ""),
        ))
    return model


def is_dwg_conversion_available() -> bool:
    """Prüft ob DWG-Konvertierung verfügbar ist (für UI-Feedback)."""
    try:
        from nl2cad.core.parsers.dwg_converter import get_best_available_converter
        return get_best_available_converter().is_available()
    except Exception:
        return False
