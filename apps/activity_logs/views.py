from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import ActivityLog


@login_required
def activity_list(request):
    logs = ActivityLog.objects.filter(user=request.user).select_related("project", "task")
    query = request.GET.get("q", "").strip()
    if query:
        logs = logs.filter(Q(summary__icontains=query) | Q(event_type__icontains=query))
    return render(request, "activity_logs/list.html", {"logs": logs[:200], "query": query})
