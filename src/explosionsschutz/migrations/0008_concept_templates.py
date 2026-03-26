# Generated manually for ADR-147 concept-templates integration

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("explosionsschutz", "0007_area_dxf_svg"),
    ]

    operations = [
        # ── ExConceptDocument ──────────────────────────────────
        migrations.CreateModel(
            name="ExConceptDocument",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("title", models.CharField(max_length=240)),
                ("scope", models.CharField(blank=True, default="explosionsschutz", max_length=30)),
                ("source_filename", models.CharField(blank=True, default="", max_length=255)),
                ("content_type", models.CharField(blank=True, default="", max_length=120)),
                ("extracted_text", models.TextField(blank=True, default="")),
                ("extraction_warnings", models.TextField(blank=True, default="", help_text="JSON-Liste von Warnungen aus der Extraktion")),
                ("page_count", models.IntegerField(blank=True, null=True)),
                ("template_json", models.TextField(blank=True, default="", help_text="Serialisiertes ConceptTemplate nach LLM-Analyse")),
                ("analysis_confidence", models.FloatField(blank=True, help_text="0.0-1.0, Konfidenz der LLM-Strukturanalyse", null=True)),
                ("status", models.CharField(choices=[("uploaded", "Hochgeladen"), ("extracting", "Wird extrahiert"), ("extracted", "Text extrahiert"), ("analyzing", "Wird analysiert"), ("analyzed", "Analysiert"), ("failed", "Fehlgeschlagen")], db_index=True, default="uploaded", max_length=20)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concept_documents", to="explosionsschutz.explosionconcept")),
            ],
            options={
                "verbose_name": "Ex-Konzept-Unterlage",
                "verbose_name_plural": "Ex-Konzept-Unterlagen",
                "db_table": "ex_concept_document",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="exconceptdocument",
            index=models.Index(fields=["tenant_id", "status"], name="ix_ex_cdoc_tenant_status"),
        ),
        # ── ExConceptTemplateStore ─────────────────────────────
        migrations.CreateModel(
            name="ExConceptTemplateStore",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("name", models.CharField(max_length=200)),
                ("scope", models.CharField(default="explosionsschutz", max_length=30)),
                ("version", models.CharField(default="1.0", max_length=20)),
                ("is_master", models.BooleanField(default=False)),
                ("framework", models.CharField(blank=True, default="", max_length=100)),
                ("source", models.CharField(choices=[("analyzed", "Aus Dokumentanalyse"), ("builtin", "Framework-Vorlage"), ("merged", "Zusammengeführt"), ("manual", "Manuell erstellt")], default="analyzed", max_length=20)),
                ("template_json", models.TextField(help_text="Serialisiertes ConceptTemplate (Pydantic JSON)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source_document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_templates", to="explosionsschutz.exconceptdocument")),
            ],
            options={
                "verbose_name": "Ex-Konzept-Template",
                "verbose_name_plural": "Ex-Konzept-Templates",
                "db_table": "ex_concept_template_store",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="exconcepttemplatestore",
            index=models.Index(fields=["tenant_id", "scope"], name="ix_ex_ctmpl_tenant_scope"),
        ),
        # ── ExFilledTemplate ───────────────────────────────────
        migrations.CreateModel(
            name="ExFilledTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("name", models.CharField(max_length=240)),
                ("values_json", models.TextField(default="{}", help_text="JSON: {section_name: {field_name: value}}")),
                ("status", models.CharField(choices=[("draft", "Entwurf"), ("review", "In Prüfung"), ("approved", "Freigegeben"), ("exported", "Exportiert")], db_index=True, default="draft", max_length=20)),
                ("generated_pdf_key", models.CharField(blank=True, default="", help_text="S3-Pfad des generierten PDFs", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("concept", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="filled_templates", to="explosionsschutz.explosionconcept")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="filled_instances", to="explosionsschutz.exconcepttemplatestore")),
            ],
            options={
                "verbose_name": "Ausgefülltes Ex-Template",
                "verbose_name_plural": "Ausgefüllte Ex-Templates",
                "db_table": "ex_filled_template",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="exfilledtemplate",
            index=models.Index(fields=["tenant_id", "status"], name="ix_ex_ftmpl_tenant_status"),
        ),
    ]
