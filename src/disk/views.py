from urllib.parse import quote
from django.shortcuts import render, redirect
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import requests
from .forms import PublicLinkForm
from .services.disk_service import YandexDiskService
from .services.cache_service import CacheService
import zipfile
import io

import logging

logger = logging.getLogger(__name__)


class FileListView(LoginRequiredMixin, FormView):
    template_name = "disk_browser/file_list.html"
    form_class = PublicLinkForm

    def get_success_url(self):
        """Return URL to redirect to after successful form submission."""
        public_key = self.request.POST.get("public_key")

        if not public_key:
            return HttpResponse("Public key is required", status=400)

        file_type = self.request.POST.get("file_type", "")

        # url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_key}"

        base_url = "/"
        if public_key:
            url = f"{base_url}?public_key={public_key}"
            if file_type:
                url += f"&file_type={file_type}"
            return url
        return base_url

    def get_context_data(self, **kwargs):
        """
        Get context data for the view with enhanced error handling and logging.
        """
        context = super().get_context_data(**kwargs)
        # Get request parameters
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

                # Initialize form with current values
                context["form"].initial.update(
                    {"public_key": public_key, "file_type": file_type}
                )

                # Clean public key using form validation
                form = self.get_form()
                if not form.is_bound:
                    form.data = self.request.GET
                    form.is_bound = True

                if form.is_valid():
                    cleaned_public_key = form.cleaned_data["public_key"]
                    logger.debug(f"Cleaned public key: {cleaned_public_key}")

                    # Apply file type filter if specified
                    if file_type:
                        original_count = len(files)
                        files = [
                            f for f in files if self._match_file_type(f, file_type)
                        ]

                        context.update(
                            {
                                "files": files,
                                "public_key": public_key,
                                "selected_files": [],
                            }
                        )

                        logger.debug(
                            f"Filtered files by type {file_type}: {len(files)} of {original_count}"
                        )

                    # Update context with results
                    context.update(
                        {
                            "files": files,
                            "public_key": cleaned_public_key,
                            "selected_files": [],
                            "total_files": len(files),
                        }
                    )
                else:
                    logger.error(f"Form validation errors: {form.errors}")
                    error_messages = []
                    for field, errors in form.errors.items():
                        for error in errors:
                            error_messages.append(f"{field}: {error}")
                    context["error"] = "Validation error: " + "; ".join(error_messages)

            except ValueError as ve:
                logger.error(f"Validation error: {str(ve)}", exc_info=True)
                context["error"] = f"Invalid input: {str(ve)}"

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                context["error"] = f"Error fetching files: {str(e)}"

            finally:
                # Always include current filter state in context
                context["current_file_type"] = file_type

        logger.debug(f"Final context keys: {context.keys()}")
        return context

    def _match_file_type(self, file, file_type):
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
        return super().form_valid(form)


@login_required
@require_POST
def download_files(request):
    public_key = request.POST.get("public_key")
    file_paths = request.POST.getlist("file_paths[]")

    if not public_key or not file_paths:
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    disk_service = YandexDiskService()

    if len(file_paths) == 1:
        return handle_single_download(disk_service, public_key, file_paths[0])
    else:
        return handle_multiple_downloads(disk_service, public_key, file_paths)


def handle_single_download(disk_service, public_key, file_path):
    try:
        download_url = disk_service.get_download_link(public_key, file_path)
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        http_response = HttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
        http_response["Content-Disposition"] = (
            f'attachment; filename="{quote(file_path.split("/")[-1])}"'
        )
        return http_response

    except requests.RequestException as e:
        logger.error(f"Error downloading file: {e}")
        return JsonResponse({"error": "Error downloading file"}, status=400)


def handle_multiple_downloads(disk_service, public_key, file_paths):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for path in file_paths:
            try:
                download_url = disk_service.get_download_link(public_key, path)
                response = requests.get(download_url)
                response.raise_for_status()

                zip_file.writestr(path.split("/")[-1], response.content)
            except Exception as e:
                logger.error(f"Error adding file to ZIP: {str(e)}")
                # Optionally, you can skip the file or handle errors differently
                continue  # Skip to the next file

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="yandex_disk_files.zip"'
    return response
