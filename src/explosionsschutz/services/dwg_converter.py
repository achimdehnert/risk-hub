"""
DWG → DXF Konvertierung via ODA File Converter.

ODA File Converter ist kostenlos von der Open Design Alliance:
https://www.opendesign.com/guestfiles/oda_file_converter

Installation im Docker-Image:
    apt-get install -y libfreetype6 libgl1-mesa-glx
    dpkg -i ODAFileConverter_QT6_lnxX64_8.3dll_25.3.deb
"""

import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

ODA_BINARY = os.environ.get(
    "ODA_FILE_CONVERTER",
    "/usr/bin/ODAFileConverter",
)


def is_oda_available() -> bool:
    """Prüft ob ODA File Converter installiert ist."""
    return shutil.which(ODA_BINARY) is not None or os.path.isfile(ODA_BINARY)


def dwg_to_dxf(dwg_bytes: bytes, filename: str = "input.dwg") -> bytes:
    """
    Konvertiert DWG-Bytes zu DXF-Bytes via ODA File Converter.

    Args:
        dwg_bytes: DWG-Dateiinhalt
        filename: Original-Dateiname (für Logging)

    Returns:
        DXF-Bytes

    Raises:
        RuntimeError: Wenn ODA nicht verfügbar oder Konvertierung fehlschlägt
    """
    if not is_oda_available():
        raise RuntimeError(
            "DWG-Konvertierung nicht verfügbar. "
            "Bitte DXF-Datei hochladen oder Administrator kontaktieren."
        )

    with tempfile.TemporaryDirectory(prefix="dwg2dxf_") as tmpdir:
        input_dir = os.path.join(tmpdir, "input")
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(input_dir)
        os.makedirs(output_dir)

        input_path = os.path.join(input_dir, filename)
        with open(input_path, "wb") as f:
            f.write(dwg_bytes)

        # ODA: input_dir output_dir version type recurse audit
        # ACAD2018 = AutoCAD 2018 DXF format
        cmd = [
            ODA_BINARY,
            input_dir,
            output_dir,
            "ACAD2018",  # Output version
            "DXF",       # Output type
            "0",         # No recursion
            "1",         # Audit
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"DWG-Konvertierung Timeout für {filename}"
            )

        if result.returncode != 0:
            logger.warning(
                "[DWG→DXF] ODA Fehler: %s %s",
                result.stdout,
                result.stderr,
            )

        # Output-Datei finden
        dxf_name = os.path.splitext(filename)[0] + ".dxf"
        dxf_path = os.path.join(output_dir, dxf_name)

        if not os.path.isfile(dxf_path):
            # Versuche beliebige .dxf Datei im Output
            for f in os.listdir(output_dir):
                if f.lower().endswith(".dxf"):
                    dxf_path = os.path.join(output_dir, f)
                    break
            else:
                raise RuntimeError(
                    f"DWG-Konvertierung fehlgeschlagen: "
                    f"keine DXF-Ausgabe für {filename}"
                )

        with open(dxf_path, "rb") as f:
            return f.read()
