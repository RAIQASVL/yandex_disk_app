from django.views.generic import ListView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
import requests

from .forms import PublicLinkForm
from .services.disk_service import YandexDiskService
from .models import PublicLink


class FileListView(LoginRequiredMixin, FormView):
    template_name = "disk_browser/file_list.html"
    form_class = PublicLinkForm
    success_url = reverse_lazy("file_list")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.disk_service = YandexDiskService()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_key = self.request.GET.get("public_key")

        if public_key:
            try:
                files = self.disk_service.get_public_resources(public_key)
                context["files"] = files
                context["public_key"] = public_key
            except requests.RequestException:
                context["error"] = "Could not fetch files. Please check the public key."

        return context

    def form_valid(self, form):
        public_key = form.cleaned_data["public_key"]
        PublicLink.objects.create(user=self.request.user, public_key=public_key)
        return redirect(f"{self.success_url}?public_key={public_key}")


def download_file(request, public_key, path):
    """View for downloading files from Yandex.Disk."""
    if not request.user.is_authenticated:
        return redirect("login")  # Redirect if the user is not authenticated

    disk_service = YandexDiskService()
    
    

    try:
        # Get the download link for the requested file
        download_url = disk_service.get_download_link(public_key, path)
        print(
            f"Attempting to download file from URL: {download_url}"
        )  # Log the download URL

        # Request the file from the download URL
        response = requests.get(download_url, stream=True, allow_redirects=True)
        response.raise_for_status()  # Raise an error for bad responses

        # Create HTTP response with the file content
        http_response = HttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get(
                "Content-Type", "application/json"
            ),
        )
        # Set the content disposition header to prompt file download
        http_response["Content-Disposition"] = (
            f'attachment; filename="{path.split("/")[-1]}"'
        )
        return http_response

    except requests.RequestException as e:
        print(f"Error downloading file: {e}")  # Log any errors that occur
        return HttpResponse(
            "Error downloading file", status=400
        )  # Return error response
