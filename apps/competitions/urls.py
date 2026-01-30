from django.urls import path
from . import views

app_name = "competitions"

urlpatterns = [
    path("my/", views.my_competitions, name="my_competitions"),
    path("<int:pk>/", views.competition_detail, name="detail"),
]
