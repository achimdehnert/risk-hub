"""
explosionsschutz.api
=====================
Django Ninja Router für CAD-Analyse-Endpunkte.

Endpunkte:
  GET  /cad/areas/{area_id}/dxf-analyse        — gespeicherte DXF-Analyse abrufen
  POST /cad/areas/{area_id}/ex-zonen           — ATEX Ex-Zonen analysieren
  POST /cad/areas/{area_id}/brandschutz        — Brandschutz-Analyse
  POST /cad/areas/{area_id}/mengen             — Mengenermittlung (GAEB-Basis)

Alle Endpunkte arbeiten auf dem gespeicherten dxf_analysis_json des Area-Modells.
Kein erneutes DXF-Upload nötig — Analyse on-demand aus gecachtem JSON.
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

logger = logging.getLogger(__name__)
router = Router(tags=["cad"])


# ---------------------------------------------------------------------------
# Schemas (Response)
# ---------------------------------------------------------------------------

class DxfAnalyseOut(Schema):
    area_id: int
    rooms_count: int
    total_area_m2: float
    layers_count: int
    dxf_version: str
    plan_type: str
    has_analysis: bool


class ExZoneOut(Schema):
    name: str
    zone_type: str
    atex_category: str
    area_m2: float
    volume_m3: float
    layer: str


class ExZonenOut(Schema):
    area_id: int
    zones: list[ExZoneOut]
    zone_summary: dict[str, float]
    total_ex_area_m2: float
    total_ex_volume_m3: float
    has_zone_0: bool
    has_dust_zones: bool
    compliance_notes: list[str]
    layer_hints: list[str]


class BrandabschnittOut(Schema):
    id: int
    room_names: list[str]
    total_area_m2: float
    limit_m2: float
    exceeds_limit: bool
    ausnutzung_pct: float


class FluchtwegOut(Schema):
    room_name: str
    area_m2: float
    nearest_exit_distance_m: float
    is_compliant: bool
    is_dead_end: bool


class BrandschutzOut(Schema):
    area_id: int
    gebaeudeklasse: str
    bgf_m2: float
    brandabschnitte: list[BrandabschnittOut]
    critical_brandabschnitte: int
    brandabschnitt_limit_m2: float
    fluchtweg_non_compliant: int
    t30_count: int
    t60_count: int
    t90_count: int
    compliance_issues: list[str]
    compliance_info: list[str]


class GAEBPositionOut(Schema):
    lv_position: str
    leistung: str
    menge: float
    einheit: str
    einheitspreis: float
    gesamtpreis: float


class MengenOut(Schema):
    area_id: int
    nutzflaeche_total_m2: float
    bruttogrundflaeche_m2: float
    wand_flaeche_gesamt_m2: float
    wand_laenge_gesamt_m: float
    tueren_gesamt: int
    fenster_gesamt: int
    gesamtkosten_indikativ: float
    kosten_pro_m2_indikativ: float
    din276_summary: dict[str, float]
    flaechen_din277: dict[str, float]
    gaeb_positions: list[GAEBPositionOut]


# ---------------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------------

class ExZonenIn(Schema):
    room_height_m: float = 3.0


class BrandschutzIn(Schema):
    floor_count: int = 1
    nutzung: str = "default"
    room_height_m: float = 3.0


class MengenIn(Schema):
    room_height_m: float = 3.0
    bgf_zuschlag: float = 1.15


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_area(area_id: int, request: HttpRequest):
    """Lädt Area mit Tenant-Filter."""
    from explosionsschutz.services import get_area_for_tenant

    tenant_id = getattr(request, "tenant_id", None)
    area = get_area_for_tenant(tenant_id, area_id)
    if not area:
        raise HttpError(404, f"Area {area_id} nicht gefunden")
    return area


def _require_dxf_analysis(area) -> dict[str, Any]:
    """Gibt dxf_analysis_json zurück oder 404."""
    data = getattr(area, "dxf_analysis_json", None)
    if not data:
        raise HttpError(
            404,
            "Keine DXF-Analyse vorhanden. Bitte zuerst eine DXF-Datei hochladen.",
        )
    return data


def _dxf_model_from_analysis(analysis: dict):
    """Rekonstruiert DXFModel-Objekt aus gecachtem JSON für Re-Analyse."""
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

    for l in analysis.get("layers", []):
        model.layers.append(DXFLayer(
            name=l.get("name", ""),
            color=l.get("color", 7),
            classified_as=l.get("classified_as", ""),
        ))

    return model


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/areas/{area_id}/dxf-analyse", response=DxfAnalyseOut)
def api_get_dxf_analyse(request: HttpRequest, area_id: int) -> DxfAnalyseOut:
    """Gibt die gespeicherte DXF-Analyse-Zusammenfassung zurück."""
    area = _get_area(area_id, request)
    data = _require_dxf_analysis(area)
    return DxfAnalyseOut(
        area_id=area_id,
        rooms_count=data.get("rooms_count", 0),
        total_area_m2=data.get("total_area_m2", 0.0),
        layers_count=data.get("layer_count", data.get("layers_count", 0)),
        dxf_version=data.get("dxf_version", ""),
        plan_type=data.get("plan_type", "unknown"),
        has_analysis=True,
    )


@router.post("/areas/{area_id}/ex-zonen", response=ExZonenOut)
def api_ex_zonen(request: HttpRequest, area_id: int, payload: ExZonenIn) -> ExZonenOut:
    """
    ATEX Ex-Zonen-Analyse aus gecachtem DXF-Analyse-JSON.

    Erkennt Zone 0/1/2 (Gas) und 20/21/22 (Staub) aus Layer- und Raumnamen.
    """
    from nl2cad.core.analyzers.ex_zonen_analyzer import ExZonenAnalyzer

    area = _get_area(area_id, request)
    data = _require_dxf_analysis(area)
    model = _dxf_model_from_analysis(data)

    analyzer = ExZonenAnalyzer(room_height_m=payload.room_height_m)
    result = analyzer.analyze(model)

    return ExZonenOut(
        area_id=area_id,
        zones=[
            ExZoneOut(
                name=z.name,
                zone_type=z.zone_type,
                atex_category=z.atex_category,
                area_m2=round(z.area_m2, 3),
                volume_m3=round(z.volume_m3, 3),
                layer=z.layer,
            )
            for z in result.zones
        ],
        zone_summary={k: round(v, 3) for k, v in result.zone_summary.items()},
        total_ex_area_m2=round(result.total_ex_area_m2, 3),
        total_ex_volume_m3=round(result.total_ex_volume_m3, 3),
        has_zone_0=result.has_zone_0,
        has_dust_zones=result.has_dust_zones,
        compliance_notes=result.compliance_notes,
        layer_hints=result.layer_hints,
    )


@router.post("/areas/{area_id}/brandschutz", response=BrandschutzOut)
def api_brandschutz(
    request: HttpRequest, area_id: int, payload: BrandschutzIn
) -> BrandschutzOut:
    """
    Brandschutz-Analyse: Gebäudeklasse, Brandabschnitte, Fluchtweg, FWK.

    Gebäudeklasse wird aus BGF + floor_count ermittelt.
    Nutzung beeinflusst Brandabschnitt-Grenzwert (wohnen/buero/gewerbe/industrie).
    """
    from nl2cad.core.analyzers.brandschutz_analyzer import BrandschutzAnalyzer

    area = _get_area(area_id, request)
    data = _require_dxf_analysis(area)
    model = _dxf_model_from_analysis(data)

    analyzer = BrandschutzAnalyzer(
        floor_count=payload.floor_count,
        nutzung=payload.nutzung,
        room_height_m=payload.room_height_m,
    )
    result = analyzer.analyze(model)

    return BrandschutzOut(
        area_id=area_id,
        gebaeudeklasse=result.gebaeudeklasse,
        bgf_m2=round(result.bgf_m2, 2),
        brandabschnitte=[
            BrandabschnittOut(
                id=b.id,
                room_names=b.room_names,
                total_area_m2=round(b.total_area_m2, 2),
                limit_m2=b.limit_m2,
                exceeds_limit=b.exceeds_limit,
                ausnutzung_pct=round(b.ausnutzung_pct, 1),
            )
            for b in result.brandabschnitte
        ],
        critical_brandabschnitte=result.critical_brandabschnitte,
        brandabschnitt_limit_m2=result.brandabschnitt_limit_m2,
        fluchtweg_non_compliant=result.fluchtweg_non_compliant,
        t30_count=result.t30_count,
        t60_count=result.t60_count,
        t90_count=result.t90_count,
        compliance_issues=result.compliance_issues,
        compliance_info=result.compliance_info,
    )


@router.post("/areas/{area_id}/mengen", response=MengenOut)
def api_mengen(
    request: HttpRequest, area_id: int, payload: MengenIn
) -> MengenOut:
    """
    Mengenermittlung + GAEB-Positions-Grundlage aus DXF-Analyse.

    Liefert Wand-, Boden-, Deckenflächen, Türen, Fenster sowie
    eine indikative Kostenschätzung und GAEB-Positionen.
    """
    from nl2cad.core.analyzers.bauteil_mengen_extractor import BauteilmengenExtractor

    area = _get_area(area_id, request)
    data = _require_dxf_analysis(area)
    model = _dxf_model_from_analysis(data)

    extractor = BauteilmengenExtractor(
        room_height_m=payload.room_height_m,
        bgf_zuschlag=payload.bgf_zuschlag,
    )
    entity_stats = data.get("entity_stats", {})
    mengen = extractor.extract(model, entity_stats=entity_stats)

    return MengenOut(
        area_id=area_id,
        nutzflaeche_total_m2=round(mengen.nutzflaeche_total_m2, 2),
        bruttogrundflaeche_m2=round(mengen.bruttogrundflaeche_m2, 2),
        wand_flaeche_gesamt_m2=round(mengen.wand_flaeche_gesamt_m2, 2),
        wand_laenge_gesamt_m=round(mengen.wand_laenge_gesamt_m, 2),
        tueren_gesamt=mengen.tueren_gesamt,
        fenster_gesamt=mengen.fenster_gesamt,
        gesamtkosten_indikativ=round(mengen.gesamtkosten_indikativ, 2),
        kosten_pro_m2_indikativ=round(mengen.kosten_pro_m2_indikativ, 2),
        din276_summary={k: round(v, 2) for k, v in mengen.din276_summary.items()},
        flaechen_din277={k: round(v, 2) for k, v in mengen.flaechen_din277.items()},
        gaeb_positions=[
            GAEBPositionOut(
                lv_position=p.lv_position,
                leistung=p.leistung,
                menge=round(p.menge, 2),
                einheit=p.einheit,
                einheitspreis=round(p.einheitspreis, 2),
                gesamtpreis=round(p.gesamtpreis, 2),
            )
            for p in mengen.gaeb_positions
        ],
    )
