"""
DXF → SVG Konvertierung via ezdxf Drawing Addon.

Generiert eine SVG-Preview aus einer DXF-Datei für die Anzeige im Browser.
"""

import io
import logging

import ezdxf
from django.core.files.base import ContentFile
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.svg import SVGBackend

logger = logging.getLogger(__name__)


def dxf_to_svg(dxf_bytes: bytes) -> bytes:
    """
    Konvertiert DXF-Bytes in SVG-Bytes.

    Returns:
        SVG als bytes
    Raises:
        ValueError bei ungültiger DXF-Datei
    """
    try:
        doc = ezdxf.read(io.BytesIO(dxf_bytes))
    except Exception as exc:
        raise ValueError(f"Ungültige DXF-Datei: {exc}") from exc

    msp = doc.modelspace()
    backend = SVGBackend()
    ctx = RenderContext(doc)
    frontend = Frontend(ctx, backend)
    frontend.draw_layout(msp)

    svg_string = backend.get_string(
        view_box=True,
    )

    return svg_string.encode("utf-8")


def generate_svg_for_area(area) -> bool:
    """
    Generiert SVG-Preview für ein Area-Objekt und speichert sie.

    Returns:
        True wenn SVG erfolgreich generiert, False sonst
    """
    if not area.dxf_file:
        return False

    try:
        area.dxf_file.seek(0)
        dxf_bytes = area.dxf_file.read()
        svg_bytes = dxf_to_svg(dxf_bytes)

        filename = f"area_{area.pk}.svg"
        area.dxf_svg.save(filename, ContentFile(svg_bytes), save=False)

        logger.info(
            "[SVG-Export] Area %s: %d bytes SVG generiert",
            area.pk,
            len(svg_bytes),
        )
        return True

    except Exception as exc:
        logger.warning(
            "[SVG-Export] Area %s fehlgeschlagen: %s",
            area.pk,
            exc,
        )
        return False
