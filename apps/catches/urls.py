from django.urls import path
from . import views

app_name = "catches"

urlpatterns = [
    path("new/", views.catch_create, name="catch_create"),
    path("<int:pk>/", views.catch_detail, name="detail"),
    path("<int:pk>/approve/", views.catch_approve, name="approve"),
    path("<int:pk>/reject/", views.catch_reject, name="reject"),
    path("mine/", views.my_catches, name="my_catches"),
]
