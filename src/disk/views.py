import logging
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseBadRequest
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import PublicLinkForm
from .services.disk_service import YandexDiskService
from .services.cache_service import CacheService
import requests

logger = logging.getLogger(__name__)


class FileListView(LoginRequiredMixin, FormView):
    template_name = "disk_browser/file_list.html"
    form_class = PublicLinkForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.disk_service = YandexDiskService()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_url = self.request.GET.get("public_url")
        file_type = self.request.GET.get("file_type")

        if public_url:
            try:
                # Try to get cached resources first
                cache_key = f"yandex_files_{public_url}"
                files = CacheService.get_cached_resources(cache_key)

                if files is None:
                    public_key = self.disk_service.extract_public_key(public_url)
                    path = ""
                    files = self.disk_service.get_public_resources(public_url)
                    CacheService.cache_resources(public_key, path, files)

                if file_type:
                    files = [f for f in files if self._match_file_type(f, file_type)]

                context.update(
                    {
                        "files": files,
                        "public_url": public_url,
                        "total_files": len(files),
                        "current_file_type": file_type,
                    }
                )

            except Exception as e:
                logger.error(f"Error fetching files: {e}")
                context["error"] = str(e)

        return context

    def _match_file_type(self, file, file_type: str) -> bool:
        if not file_type:
            return True

        mime_type = file.mime_type.lower()
        type_filters = {
            "document": [
                "application/pdf",
                "text/",
                "application/msword",
                "application/vnd.openxmlformats-officedocument",
            ],
            "image": ["image/"],
            "video": ["video/"],
            "audio": ["audio/"],
        }

        return any(mime_type.startswith(t) for t in type_filters.get(file_type, []))


def stream_file(request):
    """Stream file download to avoid memory issues with large files."""
    download_url = request.GET.get("download_url")

    if not download_url:
        return HttpResponseBadRequest("Download URL is required")

    try:
        # Make streaming request to Yandex
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        # Get filename from headers
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = None
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip('"')
        if not filename:
            filename = "download"  # Default filename

        # Create streaming response
        streaming_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
        streaming_response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return streaming_response

    except requests.RequestException as e:
        logger.error(f"Error streaming file: {e}")
        return JsonResponse({"error": str(e)}, status=500)
