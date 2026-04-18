from django.contrib import admin

from training.models import TrainingAttendance, TrainingSession, TrainingTopic


class TrainingAttendanceInline(admin.TabularInline):
    model = TrainingAttendance
    extra = 0


@admin.register(TrainingTopic)
class TrainingTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "interval", "site", "department", "is_active")
    list_filter = ("interval", "is_active")
    search_fields = ("title",)


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ("topic", "session_date", "status")
    list_filter = ("status", "session_date")
    inlines = [TrainingAttendanceInline]


@admin.register(TrainingAttendance)
class TrainingAttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "user_id", "status", "signed_at")
    list_filter = ("status",)
