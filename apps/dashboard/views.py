from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .services import get_dashboard_snapshot


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        display_name = self.request.user.get_short_name() or self.request.user.get_username()
        context.update(
            {
                "page_title": "Dashboard",
                "page_heading": f"Welcome back, {display_name}",
                "page_description": (
                    "Manage projects, queue generation, and keep every output versioned locally."
                ),
                "dashboard": get_dashboard_snapshot(self.request.user),
            }
        )
        return context
