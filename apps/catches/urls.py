from django.urls import path
from . import views

app_name = "catches"

urlpatterns = [
    path("new/", views.catch_create, name="catch_create"),
]
