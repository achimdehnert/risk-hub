# src/substances/template_views.py
"""
Template-basierte Views für Gefahrstoff-Management (HTML-Seiten mit HTMX)
"""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import SdsUploadForm, SubstanceForm
from .models import (
    HazardStatementRef,
    Identifier,
    Party,
    PictogramRef,
    PrecautionaryStatementRef,
    SdsRevision,
    SiteInventoryItem,
    Substance,
)
from .services import ExIntegrationService, SubstanceService


class SubstanceHomeView(View):
    """Dashboard für Gefahrstoff-Management"""

    template_name = "substances/home.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        stats = self._get_stats(tenant_id)
        recent_substances = self._get_recent(tenant_id)

        return render(
            request,
            self.template_name,
            {
                "stats": stats,
                "recent_substances": recent_substances,
            },
        )

    def _get_stats(self, tenant_id):
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        substances = Substance.objects.filter(base_filter)
        active = substances.filter(status="active").count()
        cmr_count = substances.filter(is_cmr=True, status="active").count()

        sds_pending = SdsRevision.objects.filter(base_filter, status="pending").count()

        inventory_items = SiteInventoryItem.objects.filter(base_filter).count()

        return {
            "total_substances": substances.count(),
            "active_substances": active,
            "cmr_substances": cmr_count,
            "sds_pending": sds_pending,
            "inventory_items": inventory_items,
        }

    def _get_recent(self, tenant_id):
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        return (
            Substance.objects.filter(base_filter)
            .select_related("manufacturer")
            .order_by("-updated_at")[:5]
        )


class SubstanceListView(View):
    """Liste aller Gefahrstoffe"""

    template_name = "substances/substance_list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        # Filter
        search = request.GET.get("search", "")
        status = request.GET.get("status", "")
        storage_class = request.GET.get("storage_class", "")
        cmr_only = request.GET.get("cmr", "") == "1"

        substances = (
            Substance.objects.filter(base_filter)
            .select_related("manufacturer")
            .prefetch_related("identifiers")
        )

        if search:
            substances = substances.filter(
                Q(name__icontains=search)
                | Q(trade_name__icontains=search)
                | Q(identifiers__id_value__icontains=search)
            ).distinct()

        if status:
            substances = substances.filter(status=status)

        if storage_class:
            substances = substances.filter(storage_class=storage_class)

        if cmr_only:
            substances = substances.filter(is_cmr=True)

        substances = substances.order_by("name")

        # HTMX partial response
        if request.headers.get("HX-Request"):
            return render(
                request,
                "substances/partials/substance_table.html",
                {
                    "substances": substances,
                },
            )

        return render(
            request,
            self.template_name,
            {
                "substances": substances,
                "storage_classes": Substance.StorageClass.choices,
                "filters": {
                    "search": search,
                    "status": status,
                    "storage_class": storage_class,
                    "cmr_only": cmr_only,
                },
            },
        )


class SubstanceDetailView(View):
    """Detail-Ansicht eines Gefahrstoffs"""

    template_name = "substances/substance_detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(
            Substance.objects.select_related("manufacturer", "supplier").prefetch_related(
                "identifiers",
                "sds_revisions__hazard_statements",
                "sds_revisions__precautionary_statements",
                "sds_revisions__pictograms",
                "inventory_items__site",
            ),
            pk=pk,
            tenant_id=tenant_id,
        )

        # Ex-Schutz-Daten (graceful fallback when permission
        # context is unavailable, e.g. anonymous users)
        try:
            ex_data = ExIntegrationService.get_ex_data(pk, tenant_id)
        except Exception:
            ex_data = None

        return render(
            request,
            self.template_name,
            {
                "substance": substance,
                "current_sds": substance.current_sds,
                "sds_history": substance.sds_revisions.all()[:5],
                "inventory": substance.inventory_items.all(),
                "ex_data": ex_data,
            },
        )


