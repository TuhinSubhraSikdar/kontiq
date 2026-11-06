from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.content_types.forms import ContentTypeForm
from apps.content_types.models import ContentType

from .forms import PromptTemplateForm, SUPPORTED_VARIABLES
from .models import DEFAULT_PROMPT, PromptTemplate, PromptVersion
from .services import render_prompt, restore_prompt_version, update_prompt


@login_required
def prompt_list(request):
    content_types = ContentType.objects.filter(owner=request.user).annotate(
        prompt_count=Count("prompt_templates")
    )
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    favorites = request.GET.get("favorites", "")
    if query:
        content_types = content_types.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category:
        content_types = content_types.filter(category=category)
    if status in {"active", "inactive"}:
        content_types = content_types.filter(is_active=status == "active")
    if favorites:
        content_types = content_types.filter(is_favorite=True)
    return render(request, "prompts/list.html", {
        "page_title": "Content Types",
        "content_types": content_types,
        "categories": ContentType.Category.choices,
        "query": query,
        "selected_category": category,
        "selected_status": status,
        "favorites_only": bool(favorites),
        "view_mode": request.GET.get("view", "grid"),
    })


@login_required
def content_type_workspace(request, pk):
    content_type = get_object_or_404(
        ContentType.objects.annotate(prompt_count=Count("prompt_templates")),
        pk=pk,
        owner=request.user,
    )
    prompts = content_type.prompt_templates.filter(owner=request.user).select_related("project")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "updated")
    if query:
        prompts = prompts.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(template__icontains=query)
        )
    if category:
        prompts = prompts.filter(category=category)
    prompts = prompts.order_by("title" if sort == "title" else "-updated_at")
    return render(request, "prompts/workspace.html", {
        "page_title": content_type.name,
        "content_type": content_type,
        "prompts": prompts,
        "categories": PromptTemplate.Category.choices,
        "query": query,
        "selected_category": category,
        "selected_sort": sort,
    })


@login_required
def prompt_library(request):
    prompts = PromptTemplate.objects.filter(owner=request.user).select_related("content_type", "project")
    query = request.GET.get("q", "").strip()
    content_type_id = request.GET.get("content_type", "")
    category = request.GET.get("category", "")
    scope = request.GET.get("scope", "")
    favorites = request.GET.get("favorites", "")
    sort = request.GET.get("sort", "updated")
    if query:
        prompts = prompts.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(template__icontains=query)
        )
    if content_type_id:
        prompts = prompts.filter(content_type_id=content_type_id)
    if category:
        prompts = prompts.filter(category=category)
    if scope == "templates":
        prompts = prompts.filter(project__isnull=True)
    elif scope == "overrides":
        prompts = prompts.filter(project__isnull=False)
    if favorites:
        prompts = prompts.filter(is_favorite=True)
    prompts = prompts.order_by("title", "content_type__name") if sort == "title" else prompts.order_by("-updated_at")
    return render(request, "prompts/library.html", {
        "page_title": "Prompt Library",
        "prompts": prompts,
        "content_types": request.user.kontiq_content_types.all(),
        "categories": PromptTemplate.Category.choices,
        "query": query,
        "selected_content_type": content_type_id,
        "selected_category": category,
        "selected_scope": scope,
        "favorites_only": bool(favorites),
        "selected_sort": sort,
    })


@login_required
def content_type_create(request):
    duplicate_id = request.GET.get("duplicate")
    source = None
    initial = {}
    if duplicate_id:
        source = get_object_or_404(ContentType, pk=duplicate_id, owner=request.user)
        initial = {
            "name": f"{source.name} copy",
            "description": source.description,
            "category": source.category,
            "icon": source.icon,
            "color": source.color,
            "default_word_count": source.default_word_count,
            "requirements": source.requirements,
            "custom_fields_input": "\n".join(source.custom_fields or []),
            "is_active": source.is_active,
        }
    form = ContentTypeForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        content_type = form.save(commit=False)
        content_type.owner = request.user
        content_type.save()
        copied_prompts = 0
        if source:
            for prompt in source.prompt_templates.filter(owner=request.user):
                PromptTemplate.objects.create(
                    owner=request.user,
                    content_type=content_type,
                    project=prompt.project,
                    title=prompt.title,
                    description=prompt.description,
                    category=prompt.category,
                    template=prompt.template,
                    is_active=prompt.is_active,
                )
                copied_prompts += 1
        if not copied_prompts:
            PromptTemplate.objects.create(
                owner=request.user,
                content_type=content_type,
                title=f"{content_type.name} default prompt",
                description=f"Core generation instructions for {content_type.name.lower()} content.",
                template=DEFAULT_PROMPT,
            )
        messages.success(request, "Content type and prompt workspace created.")
        return redirect("prompts:content_type_workspace", pk=content_type.pk)
    return render(request, "prompts/content_type_form.html", {
        "form": form,
        "heading": f"Duplicate {source.name}" if source else "Create content type",
        "page_title": "Duplicate content type" if source else "Create content type",
    })


@login_required
def content_type_edit(request, pk):
    content_type = get_object_or_404(ContentType, pk=pk, owner=request.user)
    form = ContentTypeForm(request.POST or None, instance=content_type)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Content type updated.")
        return redirect("prompts:content_type_workspace", pk=content_type.pk)
    return render(request, "prompts/content_type_form.html", {
        "form": form, "heading": f"Edit {content_type.name}", "page_title": "Edit content type",
        "content_type": content_type,
    })


@login_required
def content_type_delete(request, pk):
    content_type = get_object_or_404(ContentType, pk=pk, owner=request.user)
    if request.method == "POST":
        try:
            content_type.delete()
        except ProtectedError:
            messages.error(request, "This content type is used by tasks or generated content and cannot be deleted.")
            return redirect("prompts:content_type_edit", pk=content_type.pk)
        messages.success(request, "Content type and its prompt templates were deleted.")
        return redirect("prompts:list")
    return render(request, "prompts/confirm_delete.html", {"object": content_type, "kind": "content type", "cancel_url": "prompts:content_type_edit"})


@login_required
def prompt_create(request):
    initial = {}
    content_type_id = request.GET.get("content_type")
    duplicate_id = request.GET.get("duplicate")
    if content_type_id:
        initial["content_type"] = get_object_or_404(ContentType, pk=content_type_id, owner=request.user)
    if duplicate_id:
        source = get_object_or_404(PromptTemplate, pk=duplicate_id, owner=request.user)
        initial.update({
            "title": f"{source.display_title} copy",
            "description": source.description,
            "content_type": source.content_type,
            "category": source.category,
            "template": source.template,
            "is_active": source.is_active,
        })
    form = PromptTemplateForm(request.POST or None, owner=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        prompt = form.save(commit=False)
        prompt.owner = request.user
        try:
            with transaction.atomic():
                prompt.save()
        except IntegrityError:
            form.add_error(None, "A prompt already exists for this content type and scope.")
        else:
            messages.success(request, "Prompt created.")
            return redirect("prompts:edit", pk=prompt.pk)
    return render(request, "prompts/form.html", {
        "form": form, "heading": "Create prompt", "variables": sorted(SUPPORTED_VARIABLES),
        "page_title": "Prompt Editor", "duplicating": bool(duplicate_id),
    })


@login_required
def prompt_edit(request, pk):
    prompt = get_object_or_404(PromptTemplate, pk=pk, owner=request.user)
    form = PromptTemplateForm(request.POST or None, instance=prompt, owner=request.user)
    preview = ""
    if request.method == "POST" and form.is_valid():
        if "preview" in request.POST:
            sample = {name: f"[{name.replace('_', ' ')}]" for name in SUPPORTED_VARIABLES}
            preview = render_prompt(form.cleaned_data["template"], sample)
        else:
            prompt = update_prompt(prompt=prompt, cleaned_data=form.cleaned_data, user=request.user)
            messages.success(request, "Prompt updated.")
            return redirect("prompts:edit", pk=prompt.pk)
    return render(request, "prompts/form.html", {
        "form": form, "heading": prompt.display_title, "variables": sorted(SUPPORTED_VARIABLES),
        "preview": preview, "prompt": prompt, "versions": prompt.versions.all()[:20],
        "page_title": "Prompt Editor",
    })


@login_required
@require_POST
def prompt_version_restore(request, pk, version_pk):
    prompt = get_object_or_404(PromptTemplate, pk=pk, owner=request.user)
    version = get_object_or_404(PromptVersion, pk=version_pk, prompt=prompt)
    restore_prompt_version(prompt=prompt, version=version, user=request.user)
    messages.success(request, f"Version {version.version} restored as a new version.")
    return redirect("prompts:edit", pk=prompt.pk)


@login_required
@require_POST
def content_type_favorite(request, pk):
    content_type = get_object_or_404(ContentType, pk=pk, owner=request.user)
    content_type.is_favorite = not content_type.is_favorite
    content_type.save(update_fields=["is_favorite", "updated_at"])
    return redirect("prompts:content_type_workspace", pk=content_type.pk)


@login_required
@require_POST
def prompt_favorite(request, pk):
    prompt = get_object_or_404(PromptTemplate, pk=pk, owner=request.user)
    prompt.is_favorite = not prompt.is_favorite
    prompt.save(update_fields=["is_favorite", "updated_at"])
    return redirect("prompts:content_type_workspace", pk=prompt.content_type_id)


@login_required
def prompt_delete(request, pk):
    prompt = get_object_or_404(PromptTemplate, pk=pk, owner=request.user)
    if request.method == "POST":
        prompt.delete()
        messages.success(request, "Prompt template deleted.")
        return redirect("prompts:list")
    return render(request, "prompts/confirm_delete.html", {"object": prompt, "kind": "prompt template", "cancel_url": "prompts:edit"})
