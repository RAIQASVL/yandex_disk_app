import os
from dotenv import load_dotenv
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

# Load environment variables from .env file
load_dotenv()


@dataclass
class YandexDiskFile:
    """Data class for file information."""

    name: str
    path: str
    type: str
    size: int
    created: str
    modified: str
    mime_type: str


class DiskServiceInterface(ABC):
    """Interface for Yandex.Disk API operations."""

    @abstractmethod
    def get_public_resources(
        self, public_key: str, path: Optional[str] = None
    ) -> List[YandexDiskFile]:
        """Get list of files from public resource."""
        pass

    @abstractmethod
    def get_download_link(self, public_key: str, path: str) -> str:
        """Get download link for file."""
        pass


class YandexDiskService(DiskServiceInterface):
    """Implementation of Yandex.Disk API service."""

    BASE_URL = "https://cloud-api.yandex.net/v1/disk/public"

    def __init__(self):
        # Load secrets from environment variables
        self.access_token = os.getenv("YANDEX_OAUTH_TOKEN")
        if not self.access_token:
            raise ValueError(
                "Yandex OAuth token not found. Please set YANDEX_OAUTH_TOKEN in your .env file."
            )

        self.session = requests.Session()

    def get_public_resources(
        self, public_key: str, path: Optional[str] = None
    ) -> List[YandexDiskFile]:
        """Get list of files from public resource."""
        headers = {"Authorization": f"OAuth {self.access_token}"}
        params = {"public_key": public_key}
        if path:
            params["path"] = path

        # Make a request to the Yandex Disk API
        response = self.session.get(
            f"{self.BASE_URL}/resources", headers=headers, params=params
        )
        response.raise_for_status()

        data = response.json()
        files = []

        # Collect file information from the response
        for item in data.get("_embedded", {}).get("items", []):
            files.append(
                YandexDiskFile(
                    name=item["name"],
                    path=item["path"],
                    type=item["type"],
                    size=item["size"],
                    created=item["created"],
                    modified=item["modified"],
                    mime_type=item.get("mime_type", ""),
                )
            )

        return files

    def get_download_link(self, public_key: str, path: str) -> str:
        """Get download link for file."""
        headers = {"Authorization": f"OAuth {self.access_token}"}
        params = {"public_key": public_key, "path": path}

        # Make a request to get the download link
        response = self.session.get(
            f"{self.BASE_URL}/resources/download", headers=headers, params=params
        )
        response.raise_for_status()

        # Return the download link
        return response.json()["href"]


def download_file(request, public_key, path):
    """View for downloading files."""
    if not request.user.is_authenticated:
        return redirect("login")  # Redirect if user is not authenticated

    disk_service = YandexDiskService()

    try:
        # Get the download link for the requested file
        download_url = disk_service.get_download_link(public_key, path)
        print(f"Attempting to download file from URL: {download_url}")

        # Request the file from the download URL
        response = requests.get(download_url, stream=True, allow_redirects=True)
        response.raise_for_status()  # Raise an error for bad responses

        # Create HTTP response with the file content
        http_response = HttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
        # Set the content disposition header to prompt file download
        http_response["Content-Disposition"] = (
            f'attachment; filename="{quote(path.split("/")[-1])}"'
        )
        return http_response

    except requests.RequestException as e:
        print(f"Error downloading file: {e}")
        return HttpResponse("Error downloading file", status=400)
