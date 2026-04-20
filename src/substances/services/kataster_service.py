# substances/services/kataster_service.py
"""Service-Layer für das Gefahrstoffkataster (UC-004).

Enthält:
- ProductService: CRUD für Handelsprodukte
- UsageService: CRUD für Standort-Verwendungen
- KatasterImportService: Excel-Import Pipeline
- KatasterDashboardService: Dashboard-Aggregation
"""

import hashlib
import logging
from dataclasses import dataclass, field
from uuid import UUID

from django.db.models import Count, Q

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    """Statistik eines Excel-Imports."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class ProductService:
    """CRUD und Suche für Handelsprodukte."""

    @staticmethod
    def list_products(tenant_id: UUID, *, search: str = "", status: str = "", site_id: int | None = None):
        from substances.models import Product

        qs = (
            Product.objects.filter(tenant_id=tenant_id)
            .select_related("manufacturer", "supplier", "sds_revision")
            .prefetch_related("components__substance")
        )
        if search:
            qs = qs.filter(
                Q(trade_name__icontains=search)
                | Q(material_number__icontains=search)
                | Q(manufacturer__name__icontains=search)
            )
        if status:
            qs = qs.filter(status=status)
        if site_id:
            qs = qs.filter(usages__site_id=site_id).distinct()
        return qs.order_by("trade_name")

    @staticmethod
    def get_product(pk: int, tenant_id: UUID):
        from django.shortcuts import get_object_or_404

        from substances.models import Product

        return get_object_or_404(
            Product.objects.select_related("manufacturer", "supplier", "sds_revision")
            .prefetch_related(
                "components__substance",
                "usages__site",
                "usages__department",
            ),
            pk=pk,
            tenant_id=tenant_id,
        )

    @staticmethod
    def create_product(tenant_id: UUID, user_id: UUID | None, **kwargs):
        from substances.models import Product

        product = Product(tenant_id=tenant_id, created_by=user_id, **kwargs)
        product.full_clean()
        product.save()
        return product


class UsageService:
    """CRUD für Gefahrstoff-Verwendungen."""

    @staticmethod
    def list_usages(
        tenant_id: UUID,
        *,
        site_id: int | None = None,
        department_id: int | None = None,
        status: str = "",
        search: str = "",
        substitution_status: str = "",
    ):
        from substances.models import SubstanceUsage

        qs = (
            SubstanceUsage.objects.filter(tenant_id=tenant_id)
            .select_related("product__manufacturer", "site", "department")
        )
        if site_id:
            qs = qs.filter(site_id=site_id)
        if department_id:
            qs = qs.filter(department_id=department_id)
        if status:
            qs = qs.filter(status=status)
        if substitution_status:
            qs = qs.filter(substitution_status=substitution_status)
        if search:
            qs = qs.filter(
                Q(product__trade_name__icontains=search)
                | Q(usage_description__icontains=search)
                | Q(storage_location__icontains=search)
            )
        return qs.order_by("product__trade_name")

    @staticmethod
    def get_usage(pk: int, tenant_id: UUID):
        from django.shortcuts import get_object_or_404

        from substances.models import SubstanceUsage

        return get_object_or_404(
            SubstanceUsage.objects.select_related(
                "product__manufacturer",
                "site",
                "department",
                "operating_instruction",
                "risk_assessment",
            ),
            pk=pk,
            tenant_id=tenant_id,
        )


class KatasterDashboardService:
    """Aggregation für das Kataster-Dashboard."""

    @staticmethod
    def get_stats(tenant_id: UUID) -> dict:
        from substances.models import ImportBatch, Product, SubstanceUsage
        from tenancy.models import Department, Site

        products = Product.objects.filter(tenant_id=tenant_id)
        usages = SubstanceUsage.objects.filter(tenant_id=tenant_id)
        sites = Site.objects.filter(tenant_id=tenant_id, is_active=True)
        departments = Department.objects.filter(tenant_id=tenant_id)
        imports = ImportBatch.objects.filter(tenant_id=tenant_id)

        return {
            "total_products": products.count(),
            "active_products": products.filter(status="active").count(),
            "total_usages": usages.count(),
            "active_usages": usages.filter(status="active").count(),
            "substitution_open": usages.filter(substitution_status="open").count(),
            "sites": sites.count(),
            "departments": departments.count(),
            "imports": imports.count(),
            "imports_pending": imports.filter(status="pending").count(),
        }

    @staticmethod
    def get_site_summary(tenant_id: UUID) -> list:
        from tenancy.models import Site

        return (
            Site.objects.filter(tenant_id=tenant_id, is_active=True)
            .annotate(
                usage_count=Count("substance_usages", filter=Q(substance_usages__status="active")),
                department_count=Count("departments"),
            )
            .order_by("name")
        )

    @staticmethod
    def get_recent_products(tenant_id: UUID, limit: int = 5):
        from substances.models import Product

        return (
            Product.objects.filter(tenant_id=tenant_id)
            .select_related("manufacturer")
            .order_by("-updated_at")[:limit]
        )


class KatasterImportService:
    """Excel-Import Pipeline für das Gefahrstoffkataster."""

    def __init__(self, tenant_id: UUID, user_id: UUID | None = None):
        self.tenant_id = tenant_id
        self.user_id = user_id

    def create_batch(self, file_name: str, file_content: bytes, target_site_id: int):
        from substances.models import ImportBatch

        file_hash = hashlib.sha256(file_content).hexdigest()

        existing = ImportBatch.objects.filter(
            tenant_id=self.tenant_id, file_hash=file_hash
        ).first()
        if existing:
            return existing, True

        batch = ImportBatch.objects.create(
            tenant_id=self.tenant_id,
            created_by=self.user_id,
            file_name=file_name,
            file_hash=file_hash,
            target_site_id=target_site_id,
            status=ImportBatch.Status.PENDING,
        )
        return batch, False

    # Target fields the import pipeline understands
    TARGET_FIELDS = (
        "trade_name", "manufacturer_name", "material_number",
        "cas_number", "usage_description", "storage_location",
        "storage_class", "department_name", "hazard_symbols",
        "h_statements", "p_statements", "wgk",
    )

    def parse_excel(self, file_content: bytes) -> list[dict]:
        """Parse Excel (.xlsx or .xls) via LLM-analysierte Struktur.

        Trennung: LLM analysiert Struktur → Parser extrahiert Daten.
        LLM sieht nur Struktur/Header, niemals die eigentlichen Werte.
        Fallback auf regelbasierte Erkennung wenn LLM nicht verfügbar.
        """
        try:
            raw_rows = self._parse_xlsx(file_content)
        except Exception:
            raw_rows = self._parse_xls(file_content)

        if not raw_rows:
            return []

        # Step 1: LLM analysiert Struktur (oder Fallback)
        analysis = self._analyze_structure(raw_rows)
        logger.info("Structure analysis: %s", analysis)

        # Step 2: Deterministischer Parser extrahiert Daten
        return self._extract_rows(raw_rows, analysis)

    # ------------------------------------------------------------------
    # Step 1: Strukturanalyse (LLM mit Fallback)
    # ------------------------------------------------------------------

    @staticmethod
    def _analyze_structure(raw_rows: list[tuple]) -> dict:
        """LLM-tiefe Analyse der Tabellen-Struktur. Kein Datenzugriff."""
        try:
            return KatasterImportService._analyze_with_llm(raw_rows)
        except Exception:
            logger.warning("LLM analysis unavailable, using rule-based fallback")
            return KatasterImportService._analyze_rule_based(raw_rows)

    @staticmethod
    def _analyze_with_llm(raw_rows: list[tuple]) -> dict:
        """Sende Struktur-Preview an LLM, erhalte JSON-Mapping zurück."""
        import json

        from aifw.service import sync_completion

        # Preview: erste 20 Zeilen, nur nicht-leere Zellen (col_idx, value)
        preview_lines = []
        max_preview = min(20, len(raw_rows))
        max_cols = min(53, max((len(r) for r in raw_rows[:max_preview]), default=0))
        for idx in range(max_preview):
            cells = []
            for c in range(max_cols):
                v = str(raw_rows[idx][c] if c < len(raw_rows[idx]) else "").strip()
                if v:
                    cells.append(f"[{c}]={v[:60]}")
            if cells:
                preview_lines.append(f"Row {idx}: {', '.join(cells)}")

        prompt = (
            "Du bist ein Experte für Gefahrstoffkataster nach GefStoffV §6.\n"
            "Analysiere die STRUKTUR dieser Excel-Tabelle.\n\n"
            "VORSCHAU:\n" + "\n".join(preview_lines) + "\n\n"
            "Aufgabe: Identifiziere:\n"
            "1. header_row — 0-basierte Zeilennummer der Spaltenüberschriften\n"
            "2. sub_header_rows — Liste von Sub-Header-Zeilen (z.B. Abteilungskürzel)\n"
            "3. data_start_row — erste Zeile mit echten Produktdaten\n"
            "4. product_name_col — Spaltenindex mit Handelsname/Produkt (PFLICHT)\n"
            "5. column_mapping — Zuordnung unserer Zielfelder zu Spaltenindizes\n\n"
            "Zielfelder: trade_name, manufacturer_name, material_number, "
            "cas_number, usage_description, storage_location, storage_class, "
            "department_name, hazard_symbols, h_statements, p_statements, wgk\n\n"
            "Antworte NUR mit JSON (keine Erklärung):\n"
            "{\n"
            '  "header_row": <int>,\n'
            '  "sub_header_rows": [<int>, ...],\n'
            '  "data_start_row": <int>,\n'
            '  "product_name_col": <int>,\n'
            '  "column_mapping": {\n'
            '    "trade_name": <int>,\n'
            '    "manufacturer_name": <int or null>,\n'
            '    "material_number": <int or null>,\n'
            '    "cas_number": <int or null>,\n'
            '    "usage_description": <int or null>,\n'
            '    "storage_location": <int or null>,\n'
            '    "storage_class": <int or null>,\n'
            '    "hazard_symbols": <int or null>,\n'
            '    "h_statements": <int or null>,\n'
            '    "p_statements": <int or null>,\n'
            '    "wgk": <int or null>\n'
            "  },\n"
            '  "notes": "<kurze Beschreibung der erkannten Struktur>"\n'
            "}"
        )

        response = sync_completion(
            "kataster_import_analyze",
            messages=[{"role": "user", "content": prompt}],
            model="groq/llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=600,
        )
        text = response.content or ""

        # JSON extrahieren
        start = text.find("{")
        end = text.rfind("}") + 1
        if start < 0 or end <= start:
            raise ValueError("No JSON in LLM response")

        result = json.loads(text[start:end])

        # Validierung: product_name_col muss vorhanden sein
        if "product_name_col" not in result:
            raise ValueError("LLM did not identify product_name_col")

        return result

    @staticmethod
    def _analyze_rule_based(raw_rows: list[tuple]) -> dict:
        """Fallback: regelbasierte Header-Erkennung + bekannte Spaltenpositionen."""
        header_keywords = {
            "handelsname", "produkt", "hersteller", "firma",
            "materialnummer", "lfdnr", "bezeichnung", "gefahrstoff",
        }
        header_row_idx = 0
        for idx, row in enumerate(raw_rows[:30]):
            joined = " ".join(str(c or "").strip().lower() for c in row)
            matches = sum(1 for kw in header_keywords if kw in joined)
            if matches >= 2:
                header_row_idx = idx
                break

        # Sub-Header erkennen
        data_start = header_row_idx + 1
        if header_row_idx + 1 < len(raw_rows):
            next_texts = [str(c or "").strip() for c in raw_rows[header_row_idx + 1]]
            if next_texts and not (next_texts[0] and next_texts[0][:1].isdigit()):
                data_start = header_row_idx + 2

        # Spalten-Mapping anhand Header + Sub-Header-Text erraten
        # Merge header + sub-header rows for matching
        merged_headers = [str(h or "").strip().lower() for h in raw_rows[header_row_idx]]
        for sub_idx in range(header_row_idx + 1, data_start):
            if sub_idx < len(raw_rows):
                for col_idx, sv in enumerate(raw_rows[sub_idx]):
                    sv_str = str(sv or "").strip().lower()
                    if sv_str and col_idx < len(merged_headers):
                        if merged_headers[col_idx]:
                            merged_headers[col_idx] += " " + sv_str
                        else:
                            merged_headers[col_idx] = sv_str

        mapping = {}
        field_keywords = {
            "trade_name": ["handelsname", "produkt", "bezeichnung"],
            "manufacturer_name": ["hersteller", "firma", "lieferant"],
            "material_number": ["materialnummer", "artikelnummer", "mat.nr"],
            "usage_description": ["verwendung"],
            "storage_class": ["lagerklasse"],
            "storage_location": ["lagerort"],
            "hazard_symbols": ["symbol", "gefahrensymbol", "piktogramm"],
            "h_statements": ["h-sätze", "h-s"],
            "p_statements": ["p-sätze", "p-s"],
            "wgk": ["wgk"],
            "cas_number": ["cas"],
        }
        for field_name, keywords in field_keywords.items():
            for col_idx, h in enumerate(merged_headers):
                if any(kw in h for kw in keywords):
                    mapping[field_name] = col_idx
                    break

        product_col = mapping.get("trade_name", 1)

        return {
            "header_row": header_row_idx,
            "sub_header_rows": list(range(header_row_idx + 1, data_start)),
            "data_start_row": data_start,
            "product_name_col": product_col,
            "column_mapping": mapping,
            "notes": "rule-based fallback",
        }

    # ------------------------------------------------------------------
    # Step 2: Deterministischer Parser (kein LLM, nur Datenextraktion)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rows(raw_rows: list[tuple], analysis: dict) -> list[dict]:
        """Extrahiere Datenzeilen basierend auf der Strukturanalyse.

        Rein deterministisch — liest nur Zellwerte an den vom
        LLM/Fallback identifizierten Positionen aus.
        """
        data_start = analysis.get("data_start_row", 1)
        product_col = analysis.get("product_name_col", 1)
        col_map = analysis.get("column_mapping", {})

        result = []
        for row_idx in range(data_start, len(raw_rows)):
            row = raw_rows[row_idx]

            # Produktname prüfen — nur Zeilen mit Name sind relevant
            trade_name = str(row[product_col] if product_col < len(row) else "").strip()
            if not trade_name:
                continue

            record = {"trade_name": trade_name, "_row_number": row_idx + 1}

            # Alle gemappten Felder auslesen
            for field_name, col_idx in col_map.items():
                if field_name == "trade_name":
                    continue
                if col_idx is not None and col_idx < len(row):
                    val = row[col_idx]
                    record[field_name] = str(val).strip() if val is not None else ""

            result.append(record)

        return result

    @staticmethod
    def _parse_xlsx(file_content: bytes) -> list[tuple]:
        """Parse .xlsx via openpyxl."""
        import io

        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        return rows

    @staticmethod
    def _parse_xls(file_content: bytes) -> list[tuple]:
        """Parse .xls (legacy Excel) via xlrd."""
        import xlrd

        wb = xlrd.open_workbook(file_contents=file_content)
        ws = wb.sheet_by_index(0)
        rows = []
        for row_idx in range(ws.nrows):
            rows.append(tuple(ws.cell_value(row_idx, col) for col in range(ws.ncols)))
        return rows

    def process_batch(self, batch, rows: list[dict], column_mapping: dict) -> ImportStats:
        """Verarbeitet geparste Zeilen und erstellt/aktualisiert Produkte + Usages."""
        from substances.models import ImportRow, Product, SubstanceUsage

        stats = ImportStats()
        batch.column_mapping = column_mapping
        batch.status = batch.Status.PROCESSING
        batch.save(update_fields=["column_mapping", "status"])

        for row_data in rows:
            row_num = row_data.pop("_row_number", 0)
            import_row = ImportRow.objects.create(
                tenant_id=self.tenant_id,
                created_by=self.user_id,
                batch=batch,
                row_number=row_num,
                raw_data=row_data,
            )

            try:
                trade_name = self._map_field(row_data, column_mapping, "trade_name")
                if not trade_name:
                    import_row.status = ImportRow.Status.SKIPPED
                    import_row.messages = ["Kein Produktname gefunden"]
                    import_row.save(update_fields=["status", "messages"])
                    stats.skipped += 1
                    continue

                product, created = Product.objects.get_or_create(
                    tenant_id=self.tenant_id,
                    trade_name=trade_name,
                    manufacturer=None,
                    defaults={
                        "created_by": self.user_id,
                        "material_number": self._map_field(row_data, column_mapping, "material_number"),
                        "status": Product.Status.ACTIVE,
                    },
                )

                usage_desc = self._map_field(row_data, column_mapping, "usage_description")
                storage_loc = self._map_field(row_data, column_mapping, "storage_location")
                storage_cls = self._map_field(row_data, column_mapping, "storage_class")

                SubstanceUsage.objects.update_or_create(
                    tenant_id=self.tenant_id,
                    product=product,
                    site=batch.target_site,
                    department=None,
                    defaults={
                        "created_by": self.user_id,
                        "usage_description": usage_desc,
                        "storage_location": storage_loc,
                        "storage_class": storage_cls,
                    },
                )

                import_row.resolved_product = product
                import_row.status = ImportRow.Status.OK
                import_row.save(update_fields=["resolved_product", "status"])

                if created:
                    stats.created += 1
                else:
                    stats.updated += 1

            except Exception as e:
                logger.exception("Import row %d failed", row_num)
                import_row.status = ImportRow.Status.ERROR
                import_row.messages = [str(e)]
                import_row.save(update_fields=["status", "messages"])
                stats.errors.append(f"Zeile {row_num}: {e}")

        from django.utils import timezone

        batch.status = batch.Status.DONE if not stats.errors else batch.Status.FAILED
        batch.stats = {
            "created": stats.created,
            "updated": stats.updated,
            "skipped": stats.skipped,
            "errors": len(stats.errors),
        }
        batch.imported_at = timezone.now()
        batch.save(update_fields=["status", "stats", "imported_at"])

        return stats

    @staticmethod
    def _map_field(row_data: dict, mapping: dict, field_name: str) -> str:
        """Löst Spalten-Mapping auf und gibt den Wert zurück."""
        excel_col = mapping.get(field_name, "")
        if excel_col and excel_col in row_data:
            return row_data[excel_col].strip()
        return ""
