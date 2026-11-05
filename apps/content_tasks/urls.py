from django.urls import path

from . import views

app_name = "tasks"
urlpatterns = [
    path("", views.task_list, name="list"),
    path("new/", views.task_create, name="create"),
    path("bulk/", views.task_bulk_create, name="bulk_create"),
    path("import/csv/", views.task_csv_import, name="csv_import"),
    path("proceed/", views.task_proceed_selected, name="proceed_selected"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/row/", views.task_quick_update, name="quick_update"),
    path("<int:pk>/edit/", views.task_edit, name="edit"),
    path("<int:pk>/generate/", views.task_generate, name="generate"),
    path("<int:pk>/delete/", views.task_delete, name="delete"),
]
