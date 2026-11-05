from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity_logs.services import record_activity
from apps.ai_engine.services import queue_generation

from .forms import BulkTaskForm, CSVTaskUploadForm, ContentTaskForm, TaskRowUpdateForm
from .models import ContentTask
from .services import create_tasks_from_csv, queue_selected_tasks, update_task_row


def _task_for(user, pk):
    return get_object_or_404(ContentTask.objects.select_related("project", "content_type"), pk=pk, project__owner=user)


@login_required
def task_list(request):
    tasks = ContentTask.objects.filter(project__owner=request.user).select_related(
        "project", "content_type", "generated_content"
    )
    status = request.GET.get("status", "")
    project = request.GET.get("project", "")
    query = request.GET.get("q", "").strip()
    if status:
        tasks = tasks.filter(status=status)
    if project:
        tasks = tasks.filter(project_id=project)
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(primary_keyword__icontains=query))
    return render(request, "tasks/list.html", {
        "tasks": tasks, "statuses": ContentTask.Status.choices,
        "projects": request.user.kontiq_projects.all(), "selected_status": status, "selected_project": project, "query": query,
        "content_types": request.user.kontiq_content_types.filter(is_active=True),
    })


@login_required
def task_create(request):
    form = ContentTaskForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.status = ContentTask.Status.SCHEDULED if task.scheduled_for else ContentTask.Status.DRAFT
        task.save()
        record_activity(
            user=request.user,
            project=task.project,
            task=task,
            event_type="task.created",
            summary=f"Created task {task.display_title}",
        )
        messages.success(request, "Content task created.")
        return redirect("tasks:detail", pk=task.pk)
    return render(request, "tasks/form.html", {"form": form, "heading": "New content task"})


@login_required
def task_bulk_create(request):
    form = BulkTaskForm(request.POST or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            created = []
            for row in form.cleaned_data["titles"]:
                parts = [part.strip() for part in row.split("|", 1)]
                title = parts[0]
                keyword = parts[1] if len(parts) > 1 and parts[1] else title
                created.append(ContentTask(
                    project=form.cleaned_data["project"], content_type=form.cleaned_data["content_type"],
                    title=title, primary_keyword=keyword, target_word_count=form.cleaned_data["target_word_count"],
                ))
            ContentTask.objects.bulk_create(created)
        messages.success(request, f"Created {len(created)} content tasks.")
        return redirect("tasks:list")
    return render(request, "tasks/form.html", {"form": form, "heading": "Bulk-create tasks"})


@login_required
def task_csv_import(request):
    form = CSVTaskUploadForm(request.POST or None, request.FILES or None, owner=request.user)
    if request.method == "POST" and form.is_valid():
        created = create_tasks_from_csv(
            owner=request.user,
            project=form.cleaned_data["project"],
            rows=form.parsed_rows,
        )
        messages.success(request, f"Imported {len(created)} content rows. Review them, then select Proceed.")
        return redirect("tasks:list")
    return render(request, "tasks/csv_import.html", {"form": form})


@login_required
def task_quick_update(request, pk):
    task = _task_for(request.user, pk)
    if request.method != "POST":
        return redirect("tasks:list")
    form = TaskRowUpdateForm(request.POST, instance=task, owner=request.user)
    if not form.is_valid():
        error = next(iter(form.errors.values()))[0]
        messages.error(request, f"{task.display_title}: {error}")
        return redirect("tasks:list")
    try:
        update_task_row(task=task, form=form)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Updated "{task.display_title}".')
    return redirect("tasks:list")


@login_required
def task_proceed_selected(request):
    if request.method != "POST":
        return redirect("tasks:list")
    try:
        result = queue_selected_tasks(owner=request.user, task_ids=request.POST.getlist("task_ids"))
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("tasks:list")

    if result.queued:
        messages.success(request, f"Queued {result.queued} selected content row(s) for generation.")
    if result.already_active:
        messages.info(request, f"{result.already_active} selected row(s) were already in progress.")
    if result.unavailable:
        messages.warning(request, "Some selected rows were unavailable and were not queued.")
    for error in result.errors:
        messages.error(request, error)
    return redirect("tasks:list")


@login_required
def task_detail(request, pk):
    return render(request, "tasks/detail.html", {"task": _task_for(request.user, pk)})


@login_required
def task_edit(request, pk):
    task = _task_for(request.user, pk)
    if task.status in {ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING}:
        messages.error(request, "A queued or processing task cannot be edited.")
        return redirect("tasks:detail", pk=task.pk)
    form = ContentTaskForm(request.POST or None, instance=task, owner=request.user)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        if task.status != ContentTask.Status.COMPLETED:
            task.status = ContentTask.Status.SCHEDULED if task.scheduled_for else ContentTask.Status.DRAFT
        task.save()
        messages.success(request, "Task updated.")
        return redirect("tasks:detail", pk=task.pk)
    return render(request, "tasks/form.html", {"form": form, "heading": f"Edit {task.display_title}"})


@login_required
def task_generate(request, pk):
    task = _task_for(request.user, pk)
    if request.method == "POST":
        try:
            _, created = queue_generation(task.pk, request.user)
        except (ValueError, RuntimeError) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Generation queued." if created else "Generation is already in progress.")
    return redirect("tasks:detail", pk=task.pk)


@login_required
def task_delete(request, pk):
    task = _task_for(request.user, pk)
    if task.status in {ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING}:
        messages.error(request, "A queued or processing task cannot be deleted.")
        return redirect("tasks:detail", pk=task.pk)
    if request.method == "POST":
        document = ""
        storage = None
        if hasattr(task, "generated_content") and task.generated_content.document:
            document = task.generated_content.document.name
            storage = task.generated_content.document.storage
        with transaction.atomic():
            task.delete()
            if document:
                transaction.on_commit(lambda: storage.delete(document))
        messages.success(request, "Task, generated content, versions, and stored document were deleted.")
        return redirect("tasks:list")
    return render(request, "tasks/confirm_delete.html", {"task": task})
