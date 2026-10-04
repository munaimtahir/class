from django.contrib import admin
from django.contrib.staticfiles.views import serve
from django.urls import include, path
from django.urls import re_path

urlpatterns = [
    # Django admin panel is at /django-admin/ so that /admin/* frontend routes
    # are served by Next.js without conflict.
    path("django-admin/", admin.site.urls),
    path("api/", include("core.urls")),
    # Serve static assets from the backend so the Django admin stays usable
    # in deployed DEBUG=False environments where no separate static server exists.
    re_path(r"^static/(?P<path>.*)$", serve, {"insecure": True}),
]
