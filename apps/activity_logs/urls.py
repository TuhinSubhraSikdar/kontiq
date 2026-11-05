from django.urls import path

from .views import activity_list

app_name = "activity_logs"
urlpatterns = [path("", activity_list, name="list")]
