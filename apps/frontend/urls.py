"""
Frontend URL configuration.
"""

from django.urls import path
from . import views

app_name = "frontend"

urlpatterns = [
    path("", views.home, name="home"),
    path("scan/", views.scan, name="scan"),
    path("scan/<int:scan_id>/", views.scan_detail, name="scan_detail"),
    path("history/", views.history, name="history"),
]
