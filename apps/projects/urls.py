from django.urls import path

from . import views

app_name = "projects"
urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_edit, name="edit"),
    path("<int:pk>/delete/", views.project_delete, name="delete"),
    path("<int:pk>/links/add/", views.link_add, name="link_add"),
    path("<int:pk>/links/<int:link_pk>/delete/", views.link_delete, name="link_delete"),
    path("<int:pk>/references/add/", views.reference_add, name="reference_add"),
    path("<int:pk>/references/<int:reference_pk>/download/", views.reference_download, name="reference_download"),
    path("<int:pk>/references/<int:reference_pk>/delete/", views.reference_delete, name="reference_delete"),
]
