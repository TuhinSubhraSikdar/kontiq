from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    """Authenticated Phase 0 landing page.

    The database-driven dashboard is intentionally deferred to Phase 1.
    """

    template_name = "core/home.html"
