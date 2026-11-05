from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity_logs.services import record_activity

from .forms import GeneratedContentForm
from .models import GeneratedContent, GeneratedContentVersion
from .services import render_docx, render_html_document, update_content


def _content_for(user, pk):
    return get_object_or_404(
        GeneratedContent.objects.select_related("project", "content_type", "task"),
        pk=pk,
        project__owner=user,
    )


@login_required
def library_list(request):
    contents = GeneratedContent.objects.filter(project__owner=request.user).select_related("project", "content_type")
    project_id = request.GET.get("project", "")
    if project_id:
        contents = contents.filter(project_id=project_id)
    return render(request, "library/list.html", {
        "contents": contents,
        "projects": request.user.kontiq_projects.all(),
        "selected_project": project_id,
    })


@login_required
def content_detail(request, pk):
    content = _content_for(request.user, pk)
    return render(request, "library/detail.html", {"content_item": content, "versions": content.versions.all()})


@login_required
def content_edit(request, pk):
    content = _content_for(request.user, pk)
    form = GeneratedContentForm(request.POST or None, instance=content)
    if request.method == "POST" and form.is_valid():
        content = update_content(content=content, cleaned_data=form.cleaned_data.copy(), user=request.user)
        messages.success(request, "Content updated and the previous version was preserved.")
        return redirect("library:detail", pk=content.pk)
    return render(request, "library/form.html", {"form": form, "content_item": content})


@login_required
def version_restore(request, pk, version_pk):
    content = _content_for(request.user, pk)
    version = get_object_or_404(GeneratedContentVersion, pk=version_pk, content=content)
    if request.method == "POST":
        data = {
            "title": version.title,
            "slug": content.slug,
            "meta_description": version.meta_description,
            "body": version.body,
            "change_note": f"Snapshot before restoring version {version.version}",
        }
        update_content(content=content, cleaned_data=data, user=request.user)
        messages.success(request, f"Version {version.version} restored.")
    return redirect("library:detail", pk=content.pk)


@login_required
def html_download(request, pk):
    content = _content_for(request.user, pk)
    response = HttpResponse(render_html_document(content), content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{content.slug}.html"'
    return response


@login_required
def docx_download(request, pk):
    content = _content_for(request.user, pk)
    document = content.document if content.document else render_docx(content)
    return FileResponse(
        document.open("rb"),
        as_attachment=True,
        filename=f"{content.slug}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
