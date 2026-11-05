from django import forms
from django.core.exceptions import ImproperlyConfigured

from .crypto import encrypt_credential
from .models import AIProviderConfiguration


class AIProviderConfigurationAdminForm(forms.ModelForm):
    make_active = forms.BooleanField(
        label="Use this configuration for generation",
        required=False,
        help_text="Selecting this replaces the currently active provider configuration.",
    )
    api_key = forms.CharField(
        label="API key",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text=(
            "The key is encrypted before storage and is never displayed again. "
            "Leave blank while editing to keep the saved key."
        ),
    )

    class Meta:
        model = AIProviderConfiguration
        fields = [
            "name",
            "provider",
            "model_name",
            "api_base_url",
            "api_key",
            "make_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["make_active"].initial = hasattr(self.instance, "active_selection")

    def clean_api_key(self):
        value = self.cleaned_data.get("api_key", "").strip()
        if not value and not self.instance.encrypted_api_key:
            raise forms.ValidationError("Enter an API key for this configuration.")
        if value:
            # Validate the external encryption key before the admin form can save a secret.
            try:
                encrypt_credential(value)
            except ImproperlyConfigured as exc:
                raise forms.ValidationError(str(exc)) from exc
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        api_key = self.cleaned_data.get("api_key")
        if api_key:
            instance.set_api_key(api_key)
        if commit:
            instance.save()
            self.save_m2m()
        return instance
