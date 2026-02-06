from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("apps.accounts.urls")),  # ak už používaš accounts app

    path("", include("core.urls")),
    path("competitions/", include("apps.competitions.urls")),
    path("catches/", include("apps.catches.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("friends/", include("apps.friends.urls")),
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("favicon/favicon.ico"), permanent=True),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
