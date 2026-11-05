from django.urls import path

from .views import provider_settings

app_name = "ai_engine"
urlpatterns = [path("", provider_settings, name="settings")]
