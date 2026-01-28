from django.contrib import admin
from actions.models import ActionItem


@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "due_date", "tenant_id")
    list_filter = ("status", "priority")
    search_fields = ("title", "description")
