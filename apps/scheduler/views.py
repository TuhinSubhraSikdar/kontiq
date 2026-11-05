from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.content_tasks.models import ContentTask
from apps.projects.models import Project

from .forms import ScheduleConfigurationForm
from .models import ScheduleConfiguration
from .services import dispatch_due_tasks


@login_required
def scheduler_index(request):
    projects = Project.objects.filter(owner=request.user)
    configurations = []
    for project in projects:
        config, _ = ScheduleConfiguration.objects.get_or_create(project=project)
        configurations.append(config)
    queue = ContentTask.objects.filter(
        project__owner=request.user,
        status__in=[ContentTask.Status.SCHEDULED, ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING, ContentTask.Status.FAILED],
    ).select_related("project")[:50]
    return render(request, "scheduler/index.html", {"configurations": configurations, "queue": queue})


@login_required
def scheduler_configure(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    config, _ = ScheduleConfiguration.objects.get_or_create(project=project)
    form = ScheduleConfigurationForm(request.POST or None, instance=config)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Automation settings updated for {project.name}.")
        return redirect("scheduler:index")
    return render(request, "scheduler/form.html", {"form": form, "project": project})


@login_required
def dispatch_now(request):
    if request.method == "POST":
        count = dispatch_due_tasks(owner=request.user)
        messages.success(request, f"Queued {count} due task{'s' if count != 1 else ''}.")
    return redirect("scheduler:index")
