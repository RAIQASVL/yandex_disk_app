import unittest
from unittest.mock import patch, Mock
import os
from dotenv import load_dotenv
import requests
from disk.services.disk_service import YandexDiskService, YandexDiskFile

load_dotenv()


class TestYandexDiskService(unittest.TestCase):
    def setUp(self):
        # Ensure we have a mock token for testing
        "YANDEX_OAUTH_TOKEN" == "mock_token"
        self.service = YandexDiskService()

        # Sample response data
        self.folder_response = {
            "_embedded": {
                "items": [
                    {
                        "name": "test_file.txt",
                        "path": "/test_file.txt",
                        "type": "file",
                        "size": 1024,
                        "created": "2024-10-23T10:00:00+00:00",
                        "modified": "2024-10-23T10:00:00+00:00",
                        "mime_type": "text/plain",
                    },
                    {
                        "name": "test_image.jpg",
                        "path": "/test_image.jpg",
                        "type": "file",
                        "size": 2048,
                        "created": "2024-10-23T10:00:00+00:00",
                        "modified": "2024-10-23T10:00:00+00:00",
                        "mime_type": "image/jpeg",
                    },
                ]
            }
        }

        self.single_file_response = {
            "name": "single_file.txt",
            "path": "/single_file.txt",
            "type": "file",
            "size": 512,
            "created": "2024-10-23T10:00:00+00:00",
            "modified": "2024-10-23T10:00:00+00:00",
            "mime_type": "text/plain",
        }

        self.download_link_response = {"href": "https://example.com/download/link"}

    def test_clean_public_key(self):
        """Test public key cleaning for various URL formats"""
        test_cases = [
            ("https://disk.yandex.ru/d/abc123", "abc123"),
            ("https://disk.yandex.com/i/def456", "def456"),
            ("https://yadi.sk/d/ghi789", "ghi789"),
            ("plain_key_123", "plain_key_123"),
            ("https://disk.yandex.ru/d/p2M7pVhkNbAiGw", "p2M7pVhkNbAiGw"),
        ]

        for input_key, expected in test_cases:
            with self.subTest(input_key=input_key):
                result = self.service._clean_public_key(input_key)
                self.assertEqual(result, expected)

    @patch("requests.Session.get")
    def test_get_public_resources_folder(self, mock_get):
        """Test retrieving resources from a folder"""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = self.folder_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test the method
        files = self.service.get_public_resources("test_key")

        # Verify results
        self.assertEqual(len(files), 2)
        self.assertIsInstance(files[0], YandexDiskFile)
        self.assertEqual(files[0].name, "test_file.txt")
        self.assertEqual(files[1].name, "test_image.jpg")

    @patch("requests.Session.get")
    def test_get_public_resources_single_file(self, mock_get):
        """Test retrieving a single file resource"""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = self.single_file_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test the method
        files = self.service.get_public_resources("test_key")

        # Verify results
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "single_file.txt")
        self.assertEqual(files[0].size, 512)

    @patch("requests.Session.get")
    def test_get_download_link(self, mock_get):
        """Test retrieving download link"""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = self.download_link_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test the method
        link = self.service.get_download_link("test_key", "/test_file.txt")

        # Verify results
        self.assertEqual(link, "https://example.com/download/link")

    @patch("requests.Session.get")
    def test_handle_404_error(self, mock_get):
        """Test handling of 404 error"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Test the method
        with self.assertRaises(ValueError) as context:
            self.service.get_public_resources("invalid_key")

        self.assertIn("resource was not found", str(context.exception))

    @patch("requests.Session.get")
    def test_handle_403_error(self, mock_get):
        """Test handling of 403 error"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        # Test the method
        with self.assertRaises(ValueError) as context:
            self.service.get_public_resources("forbidden_key")

        self.assertIn("forbidden", str(context.exception))

    # def test_missing_token(self):
    #     """Test handling of missing OAuth token"""
    #     # Remove token from environment
    #     "YANDEX_OAUTH_TOKEN" == None

    #     # Test service initialization
    #     with self.assertRaises(ValueError) as context:
    #         YandexDiskService()

    #     self.assertIn("token is missing", str(context.exception))


if __name__ == "__main__":
    unittest.main()
