from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import provider_status


@login_required
def provider_settings(request):
    return render(request, "settings/ai.html", {"provider": provider_status()})
