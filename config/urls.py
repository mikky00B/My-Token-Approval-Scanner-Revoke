"""
Main URL configuration for wallet_scanner project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
    path("", include("apps.frontend.urls")),
]
