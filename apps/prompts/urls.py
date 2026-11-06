from django.urls import path

from . import views

app_name = "prompts"
urlpatterns = [
    path("", views.prompt_list, name="list"),
    path("library/", views.prompt_library, name="library"),
    path("content-types/new/", views.content_type_create, name="content_type_create"),
    path("content-types/<int:pk>/", views.content_type_workspace, name="content_type_workspace"),
    path("content-types/<int:pk>/edit/", views.content_type_edit, name="content_type_edit"),
    path("content-types/<int:pk>/favorite/", views.content_type_favorite, name="content_type_favorite"),
    path("content-types/<int:pk>/delete/", views.content_type_delete, name="content_type_delete"),
    path("new/", views.prompt_create, name="create"),
    path("<int:pk>/edit/", views.prompt_edit, name="edit"),
    path("<int:pk>/favorite/", views.prompt_favorite, name="favorite"),
    path("<int:pk>/versions/<int:version_pk>/restore/", views.prompt_version_restore, name="version_restore"),
    path("<int:pk>/delete/", views.prompt_delete, name="delete"),
]
