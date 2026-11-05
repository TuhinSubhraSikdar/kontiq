from django.urls import path

from . import views

app_name = "tasks"
urlpatterns = [
    path("", views.task_list, name="list"),
    path("new/", views.task_create, name="create"),
    path("bulk/", views.task_bulk_create, name="bulk_create"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/edit/", views.task_edit, name="edit"),
    path("<int:pk>/generate/", views.task_generate, name="generate"),
    path("<int:pk>/delete/", views.task_delete, name="delete"),
]
