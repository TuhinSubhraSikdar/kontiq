from django.urls import path

from . import views

app_name = "library"
urlpatterns = [
    path("", views.library_list, name="list"),
    path("<int:pk>/", views.content_detail, name="detail"),
    path("<int:pk>/edit/", views.content_edit, name="edit"),
    path("<int:pk>/versions/<int:version_pk>/restore/", views.version_restore, name="version_restore"),
    path("<int:pk>/download/html/", views.html_download, name="html_download"),
    path("<int:pk>/download/docx/", views.docx_download, name="docx_download"),
]