class SubstanceCreateView(View):
    """Neuen Gefahrstoff anlegen"""

    template_name = "substances/substance_form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = SubstanceForm(tenant_id=tenant_id)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neuen Gefahrstoff anlegen",
            },
        )

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user.is_authenticated else None

        form = SubstanceForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            substance = form.save(commit=False)
            substance.tenant_id = tenant_id
            substance.created_by = user_id
            substance.save()

            # CAS-Nummer speichern falls angegeben
            cas_number = form.cleaned_data.get("cas_number")
            if cas_number:
                Identifier.objects.create(
                    tenant_id=tenant_id,
                    created_by=user_id,
                    substance=substance,
                    id_type="cas",
                    id_value=cas_number,
                )

            messages.success(request, f"Gefahrstoff '{substance.name}' angelegt.")
            return redirect("substances:detail", pk=substance.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neuen Gefahrstoff anlegen",
            },
        )


class SubstanceEditView(View):
    """Gefahrstoff bearbeiten"""

    template_name = "substances/substance_form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=pk, tenant_id=tenant_id)
        form = SubstanceForm(instance=substance, tenant_id=tenant_id)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "substance": substance,
                "title": f"Gefahrstoff bearbeiten: {substance.name}",
            },
        )

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=pk, tenant_id=tenant_id)

        form = SubstanceForm(request.POST, instance=substance, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, f"Gefahrstoff '{substance.name}' aktualisiert.")
            return redirect("substances:detail", pk=substance.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "substance": substance,
                "title": f"Gefahrstoff bearbeiten: {substance.name}",
            },
        )


class SdsUploadView(View):
    """SDS-PDF Upload mit OCR-Parsing"""

    template_name = "substances/sds_upload.html"

    def get(self, request, substance_pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=substance_pk, tenant_id=tenant_id)
        form = SdsUploadForm()

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "substance": substance,
            },
        )

    def post(self, request, substance_pk):
        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user.is_authenticated else None
        substance = get_object_or_404(Substance, pk=substance_pk, tenant_id=tenant_id)

        form = SdsUploadForm(request.POST, request.FILES)
        if form.is_valid():
            from .services.sds_parser import SdsParserService

            pdf_file = request.FILES["pdf_file"]
            revision_date = form.cleaned_data["revision_date"]

            # PDF parsen
            parser = SdsParserService()
            parsed_data = parser.parse_pdf(pdf_file)

            # Neue SDS-Revision erstellen
            next_rev = substance.sds_revisions.count() + 1
            sds = SdsRevision.objects.create(
                tenant_id=tenant_id,
                created_by=user_id,
                substance=substance,
                revision_number=next_rev,
                revision_date=revision_date,
                status=SdsRevision.Status.DRAFT,
                signal_word=parsed_data.get("signal_word", "none"),
            )

            # H-Sätze verknüpfen
            for h_code in parsed_data.get("h_statements", []):
                try:
                    h = HazardStatementRef.objects.get(code=h_code)
                    sds.hazard_statements.add(h)
                except HazardStatementRef.DoesNotExist:
                    pass

            # P-Sätze verknüpfen
            for p_code in parsed_data.get("p_statements", []):
                try:
                    p = PrecautionaryStatementRef.objects.get(code=p_code)
                    sds.precautionary_statements.add(p)
                except PrecautionaryStatementRef.DoesNotExist:
                    pass

            # Piktogramme verknüpfen
            for pic_code in parsed_data.get("pictograms", []):
                try:
                    pic = PictogramRef.objects.get(code=pic_code)
                    sds.pictograms.add(pic)
                except PictogramRef.DoesNotExist:
                    pass

            # Ex-Daten aktualisieren falls geparst
            if parsed_data.get("flash_point_c"):
                substance.flash_point_c = parsed_data["flash_point_c"]
            if parsed_data.get("ignition_temperature_c"):
                substance.ignition_temperature_c = parsed_data["ignition_temperature_c"]
            if parsed_data.get("lower_explosion_limit"):
                substance.lower_explosion_limit = parsed_data["lower_explosion_limit"]
            if parsed_data.get("upper_explosion_limit"):
                substance.upper_explosion_limit = parsed_data["upper_explosion_limit"]
            substance.save()

            messages.success(
                request,
                f"SDS Rev. {next_rev} hochgeladen und geparst. "
                f"Gefunden: {len(parsed_data.get('h_statements', []))} H-Sätze, "
                f"{len(parsed_data.get('p_statements', []))} P-Sätze",
            )
            return redirect("substances:detail", pk=substance.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "substance": substance,
            },
        )


