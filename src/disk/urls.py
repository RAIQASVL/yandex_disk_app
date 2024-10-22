from django.contrib import admin
from django.urls import path, include
from . import views

app_name = "disk"

urlpatterns = [
    path("file-list/", views.FileListView.as_view(), name="file_list"),
]
