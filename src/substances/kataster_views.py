# src/substances/kataster_views.py
"""Views für das Gefahrstoffkataster (UC-004).

Dashboard, Product CRUD, SubstanceUsage CRUD, Excel-Import.
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .kataster_forms import KatasterImportForm, ProductForm, SubstanceUsageForm
from .services.kataster_service import (
    KatasterDashboardService,
    KatasterImportService,
    ProductService,
    UsageService,
)

logger = logging.getLogger(__name__)


def _tenant_id(request):
    return getattr(request, "tenant_id", None)


# =========================================================================
# Dashboard
# =========================================================================


class KatasterDashboardView(LoginRequiredMixin, View):
    """Gefahrstoffkataster — Übersicht und Dashboard."""

    template_name = "substances/kataster/dashboard.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        stats = KatasterDashboardService.get_stats(tenant_id)
        sites = KatasterDashboardService.get_site_summary(tenant_id)
        recent_products = KatasterDashboardService.get_recent_products(tenant_id)

        return render(
            request,
            self.template_name,
            {
                "stats": stats,
                "sites": sites,
                "recent_products": recent_products,
            },
        )


# =========================================================================
# Product CRUD
# =========================================================================


class ProductListView(LoginRequiredMixin, View):
    """Handelsprodukte — Liste mit HTMX-Filter."""

    template_name = "substances/kataster/product_list.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        search = request.GET.get("search", "")
        status = request.GET.get("status", "")
        site_id = request.GET.get("site", "")

        products = ProductService.list_products(
            tenant_id,
            search=search,
            status=status,
            site_id=int(site_id) if site_id else None,
        )

        ctx = {
            "products": products,
            "filters": {"search": search, "status": status, "site": site_id},
        }

        if request.headers.get("HX-Request"):
            return render(request, "substances/kataster/partials/_product_rows.html", ctx)

        from tenancy.models import Site

        ctx["sites"] = Site.objects.filter(tenant_id=tenant_id, is_active=True).order_by("name")
        return render(request, self.template_name, ctx)


class ProductCreateView(LoginRequiredMixin, View):
    """Neues Handelsprodukt anlegen."""

    template_name = "substances/kataster/product_form.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        form = ProductForm(tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Produkt anlegen",
            },
        )

    def post(self, request):
        tenant_id = _tenant_id(request)
        form = ProductForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant_id = tenant_id
            product.created_by = request.user.id if request.user.is_authenticated else None
            product.save()
            messages.success(request, f"Produkt '{product.trade_name}' angelegt.")
            return redirect("kataster:product-detail", pk=product.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Produkt anlegen",
            },
        )


class ProductDetailView(LoginRequiredMixin, View):
    """Produktdetail mit Komponenten und Verwendungen."""

    template_name = "substances/kataster/product_detail.html"

    def get(self, request, pk):
        tenant_id = _tenant_id(request)
        product = ProductService.get_product(pk, tenant_id)
        return render(
            request,
            self.template_name,
            {
                "product": product,
                "components": product.components.select_related("substance").all(),
                "usages": product.usages.select_related("site", "department").all(),
            },
        )


class ProductEditView(LoginRequiredMixin, View):
    """Handelsprodukt bearbeiten."""

    template_name = "substances/kataster/product_form.html"

    def get(self, request, pk):
        tenant_id = _tenant_id(request)
        product = ProductService.get_product(pk, tenant_id)
        form = ProductForm(instance=product, tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "title": f"Produkt bearbeiten: {product.trade_name}",
            },
        )

    def post(self, request, pk):
        tenant_id = _tenant_id(request)
        product = ProductService.get_product(pk, tenant_id)
        form = ProductForm(request.POST, instance=product, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, f"Produkt '{product.trade_name}' aktualisiert.")
            return redirect("kataster:product-detail", pk=product.pk)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "product": product,
                "title": f"Produkt bearbeiten: {product.trade_name}",
            },
        )


# =========================================================================
# SubstanceUsage CRUD
# =========================================================================


class UsageListView(LoginRequiredMixin, View):
    """Verwendungen — Liste mit HTMX-Filter."""

    template_name = "substances/kataster/usage_list.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        search = request.GET.get("search", "")
        status = request.GET.get("status", "")
        site_id = request.GET.get("site", "")
        sub_status = request.GET.get("substitution", "")

        usages = UsageService.list_usages(
            tenant_id,
            search=search,
            status=status,
            site_id=int(site_id) if site_id else None,
            substitution_status=sub_status,
        )

        ctx = {
            "usages": usages,
            "filters": {
                "search": search,
                "status": status,
                "site": site_id,
                "substitution": sub_status,
            },
        }

        if request.headers.get("HX-Request"):
            return render(request, "substances/kataster/partials/_usage_rows.html", ctx)

        from tenancy.models import Site

        ctx["sites"] = Site.objects.filter(tenant_id=tenant_id, is_active=True).order_by("name")
        return render(request, self.template_name, ctx)


class UsageCreateView(LoginRequiredMixin, View):
    """Neue Verwendung anlegen."""

    template_name = "substances/kataster/usage_form.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        form = SubstanceUsageForm(tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neue Verwendung erfassen",
            },
        )

    def post(self, request):
        tenant_id = _tenant_id(request)
        form = SubstanceUsageForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            usage = form.save(commit=False)
            usage.tenant_id = tenant_id
            usage.created_by = request.user.id if request.user.is_authenticated else None
            usage.save()
            messages.success(request, "Verwendung erfasst.")
            return redirect("kataster:usage-list")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neue Verwendung erfassen",
            },
        )


class UsageEditView(LoginRequiredMixin, View):
    """Verwendung bearbeiten."""

    template_name = "substances/kataster/usage_form.html"

    def get(self, request, pk):
        tenant_id = _tenant_id(request)
        usage = UsageService.get_usage(pk, tenant_id)
        form = SubstanceUsageForm(instance=usage, tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "usage": usage,
                "title": f"Verwendung bearbeiten: {usage.product.trade_name}",
            },
        )

    def post(self, request, pk):
        tenant_id = _tenant_id(request)
        usage = UsageService.get_usage(pk, tenant_id)
        form = SubstanceUsageForm(request.POST, instance=usage, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, "Verwendung aktualisiert.")
            return redirect("kataster:usage-list")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "usage": usage,
                "title": f"Verwendung bearbeiten: {usage.product.trade_name}",
            },
        )


class UsageDetailView(LoginRequiredMixin, View):
    """Verwendungsdetail."""

    template_name = "substances/kataster/usage_detail.html"

    def get(self, request, pk):
        tenant_id = _tenant_id(request)
        usage = UsageService.get_usage(pk, tenant_id)
        return render(request, self.template_name, {"usage": usage})


# =========================================================================
# Excel-Import
# =========================================================================


class KatasterImportView(LoginRequiredMixin, View):
    """Excel-Import: Upload → Spalten-Mapping → Vorschau → Import."""

    template_name = "substances/kataster/import_upload.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        form = KatasterImportForm(tenant_id=tenant_id)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        tenant_id = _tenant_id(request)
        user_id = request.user.id if request.user.is_authenticated else None

        # Step 3: Execute import with confirmed mapping
        if "confirm_import" in request.POST:
            return self._execute_import(request, tenant_id, user_id)

        # Step 1: Upload → Parse → Show column mapping
        form = KatasterImportForm(request.POST, request.FILES, tenant_id=tenant_id)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        upload = request.FILES["import_file"]
        target_site_id = form.cleaned_data["target_site"]
        file_content = upload.read()

        service = KatasterImportService(tenant_id=tenant_id, user_id=user_id)
        batch, is_duplicate = service.create_batch(upload.name, file_content, target_site_id)

        if is_duplicate:
            messages.warning(request, f"Diese Datei wurde bereits importiert (Batch #{batch.pk}).")
            return render(
                request, self.template_name, {"form": KatasterImportForm(tenant_id=tenant_id)}
            )

        try:
            rows = service.parse_excel(file_content)
        except Exception:
            logger.exception("Excel parsing failed")
            messages.error(request, "Fehler beim Lesen der Excel-Datei.")
            return render(
                request, self.template_name, {"form": KatasterImportForm(tenant_id=tenant_id)}
            )

        if not rows:
            messages.warning(request, "Keine Daten in der Datei gefunden.")
            return render(
                request, self.template_name, {"form": KatasterImportForm(tenant_id=tenant_id)}
            )

        excel_columns = list(rows[0].keys())
        excel_columns = [c for c in excel_columns if not c.startswith("_")]

        target_fields = [
            ("trade_name", "Produktname / Handelsname *"),
            ("material_number", "Materialnummer"),
            ("manufacturer_name", "Hersteller"),
            ("usage_description", "Verwendungsbeschreibung"),
            ("storage_location", "Lagerort"),
            ("storage_class", "Lagerklasse"),
            ("department_name", "Abteilung"),
            ("cas_number", "CAS-Nummer"),
        ]

        # Store batch info in session
        request.session["kataster_import_batch_id"] = batch.pk
        request.session["kataster_import_rows"] = rows

        return render(
            request,
            "substances/kataster/import_mapping.html",
            {
                "batch": batch,
                "preview_rows": rows[:5],
                "excel_columns": excel_columns,
                "target_fields": target_fields,
                "total_rows": len(rows),
            },
        )

    def _execute_import(self, request, tenant_id, user_id):
        """Step 3: Führe den Import mit bestätigtem Mapping aus."""
        batch_id = request.session.get("kataster_import_batch_id")
        rows = request.session.get("kataster_import_rows")

        if not batch_id or not rows:
            messages.error(request, "Import-Session abgelaufen. Bitte erneut hochladen.")
            return redirect("kataster:import")

        from .models import ImportBatch

        batch = get_object_or_404(ImportBatch, pk=batch_id, tenant_id=tenant_id)

        column_mapping = {}
        for key in request.POST:
            if key.startswith("map_"):
                field_name = key[4:]
                excel_col = request.POST[key]
                if excel_col:
                    column_mapping[field_name] = excel_col

        service = KatasterImportService(tenant_id=tenant_id, user_id=user_id)
        stats = service.process_batch(batch, rows, column_mapping)

        # Clean session
        del request.session["kataster_import_batch_id"]
        del request.session["kataster_import_rows"]

        if stats.errors:
            messages.warning(
                request,
                f"Import teilweise: {stats.created} neu, {stats.updated} aktualisiert, "
                f"{len(stats.errors)} Fehler.",
            )
        else:
            messages.success(
                request,
                f"Import erfolgreich: {stats.created} neu, {stats.updated} aktualisiert, "
                f"{stats.skipped} übersprungen.",
            )

        return render(
            request,
            "substances/kataster/import_result.html",
            {
                "batch": batch,
                "stats": stats,
            },
        )


class ImportBatchListView(LoginRequiredMixin, View):
    """Liste aller Import-Batches."""

    template_name = "substances/kataster/import_list.html"

    def get(self, request):
        tenant_id = _tenant_id(request)
        from .models import ImportBatch

        batches = (
            ImportBatch.objects.filter(tenant_id=tenant_id)
            .select_related("target_site")
            .order_by("-created_at")
        )
        return render(request, self.template_name, {"batches": batches})
