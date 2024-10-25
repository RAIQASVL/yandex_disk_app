"""
Yandex.Disk API Service Module
Handles file operations and downloads from Yandex.Disk public folders.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
import requests
from urllib.parse import urlparse
import os
import io
import zipfile

logger = logging.getLogger(__name__)


@dataclass
class YandexDiskFile:
    """
    Represents a file from Yandex.Disk.

    Attributes:
        name: File name
        path: File path in Yandex.Disk
        type: File type (file/directory)
        size: Size in bytes
        created: Creation timestamp
        modified: Last modification timestamp
        mime_type: MIME type
        download_link: Direct download URL
    """

    name: str
    path: str
    type: str
    size: int
    created: str
    modified: str
    mime_type: str
    download_link: Optional[str] = None

    @property
    def size_formatted(self) -> str:
        """Format file size in human-readable format."""
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class YandexDiskService:
    """Service for interacting with Yandex.Disk API."""

    BASE_URL = "https://cloud-api.yandex.net/v1/disk/public"
    CHUNK_SIZE = 8192  # Chunk size for streaming

    def __init__(self):
        """Initialize service with OAuth token."""
        self.token = os.getenv("YANDEX_OAUTH_TOKEN")
        if not self.token:
            raise ValueError("Yandex OAuth token not found in environment")

        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"OAuth {self.token}", "Accept": "application/json"}
        )

    @staticmethod
    def extract_public_key(url: str) -> str:
        """Extract public key from Yandex.Disk URL."""
        try:
            parsed = urlparse(url)
            if "disk.yandex" not in parsed.netloc:
                raise ValueError("Invalid Yandex.Disk URL")

            path_parts = parsed.path.split("/")
            if "/d/" in parsed.path:
                return path_parts[-1]
            elif "/public/" in parsed.path:
                return path_parts[-1]

            raise ValueError("Could not extract public key from URL")
        except Exception as e:
            logger.error(f"Error extracting public key: {e}")
            raise ValueError(f"Invalid Yandex.Disk URL format: {str(e)}")

    def get_public_resources(self, public_url: str) -> List[YandexDiskFile]:
        """
        Fetch files from public folder.

        Args:
            public_url: Yandex.Disk public URL or direct key

        Returns:
            List of YandexDiskFile objects

        Raises:
            RuntimeError: If API request fails
        """
        try:
            params = {
                "public_key": public_url,
                "limit": 100,
                "sort": "name",
                "fields": "name,path,type,size,created,modified,mime_type,_embedded.items",
            }

            response = self.session.get(f"{self.BASE_URL}/resources", params=params)
            response.raise_for_status()
            data = response.json()

            if "_embedded" not in data or "items" not in data["_embedded"]:
                raise ValueError("Invalid API response format")

            return [
                YandexDiskFile(
                    name=item["name"],
                    path=item["path"].lstrip("/"),
                    type=item["type"],
                    size=item.get("size", 0),
                    created=item["created"],
                    modified=item["modified"],
                    mime_type=item.get("mime_type", "application/octet-stream"),
                    download_link=self.get_download_link(public_url, item["path"]),
                )
                for item in data["_embedded"]["items"]
            ]

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise RuntimeError(f"Failed to fetch resources: {str(e)}")

    def _get_public_key(self, url: str) -> str:
        """Extract public key from URL or return direct key."""
        if not url.startswith("http"):
            return url.strip()

        try:
            parsed = urlparse(url)
            if "/d/" in parsed.path:
                return parsed.path.split("/d/")[-1]
            elif "/public?" in parsed.path:
                return parsed.path.split("public?")[-1]
            return url
        except Exception as e:
            logger.error(f"Error extracting key: {e}")
            return url

    def get_download_link(self, public_key: str, path: str) -> Optional[str]:
        """Get direct download link for a file."""
        try:
            params = {"public_key": public_key, "path": path}
            response = self.session.get(
                f"{self.BASE_URL}/resources/download", params=params
            )
            response.raise_for_status()

            data = response.json()
            return data.get("href")

        except requests.RequestException as e:
            logger.error(f"Failed to get download link: {e}")
            return None

    def create_zip(self, files: List[Dict[str, str]]) -> io.BytesIO:
        """
        Create ZIP archive with multiple files.

        Args:
            files: List of dicts with 'name' and 'download_url' keys

        Returns:
            ZIP file as BytesIO object
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in files:
                try:
                    response = self.session.get(file["download_url"], stream=True)
                    response.raise_for_status()

                    # Stream directly to ZIP
                    content = io.BytesIO()
                    for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                        if chunk:
                            content.write(chunk)

                    content.seek(0)
                    zip_file.writestr(file["name"], content.getvalue())
                    logger.debug(f"Added {file['name']} to ZIP")

                except Exception as e:
                    logger.error(f"Error adding {file['name']}: {e}")
                    continue

        buffer.seek(0)
        return buffer
