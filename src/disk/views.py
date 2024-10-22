from django.shortcuts import render, redirect
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests
from .forms import PublicLinkForm
from .services.disk_service import YandexDiskService
from .services.cache_service import CacheService
import zipfile
import io
import mimetypes


class FileListView(LoginRequiredMixin, FormView):
    template_name = "disk_browser/file_list.html"
    form_class = PublicLinkForm

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()

    #     if self.request.method == "GET":
    #         public_key = self.request.GET.get("public_key", "")
    #         file_type = self.request.GET.get("file_type", "")
    #         print(f"GET request - public_key: {public_key}, file_type: {file_type}")

    #         kwargs["initial"] = {"public_key": public_key, "file_type": file_type}

    #     return kwargs

    def get_success_url(self):
        """Return URL to redirect to after successful form submission."""
        public_key = self.request.POST.get("public_key")
        file_type = self.request.POST.get("file_type", "")

        base_url = "/"
        if public_key:
            url = f"{base_url}?public_key={public_key}"
            if file_type:
                url += f"&file_type={file_type}"
            return url
        return base_url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_key = self.request.GET.get("public_key")
        file_type = self.request.GET.get("file_type")

        if public_key:
            try:
                # Try to get cached resources first
                files = CacheService.get_cached_resources(public_key)

                if files is None:
                    # If not cached, fetch from API
                    disk_service = YandexDiskService()
                    files = disk_service.get_public_resources(public_key)
                    # Cache the results
                    CacheService.cache_resources(public_key, "", files)

                # Apply file type filter if specified
                if file_type:
                    files = [f for f in files if self._match_file_type(f, file_type)]

                context.update(
                    {
                        "files": files,
                        "public_key": public_key,
                        "selected_files": [],
                    }
                )
            except Exception as e:
                context["error"] = f"Error fetching files: {str(e)}"

        return context

    def _match_file_type(self, file, file_type):
        """Match file to selected file type filter."""
        mime_type = file.mime_type.lower()
        return {
            "document": lambda: any(
                x in mime_type for x in ["document", "pdf", "text"]
            ),
            "image": lambda: "image" in mime_type,
            "video": lambda: "video" in mime_type,
            "audio": lambda: "audio" in mime_type,
        }.get(file_type, lambda: True)()

    def form_valid(self, form):
        """Handle valid form submission."""
        public_key = form.cleaned_data.get("public_key", "")
        file_type = form.cleaned_data.get("file_type", "")

        return super().form_valid(form)


@login_required
@require_POST
def download_files(request):
    """Handle downloading multiple files as ZIP archive."""
    try:
        # Getting data from request
        public_key = request.POST.get("public_key")
        file_paths = request.POST.getlist("file_paths[]")

        print(
            f"Received request - public_key: {public_key}, file_paths: {file_paths}"
        )  # Debug information

        if not public_key or not file_paths:
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        disk_service = YandexDiskService()

        # For single file download
        if len(file_paths) == 1:
            try:
                download_url = disk_service.get_download_link(public_key, file_paths[0])
                response = requests.get(download_url, stream=True)
                response.raise_for_status()  # Ensure response is 200 OK

                filename = file_paths[0].split("/")[-1]
                http_response = HttpResponse(
                    response.iter_content(chunk_size=8192),
                    content_type=response.headers.get(
                        "Content-Type", "application/octet-stream"
                    ),
                )
                http_response["Content-Disposition"] = (
                    f'attachment; filename="{filename}"'
                )
                return http_response

            except Exception as e:
                print(f"Error downloading single file: {str(e)}")  # Debug information
                return JsonResponse(
                    {"error": f"Error downloading file: {str(e)}"}, status=400
                )

        # For multiple files download
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for path in file_paths:
                    try:
                        download_url = disk_service.get_download_link(public_key, path)
                        response = requests.get(download_url)
                        response.raise_for_status()

                        filename = path.split("/")[-1]
                        zip_file.writestr(filename, response.content)
                    except Exception as e:
                        print(
                            f"Error adding file to ZIP: {str(e)}"
                        )  # Debug information
                        continue

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer, content_type="application/zip")
            response["Content-Disposition"] = (
                'attachment; filename="yandex_disk_files.zip"'
            )
            return response

    except Exception as e:
        print(f"General error in download_files: {str(e)}")  # Debug information
        return JsonResponse({"error": str(e)}, status=400)