class SdsApproveView(View):
    """SDS-Revision freigeben"""

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user.is_authenticated else None

        sds = get_object_or_404(SdsRevision, pk=pk, tenant_id=tenant_id)

        # Vorherige freigegebene archivieren
        sds.substance.sds_revisions.filter(status=SdsRevision.Status.APPROVED).update(
            status=SdsRevision.Status.ARCHIVED
        )

        # Diese freigeben
        sds.status = SdsRevision.Status.APPROVED
        sds.approved_by = user_id
        sds.approved_at = timezone.now()
        sds.save()

        messages.success(request, f"SDS Rev. {sds.revision_number} freigegeben.")

        if request.headers.get("HX-Request"):
            return render(request, "substances/partials/sds_status_badge.html", {"sds": sds})

        return redirect("substances:detail", pk=sds.substance.pk)


class SubstanceSearchView(View):
    """HTMX-basierte Schnellsuche"""

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        query = request.GET.get("q", "")

        if len(query) < 2:
            return render(request, "substances/partials/search_results.html", {"substances": []})

        substances = SubstanceService.search(query, tenant_id, limit=10)

        return render(
            request, "substances/partials/search_results.html", {"substances": substances}
        )


class HazardRegisterView(View):
    """Gefahrstoffverzeichnis (GefStoffV §6)"""

    template_name = "substances/hazard_register.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        substances = (
            Substance.objects.filter(base_filter, status="active")
            .select_related("manufacturer")
            .prefetch_related(
                "identifiers",
                "sds_revisions__hazard_statements",
                "sds_revisions__pictograms",
                "inventory_items",
            )
            .order_by("name")
        )

        return render(
            request,
            self.template_name,
            {
                "substances": substances,
            },
        )


class PartyListView(View):
    """Liste Hersteller/Lieferanten"""

    template_name = "substances/party_list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        party_type = request.GET.get("type", "")

        parties = Party.objects.filter(base_filter).annotate(
            substance_count=Count("manufactured_substances") + Count("supplied_substances")
        )

        if party_type:
            parties = parties.filter(party_type=party_type)

        return render(
            request,
            self.template_name,
            {
                "parties": parties.order_by("name"),
                "party_types": Party.PartyType.choices,
                "selected_type": party_type,
            },
        )


