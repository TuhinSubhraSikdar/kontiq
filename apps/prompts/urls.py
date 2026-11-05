from django.urls import path

from . import views

app_name = "prompts"
urlpatterns = [
    path("", views.prompt_list, name="list"),
    path("content-types/new/", views.content_type_create, name="content_type_create"),
    path("content-types/<int:pk>/edit/", views.content_type_edit, name="content_type_edit"),
    path("content-types/<int:pk>/delete/", views.content_type_delete, name="content_type_delete"),
    path("new/", views.prompt_create, name="create"),
    path("<int:pk>/edit/", views.prompt_edit, name="edit"),
    path("<int:pk>/delete/", views.prompt_delete, name="delete"),
]
