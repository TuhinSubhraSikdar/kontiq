from django.urls import path

from . import views

app_name = "scheduler"
urlpatterns = [
    path("", views.scheduler_index, name="index"),
    path("dispatch/", views.dispatch_now, name="dispatch"),
    path("projects/<int:project_pk>/", views.scheduler_configure, name="configure"),
]
