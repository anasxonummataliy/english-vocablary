from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Channel, User


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tg_id",
        "channel_title",
        "channel_username",
        "is_active",
    )

    list_filter = ("is_active",)

    search_fields = (
        "channel_title",
        "channel_username",
        "channel_link",
        "tg_id",
    )

    ordering = ("-id",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tg_id",
        "first_name",
        "last_name",
        "username",
        "is_blocked",
        "last_activity",
    )

    list_filter = ("is_blocked",)

    search_fields = (
        "first_name",
        "last_name",
        "username",
        "tg_id",
    )

    ordering = ("-id",)

    readonly_fields = ("last_activity",)
