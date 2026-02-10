# src/substances/template_views.py
"""
Template-basierte Views für Gefahrstoff-Management (HTML-Seiten mit HTMX)
"""

from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone

from .models import (
    Party,
    Substance,
    Identifier,
    SdsRevision,
    SiteInventoryItem,
    HazardStatementRef,
    PrecautionaryStatementRef,
    PictogramRef,
)
from .forms import SubstanceForm, SdsUploadForm, PartyForm
from .services import SubstanceService, ExIntegrationService


class SubstanceHomeView(View):
    """Dashboard für Gefahrstoff-Management"""

    template_name = "substances/home.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        stats = self._get_stats(tenant_id)
        recent_substances = self._get_recent(tenant_id)

        return render(request, self.template_name, {
            "stats": stats,
            "recent_substances": recent_substances,
        })

    def _get_stats(self, tenant_id):
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        substances = Substance.objects.filter(base_filter)
        active = substances.filter(status="active").count()
        cmr_count = substances.filter(is_cmr=True, status="active").count()

        sds_pending = SdsRevision.objects.filter(
            base_filter, status="pending"
        ).count()

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
        return Substance.objects.filter(
            base_filter
        ).select_related("manufacturer").order_by("-updated_at")[:5]


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

        substances = Substance.objects.filter(base_filter).select_related(
            "manufacturer"
        ).prefetch_related("identifiers")

        if search:
            substances = substances.filter(
                Q(name__icontains=search) |
                Q(trade_name__icontains=search) |
                Q(identifiers__id_value__icontains=search)
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
            return render(request, "substances/partials/substance_table.html", {
                "substances": substances,
            })

        return render(request, self.template_name, {
            "substances": substances,
            "storage_classes": Substance.StorageClass.choices,
            "filters": {
                "search": search,
                "status": status,
                "storage_class": storage_class,
                "cmr_only": cmr_only,
            }
        })


class SubstanceDetailView(View):
    """Detail-Ansicht eines Gefahrstoffs"""

    template_name = "substances/substance_detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(
            Substance.objects.select_related("manufacturer", "supplier")
            .prefetch_related(
                "identifiers",
                "sds_revisions__hazard_statements",
                "sds_revisions__precautionary_statements",
                "sds_revisions__pictograms",
                "inventory_items__site",
            ),
            pk=pk,
            tenant_id=tenant_id
        )

        # Ex-Schutz-Daten (graceful fallback when permission
        # context is unavailable, e.g. anonymous users)
        try:
            ex_data = ExIntegrationService.get_ex_data(
                pk, tenant_id
            )
        except Exception:
            ex_data = None

        return render(request, self.template_name, {
            "substance": substance,
            "current_sds": substance.current_sds,
            "sds_history": substance.sds_revisions.all()[:5],
            "inventory": substance.inventory_items.all(),
            "ex_data": ex_data,
        })


class SubstanceCreateView(View):
    """Neuen Gefahrstoff anlegen"""

    template_name = "substances/substance_form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = SubstanceForm(tenant_id=tenant_id)

        return render(request, self.template_name, {
            "form": form,
            "title": "Neuen Gefahrstoff anlegen",
        })

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

        return render(request, self.template_name, {
            "form": form,
            "title": "Neuen Gefahrstoff anlegen",
        })


class SubstanceEditView(View):
    """Gefahrstoff bearbeiten"""

    template_name = "substances/substance_form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=pk, tenant_id=tenant_id)
        form = SubstanceForm(instance=substance, tenant_id=tenant_id)

        return render(request, self.template_name, {
            "form": form,
            "substance": substance,
            "title": f"Gefahrstoff bearbeiten: {substance.name}",
        })

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=pk, tenant_id=tenant_id)

        form = SubstanceForm(request.POST, instance=substance, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, f"Gefahrstoff '{substance.name}' aktualisiert.")
            return redirect("substances:detail", pk=substance.pk)

        return render(request, self.template_name, {
            "form": form,
            "substance": substance,
            "title": f"Gefahrstoff bearbeiten: {substance.name}",
        })


class SdsUploadView(View):
    """SDS-PDF Upload mit OCR-Parsing"""

    template_name = "substances/sds_upload.html"

    def get(self, request, substance_pk):
        tenant_id = getattr(request, "tenant_id", None)
        substance = get_object_or_404(Substance, pk=substance_pk, tenant_id=tenant_id)
        form = SdsUploadForm()

        return render(request, self.template_name, {
            "form": form,
            "substance": substance,
        })

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
                f"{len(parsed_data.get('p_statements', []))} P-Sätze"
            )
            return redirect("substances:detail", pk=substance.pk)

        return render(request, self.template_name, {
            "form": form,
            "substance": substance,
        })


class SdsApproveView(View):
    """SDS-Revision freigeben"""

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user.is_authenticated else None

        sds = get_object_or_404(SdsRevision, pk=pk, tenant_id=tenant_id)

        # Vorherige freigegebene archivieren
        sds.substance.sds_revisions.filter(
            status=SdsRevision.Status.APPROVED
        ).update(status=SdsRevision.Status.ARCHIVED)

        # Diese freigeben
        sds.status = SdsRevision.Status.APPROVED
        sds.approved_by = user_id
        sds.approved_at = timezone.now()
        sds.save()

        messages.success(request, f"SDS Rev. {sds.revision_number} freigegeben.")

        if request.headers.get("HX-Request"):
            return render(request, "substances/partials/sds_status_badge.html", {
                "sds": sds
            })

        return redirect("substances:detail", pk=sds.substance.pk)


class SubstanceSearchView(View):
    """HTMX-basierte Schnellsuche"""

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        query = request.GET.get("q", "")

        if len(query) < 2:
            return render(request, "substances/partials/search_results.html", {
                "substances": []
            })

        substances = SubstanceService.search(query, tenant_id, limit=10)

        return render(request, "substances/partials/search_results.html", {
            "substances": substances
        })


class HazardRegisterView(View):
    """Gefahrstoffverzeichnis (GefStoffV §6)"""

    template_name = "substances/hazard_register.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        substances = Substance.objects.filter(
            base_filter, status="active"
        ).select_related("manufacturer").prefetch_related(
            "identifiers",
            "sds_revisions__hazard_statements",
            "sds_revisions__pictograms",
            "inventory_items",
        ).order_by("name")

        return render(request, self.template_name, {
            "substances": substances,
        })


class PartyListView(View):
    """Liste Hersteller/Lieferanten"""

    template_name = "substances/party_list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        party_type = request.GET.get("type", "")

        parties = Party.objects.filter(base_filter).annotate(
            substance_count=Count("manufactured_substances") +
                           Count("supplied_substances")
        )

        if party_type:
            parties = parties.filter(party_type=party_type)

        return render(request, self.template_name, {
            "parties": parties.order_by("name"),
            "party_types": Party.PartyType.choices,
            "selected_type": party_type,
        })
