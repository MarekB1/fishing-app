from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("pending/", views.pending, name="pending"),
    path("pending/list/", views.pending_list, name="pending_list"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("mark-read/<int:notification_id>/", views.mark_read, name="mark_read"),
    path("go/<int:notification_id>/", views.notification_redirect, name="notification_redirect"),
]
