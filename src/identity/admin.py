from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from identity.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("username", "email", "tenant_id", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "tenant_id")