class SubstanceImportView(View):
    """Gefahrstoff-Import: Upload → KI-Vorschau → Auswahl → Übernahme."""

    template_name = "substances/substance_import.html"

    def get(self, request):
        from .forms import SubstanceImportForm

        form = SubstanceImportForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        import json
        import logging

        from .forms import SubstanceImportForm
        from .services.substance_import import SubstanceImportService

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user.is_authenticated else None

        # Step 2: User confirmed import of selected substances
        if "confirm_import" in request.POST:
            return self._handle_confirm(request, tenant_id, user_id, logger)

        # Step 1: File upload → extract → preview
        form = SubstanceImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        upload = request.FILES["import_file"]
        use_ai = form.cleaned_data.get("use_ai", False)

        service = SubstanceImportService(tenant_id=tenant_id, user_id=user_id)

        try:
            if use_ai:
                from .services.ai_extraction import ai_extract_substances

                records = ai_extract_substances(
                    file_obj=upload,
                    filename=upload.name,
                    tenant_id=tenant_id,
                )
            else:
                # Strukturierter Import — auch als Preview
                records = self._structured_extract(service, upload)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {"form": SubstanceImportForm()})
        except RuntimeError as e:
            logger.exception("Import failed")
            err_msg = str(e)
            if "AuthenticationError" in err_msg or "api_key" in err_msg:
                messages.error(
                    request,
                    "KI-Service nicht verfügbar — API-Key fehlt. "
                    "Bitte ohne KI-Extraktion versuchen oder Admin kontaktieren.",
                )
            else:
                messages.error(request, f"Import fehlgeschlagen: {err_msg[:200]}")
            return render(request, self.template_name, {"form": SubstanceImportForm()})
        except Exception:
            logger.exception("Import failed")
            messages.error(request, "Import fehlgeschlagen — bitte Dateiformat prüfen.")
            return render(request, self.template_name, {"form": SubstanceImportForm()})

        if not records:
            messages.warning(request, "Keine Gefahrstoffe im Dokument erkannt.")
            return render(request, self.template_name, {"form": SubstanceImportForm()})

        # Show preview for user selection
        records_json = json.dumps(records, ensure_ascii=False)
        messages.info(
            request,
            f"{len(records)} Gefahrstoff{'e' if len(records) != 1 else ''} erkannt. "
            "Wählen Sie die zu importierenden Stoffe aus.",
        )
        return render(
            request,
            self.template_name,
            {
                "form": SubstanceImportForm(),
                "ai_preview": records,
                "records_json": records_json,
            },
        )

    def _handle_confirm(self, request, tenant_id, user_id, logger):
        """Step 2: Import selected substances from preview."""
        import json

        from .forms import SubstanceImportForm
        from .services.substance_import import SubstanceImportService

        raw = request.POST.get("records_json", "[]")
        selected = request.POST.getlist("selected")

        try:
            all_records = json.loads(raw)
        except json.JSONDecodeError:
            messages.error(request, "Fehler beim Lesen der Vorschau-Daten.")
            return render(request, self.template_name, {"form": SubstanceImportForm()})

        # Filter to selected indices
        selected_indices = set()
        for s in selected:
            try:
                selected_indices.add(int(s))
            except ValueError:
                pass

        if not selected_indices:
            messages.warning(request, "Keine Stoffe ausgewählt.")
            records_json = json.dumps(all_records, ensure_ascii=False)
            return render(
                request,
                self.template_name,
                {
                    "form": SubstanceImportForm(),
                    "ai_preview": all_records,
                    "records_json": records_json,
                },
            )

        records_to_import = [
            r for i, r in enumerate(all_records) if i in selected_indices
        ]

        service = SubstanceImportService(tenant_id=tenant_id, user_id=user_id)
        try:
            stats = service.import_from_records(records_to_import, dry_run=False)
        except Exception:
            logger.exception("Import confirm failed")
            messages.error(request, "Import fehlgeschlagen.")
            return render(request, self.template_name, {"form": SubstanceImportForm()})

        msg = (
            f"Import abgeschlossen: {stats.created} neu, "
            f"{stats.updated} aktualisiert."
        )
        if stats.errors:
            msg += f" {len(stats.errors)} Fehler: " + "; ".join(stats.errors[:5])
            messages.warning(request, msg)
        else:
            messages.success(request, msg)

        return render(
            request,
            self.template_name,
            {"form": SubstanceImportForm(), "stats": stats},
        )

    @staticmethod
    def _structured_extract(service, upload):
        """Extract records from structured file without importing."""
        import csv
        import io
        import json
        from pathlib import Path

        ext = Path(upload.name).suffix.lower()
        content = upload.read()

        if ext == ".json":
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            return json.loads(content)
        elif ext == ".csv":
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            return [dict(row) for row in reader]
        elif ext in (".xlsx", ".xls"):
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                return []
            headers = [str(h or "").strip().lower() for h in rows[0]]
            return [dict(zip(headers, [str(c or "") for c in row])) for row in rows[1:]]
        else:
            raise ValueError(f"Format {ext} ohne KI nicht unterstützt.")
