# views.py

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from io import BytesIO
import zipfile

from django.http import (
    JsonResponse,
    StreamingHttpResponse,
    HttpResponseBadRequest,
    HttpResponse,
)
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.conf import settings

import requests

from .forms import PublicLinkForm
from .services.disk_service import YandexDiskService, YandexDiskFile
from .services.cache_service import CacheService

# Configure logging
logger = logging.getLogger(__name__)


class FileListView(LoginRequiredMixin, FormView):
    """
    Main view for browsing Yandex.Disk files.

    This view handles:
    - Displaying the file browser interface
    - Processing public folder URLs
    - Filtering files by type
    - Caching results

    Attributes:
        template_name (str): Path to the template
        form_class: Form class for handling public URLs
        login_url (str): URL to redirect if user is not authenticated
    """

    template_name = "disk_browser/file_list.html"
    form_class = PublicLinkForm
    login_url = "/login/"  # Adjust as per your auth setup

    def __init__(self, **kwargs):
        """Initialize view with YandexDiskService."""
        super().__init__(**kwargs)
        self.disk_service = YandexDiskService()

    def get_initial(self) -> Dict[str, Any]:
        """
        Get initial form data, preserving URL and file type from GET parameters.

        Returns:
            Dict with initial form values
        """
        initial = super().get_initial()
        initial["public_url"] = self.request.GET.get("public_url", "")
        initial["file_type"] = self.request.GET.get("file_type", "")
        return initial

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Prepare context data for template rendering.

        Handles:
        - File fetching from Yandex.Disk
        - Caching results
        - File filtering
        - Error handling

        Returns:
            Dict containing context for template
        """
        context = super().get_context_data(**kwargs)
        public_url = self.request.GET.get("public_url")
        file_type = self.request.GET.get("file_type")

        if public_url:
            try:
                # Generate cache key from URL and file type
                cache_key = f"yandex_files_{public_url}_{file_type}"

                # Try to get cached results first
                files = CacheService.get_cached_resources(cache_key)

                if files is None:
                    # Extract public key and fetch resources
                    public_key = self.disk_service.extract_public_key(public_url)
                    files = self.disk_service.get_public_resources(public_url)

                    # Cache the full result set
                    CacheService.cache_resources(public_key, "", files)

                # Apply file type filter if specified
                if file_type:
                    files = [f for f in files if self._match_file_type(f, file_type)]

                # Update context with results
                context.update(
                    {
                        "files": files,
                        "public_url": public_url,
                        "total_files": len(files),
                        "current_file_type": file_type,
                    }
                )

            except ValidationError as e:
                logger.warning(f"Validation error for URL {public_url}: {e}")
                context["error"] = str(e)
            except Exception as e:
                logger.error(f"Error fetching files for URL {public_url}: {e}")
                context["error"] = f"Error fetching files: {str(e)}"

        return context

    def _match_file_type(self, file: YandexDiskFile, file_type: str) -> bool:
        """
        Match file against specified type filter.

        Args:
            file: YandexDiskFile object to check
            file_type: Type to filter by

        Returns:
            bool: True if file matches filter
        """
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
            "archive": [
                "application/zip",
                "application/x-rar",
                "application/x-7z",
                "application/x-tar",
                "application/x-gzip",
            ],
        }

        return any(mime_type.startswith(t) for t in type_filters.get(file_type, []))


@csrf_protect
def stream_file(request) -> HttpResponse:
    """
    Handle both single and multiple file downloads.

    This view supports:
    - Single file streaming download
    - Multiple file ZIP archive creation
    - Progress tracking for large files
    - Error handling with appropriate responses

    Methods:
        GET: Handle single file download
        POST: Handle multiple file download (creates ZIP)

    Returns:
        HttpResponse with appropriate content and headers
    """
    if request.method == "POST":
        return _handle_multiple_files(request)
    else:
        return _handle_single_file(request)


def _handle_single_file(request) -> HttpResponse:
    """
    Handle single file download request.

    Args:
        request: HTTP request object

    Returns:
        StreamingHttpResponse for file download
    """
    download_url = request.GET.get("download_url")
    if not download_url:
        return HttpResponseBadRequest("Download URL is required")

    try:
        # Request file with streaming enabled
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        # Extract filename from headers
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = None
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip('"')
        if not filename:
            filename = "download"

        # Create streaming response
        streaming_response = StreamingHttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )

        # Set headers for download
        streaming_response["Content-Disposition"] = f'attachment; filename="{filename}"'
        if "Content-Length" in response.headers:
            streaming_response["Content-Length"] = response.headers["Content-Length"]

        return streaming_response

    except requests.RequestException as e:
        logger.error(f"Error streaming file: {e}")
        return JsonResponse(
            {"error": "Failed to download file. Please try again."}, status=500
        )


def _handle_multiple_files(request) -> HttpResponse:
    """
    Handle multiple file download request.

    Creates a ZIP archive containing all requested files.

    Args:
        request: HTTP request object

    Returns:
        HttpResponse with ZIP file
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        files = data.get("files", [])

        if not files:
            return HttpResponseBadRequest("No files selected")

        # Create ZIP file in memory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"yandex_files_{timestamp}.zip"

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_info in files:
                try:
                    # Download and add each file to ZIP
                    response = requests.get(file_info["url"], stream=True)
                    response.raise_for_status()

                    # Ensure valid filename
                    safe_filename = _sanitize_filename(file_info["name"])

                    # Write file content to ZIP
                    zip_file.writestr(safe_filename, response.content)

                except Exception as e:
                    logger.error(f"Error processing file {file_info.get('name')}: {e}")
                    # Continue with other files if one fails

        # Prepare response
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{zip_filename}"'

        # Optional: Set content length if buffer size is manageable
        if zip_buffer.tell() < settings.MAX_ZIPFILE_SIZE:
            response["Content-Length"] = zip_buffer.tell()

        return response

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        return HttpResponseBadRequest("Invalid request format")
    except Exception as e:
        logger.error(f"Error creating ZIP archive: {e}")
        return JsonResponse(
            {"error": "Failed to create ZIP archive. Please try again."}, status=500
        )


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent ZIP slip and ensure compatibility.

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    # Remove path separators and normalize
    filename = os.path.basename(filename)

    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    return filename


def handle_download_error(request, error_message: str) -> HttpResponse:
    """
    Handle download errors gracefully.

    Args:
        request: HTTP request object
        error_message: Error message to display

    Returns:
        HttpResponse with error page
    """
    logger.error(f"Download error: {error_message}")
    context = {
        "error_title": "Download Error",
        "error_message": error_message,
        "back_url": request.META.get("HTTP_REFERER", "/"),
    }
    return render(request, "disk_browser/error.html", context, status=500)
