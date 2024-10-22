from django.urls import path
from .views import FileListView, download_file

urlpatterns = [
    path("", FileListView.as_view(), name="file_list"),
    path("download/<str:public_key>/<path:path>/", download_file, name="download_file"),
]
