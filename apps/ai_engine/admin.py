from django.contrib import admin, messages
from django.db import transaction

from .forms import AIProviderConfigurationAdminForm
from .models import AIProviderConfiguration, AIProviderSelection


@admin.register(AIProviderConfiguration)
class AIProviderConfigurationAdmin(admin.ModelAdmin):
    form = AIProviderConfigurationAdminForm
    list_display = (
        "name",
        "provider",
        "model_name",
        "api_key_hint",
        "is_active",
        "updated_at",
    )
    list_filter = ("provider",)
    search_fields = ("name", "model_name")
    readonly_fields = ("api_key_hint", "created_at", "updated_at")
    actions = ("activate_selected",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("active_selection")

    @admin.display(boolean=True, description="Active")
    def is_active(self, obj):
        return hasattr(obj, "active_selection")

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        selection, _ = AIProviderSelection.objects.select_for_update().get_or_create(
            singleton=1
        )
        if form.cleaned_data.get("make_active"):
            selection.configuration = obj
            selection.save(update_fields=["configuration", "updated_at"])
        elif selection.configuration_id == obj.pk:
            selection.configuration = None
            selection.save(update_fields=["configuration", "updated_at"])

    @admin.action(description="Activate the selected provider configuration")
    def activate_selected(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one provider configuration to activate.",
                level=messages.ERROR,
            )
            return
        configuration = queryset.get()
        with transaction.atomic():
            selection, _ = AIProviderSelection.objects.select_for_update().get_or_create(
                singleton=1
            )
            selection.configuration = configuration
            selection.save(update_fields=["configuration", "updated_at"])
        self.message_user(request, f"Activated {configuration.name}.")

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser
