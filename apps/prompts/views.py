from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from apps.content_types.forms import ContentTypeForm
from apps.content_types.models import ContentType

from .forms import PromptTemplateForm, SUPPORTED_VARIABLES
from .models import DEFAULT_PROMPT, PromptTemplate
from .services import render_prompt


@login_required
def prompt_list(request):
    return render(request, "prompts/list.html", {
        "content_types": ContentType.objects.filter(owner=request.user),
        "prompts": PromptTemplate.objects.filter(owner=request.user).select_related("content_type", "project"),
    })


@login_required
def content_type_create(request):
    form = ContentTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        content_type = form.save(commit=False)
        content_type.owner = request.user
        content_type.save()
        PromptTemplate.objects.create(owner=request.user, content_type=content_type, template=DEFAULT_PROMPT)
        messages.success(request, "Content type and default prompt created.")
        return redirect("prompts:list")
    return render(request, "prompts/content_type_form.html", {"form": form, "heading": "New content type"})


@login_required
def content_type_edit(request, pk):
    content_type = get_object_or_404(ContentType, pk=pk, owner=request.user)
    form = ContentTypeForm(request.POST or None, instance=content_type)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Content type updated.")
        return redirect("prompts:list")
    return render(request, "prompts/content_type_form.html", {"form": form, "heading": f"Edit {content_type.name}"})


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
    form = PromptTemplateForm(request.POST or None, owner=request.user)
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
    return render(request, "prompts/form.html", {"form": form, "heading": "New prompt", "variables": sorted(SUPPORTED_VARIABLES)})


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
            form.save()
            messages.success(request, "Prompt updated.")
            return redirect("prompts:edit", pk=prompt.pk)
    return render(request, "prompts/form.html", {
        "form": form, "heading": f"Edit {prompt}", "variables": sorted(SUPPORTED_VARIABLES), "preview": preview,
    })


@login_required
def prompt_delete(request, pk):
    prompt = get_object_or_404(PromptTemplate, pk=pk, owner=request.user)
    if request.method == "POST":
        prompt.delete()
        messages.success(request, "Prompt template deleted.")
        return redirect("prompts:list")
    return render(request, "prompts/confirm_delete.html", {"object": prompt, "kind": "prompt template", "cancel_url": "prompts:edit"})
