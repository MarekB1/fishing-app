from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # login/logout (Django built-in auth)
    path("accounts/", include("django.contrib.auth.urls")),
    # stránky z core appky
    path("", include("core.urls")),
    path("competitions/", include("apps.competitions.urls")),
    path("catches/", include("apps.catches.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("favicon.ico", RedirectView.as_view(url=static("favicon/favicon.ico"))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
