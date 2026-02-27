from django.contrib import admin

from documents.models import Document, DocumentVersion


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "tenant_id", "created_at")
    list_filter = ("category",)
    search_fields = ("title",)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version", "filename", "size_bytes", "uploaded_at")
    list_filter = ("content_type",)
