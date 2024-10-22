from django.urls import path
from .views import FileListView, download_files

urlpatterns = [
    path("", FileListView.as_view(), name="file_list"),
    path(
        "download_files/",
        download_files,
        name="download_files",
    ),
]
