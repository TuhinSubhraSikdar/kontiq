from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity_logs.services import record_activity

from .forms import ProjectForm, ProjectLinkForm, ProjectReferenceForm
from .models import Project, ProjectLink, ProjectReference
from .services import create_reference, delete_project_with_files, delete_reference_with_file


def _project_for(user, pk):
    return get_object_or_404(Project, pk=pk, owner=user)


@login_required
def project_list(request):
    return render(request, "projects/list.html", {"projects": Project.objects.filter(owner=request.user)})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        record_activity(user=request.user, project=project, event_type="project.created", summary=f"Created project {project.name}")
        messages.success(request, "Project created.")
        return redirect("projects:detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "heading": "Create project"})


@login_required
def project_detail(request, pk):
    project = _project_for(request.user, pk)
    return render(request, "projects/detail.html", {
        "project": project,
        "link_form": ProjectLinkForm(),
        "reference_form": ProjectReferenceForm(project=project),
    })


@login_required
def project_edit(request, pk):
    project = _project_for(request.user, pk)
    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        record_activity(user=request.user, project=project, event_type="project.updated", summary=f"Updated project {project.name}")
        messages.success(request, "Project updated.")
        return redirect("projects:detail", pk=project.pk)
    return render(request, "projects/form.html", {"form": form, "heading": f"Edit {project.name}", "project": project})


@login_required
def project_delete(request, pk):
    project = _project_for(request.user, pk)
    if request.method == "POST":
        name = project.name
        delete_project_with_files(project=project)
        messages.success(request, f"Deleted {name} and its related local artifacts.")
        return redirect("projects:list")
    return render(request, "projects/confirm_delete.html", {"project": project})


@login_required
def link_add(request, pk):
    project = _project_for(request.user, pk)
    form = ProjectLinkForm(request.POST)
    if form.is_valid():
        link = form.save(commit=False)
        link.project = project
        link.save()
        messages.success(request, "Link added.")
    else:
        messages.error(request, "The link could not be added. Check the fields and try again.")
    return redirect("projects:detail", pk=project.pk)


@login_required
def link_delete(request, pk, link_pk):
    project = _project_for(request.user, pk)
    link = get_object_or_404(ProjectLink, pk=link_pk, project=project)
    if request.method == "POST":
        link.delete()
        messages.success(request, "Link removed.")
    return redirect("projects:detail", pk=project.pk)


@login_required
def reference_add(request, pk):
    project = _project_for(request.user, pk)
    form = ProjectReferenceForm(request.POST, request.FILES, project=project)
    if form.is_valid():
        reference = create_reference(project=project, upload=form.cleaned_data["file"], user=request.user)
        if reference.extraction_status == ProjectReference.ExtractionStatus.READY:
            messages.success(request, "Reference uploaded and text extracted.")
        else:
            messages.warning(request, f"Reference stored, but extraction failed: {reference.extraction_error}")
    else:
        messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
    return redirect("projects:detail", pk=project.pk)


@login_required
def reference_download(request, pk, reference_pk):
    project = _project_for(request.user, pk)
    reference = get_object_or_404(ProjectReference, pk=reference_pk, project=project)
    return FileResponse(reference.file.open("rb"), as_attachment=True, filename=reference.original_name)


@login_required
def reference_delete(request, pk, reference_pk):
    project = _project_for(request.user, pk)
    reference = get_object_or_404(ProjectReference, pk=reference_pk, project=project)
    if request.method == "POST":
        delete_reference_with_file(reference=reference)
        messages.success(request, "Reference and its stored file were deleted.")
    return redirect("projects:detail", pk=project.pk)
