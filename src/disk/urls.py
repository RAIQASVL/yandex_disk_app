from django.urls import path
from src.disk.views import FileListView, stream_file

app_name = "disk"

urlpatterns = [
    path("", FileListView.as_view(), name="file_list"),
    path("download_files/", stream_file, name="download_files"),
]
