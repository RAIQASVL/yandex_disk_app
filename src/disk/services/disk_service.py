from dataclasses import dataclass
from typing import List, Optional
import logging
import requests
from urllib.parse import urlparse
import os
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class YandexDiskFile:
    """Represents a file in Yandex.Disk."""

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
        """Return human-readable file size."""
        size = self.size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class YandexDiskService:
    """Service for interacting with Yandex.Disk API."""

    BASE_URL = "https://cloud-api.yandex.net/v1/disk/public"

    def __init__(self):
        self.token = os.getenv("YANDEX_OAUTH_TOKEN")
        if not self.token:
            raise ValueError("Yandex OAuth token not found in environment variables")

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

    def get_public_resources(
        self, public_url: str, limit: int = 100
    ) -> List[YandexDiskFile]:
        """Fetch resources from public folder."""
        try:
            public_key = public_url
            params = {
                "public_key": public_key,
                "limit": limit,
                "sort": "name",
                "fields": "name,path,type,size,created,modified,mime_type,_embedded.items",
            }

            response = self.session.get(f"{self.BASE_URL}/resources", params=params)
            response.raise_for_status()

            data = response.json()
            if "_embedded" not in data or "items" not in data["_embedded"]:
                raise ValueError("Invalid API response format")

            files = []
            for item in data["_embedded"]["items"]:
                # Get download link for each file
                download_link = self.get_download_link(public_key, item["path"])

                files.append(
                    YandexDiskFile(
                        name=item["name"],
                        path=item["path"].lstrip("/"),
                        type=item["type"],
                        size=item.get("size", 0),
                        created=item["created"],
                        modified=item["modified"],
                        mime_type=item.get("mime_type", "application/octet-stream"),
                        download_link=download_link,
                    )
                )

            return files

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise RuntimeError(f"Failed to fetch resources: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing resources: {e}")
            raise RuntimeError(f"Error processing resources: {str(e)}")

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
