from django.urls import path
from .views import home, dashboard

app_name = "pages"

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
]
