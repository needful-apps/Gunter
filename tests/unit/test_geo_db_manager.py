import os
import tempfile
from datetime import datetime
from unittest import mock

import maxminddb
import pytest
import requests

from app import Config, GeoDBManager


@pytest.fixture
def mock_config():
    class DummyConfig:
        DB_FILE_PREFIX = "GeoLite2-City"
        DB_FILE_SUFFIX = ".mmdb"
        DB_DOWNLOAD_URL = "https://example.com/GeoLite2-City.mmdb"
        GITHUB_RELEASE_API_URL = (
            "https://api.github.com/repos/example/GeoLite.mmdb/releases/latest"
        )
        DB_DIR = "/tmp"
        EXTERNAL_DB_URL = None
        CUSTOM_DB_FILE = None
        # Neue Attribute für MaxMind-Logik
        MAXMIND_LICENSE_KEY = None
        MAXMIND_DOWNLOAD_URL = None

    return DummyConfig()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield temp_dir
        os.chdir(old_cwd)


class TestGeoDBManager:
    def test_init(self, mock_config):
        """Test the initialization of the GeoDBManager."""
        manager = GeoDBManager(mock_config)
        assert manager.config == mock_config
        assert manager.mmdb_reader is None
        assert manager.last_db_update_time is None
        assert manager.current_db_version_tag == "N/A"
        assert manager.current_db_file_path is None

    def test_get_status(self, mock_config):
        """Test the status method returns expected dictionary."""
        manager = GeoDBManager(mock_config)
        status = manager.get_status()

        assert "database_loaded" in status
        assert not status["database_loaded"]
        assert status["last_database_update_check_utc"] == "N/A"
        assert status["current_database_version_tag"] == "N/A"
        assert status["current_database_file"] == "N/A"

        # Simulate custom DB file usage
        mock_config.CUSTOM_DB_FILE = "/custom/location.mmdb"
        manager.current_db_file_path = mock_config.CUSTOM_DB_FILE
        status = manager.get_status()
        assert status["current_database_file"] == "/custom/location.mmdb"

        # Set some values and test again
        manager.mmdb_reader = mock.MagicMock()
        manager.last_db_update_time = datetime(2023, 1, 1)
        manager.current_db_version_tag = "v1.0.0"
        status = manager.get_status()
        assert status["database_loaded"]
        assert status["last_database_update_check_utc"] == "2023-01-01T00:00:00"
        assert status["current_database_version_tag"] == "v1.0.0"

    @mock.patch("app.maxminddb.open_database")
    @mock.patch("app.requests.get")
    def test_download_and_load_database_success(
        self, mock_get, mock_open_db, mock_config, temp_dir
    ):
        """Test successful download and loading of the database (externe Quelle)."""
        # Setup mocks
        mock_response = mock.MagicMock()
        mock_response.headers.get.return_value = 100
        mock_response.iter_content.return_value = [b"test data"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        mock_reader = mock.MagicMock()
        mock_open_db.return_value = mock_reader

        # EXTERNAL_DB_URL setzen, damit der Download-Zweig getestet wird
        mock_config.EXTERNAL_DB_URL = mock_config.DB_DOWNLOAD_URL

        # Create the manager
        manager = GeoDBManager(mock_config)

        # Test the method
        manager.download_and_load_database()

        # Assertions
        mock_get.assert_called_once_with(
            mock_config.DB_DOWNLOAD_URL, stream=True, timeout=60
        )
        mock_open_db.assert_called_once()
        assert manager.mmdb_reader == mock_reader
        assert manager.last_db_update_time is not None
        assert os.path.exists(manager.current_db_file_path)

    @mock.patch("app.requests.get")
    def test_download_failure(self, mock_get, mock_config, temp_dir):
        """Test failure handling when download fails."""
        # Setup mock to raise an exception
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        # Create the manager
        manager = GeoDBManager(mock_config)

        # Test the method
        manager.download_and_load_database()

        # Assertions
        assert manager.mmdb_reader is None
        assert manager.current_db_file_path is None

    @mock.patch("app.requests.get")
    def test_check_for_new_release_new_version(self, mock_get, mock_config):
        """Test checking for a new release when a new version is available."""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"tag_name": "v1.0.1"}
        mock_get.return_value = mock_response

        # Create the manager and set current version
        manager = GeoDBManager(mock_config)
        manager.current_db_version_tag = "v1.0.0"

        # Mock the download method
        manager.download_and_load_database = mock.MagicMock()

        # Test the method
        manager.check_for_new_release_and_update()

        # Assertions
        mock_get.assert_called_once_with(mock_config.GITHUB_RELEASE_API_URL, timeout=10)
        assert manager.current_db_version_tag == "v1.0.1"
        manager.download_and_load_database.assert_called_once()

    @mock.patch("app.requests.get")
    def test_check_for_new_release_same_version(self, mock_get, mock_config):
        """Test checking for a new release when the current version is up to date."""
        # Setup mock response
        mock_response = mock.MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"tag_name": "v1.0.0"}
        mock_get.return_value = mock_response

        # Create the manager and set current version
        manager = GeoDBManager(mock_config)
        manager.current_db_version_tag = "v1.0.0"

        # Mock the download method
        manager.download_and_load_database = mock.MagicMock()

        # Test the method
        manager.check_for_new_release_and_update()

        # Assertions
        assert manager.current_db_version_tag == "v1.0.0"
        manager.download_and_load_database.assert_not_called()

    def test_cleanup_old_db_files(self, mock_config, temp_dir):
        """Test removal of old database files."""
        # Create a test file
        old_file = os.path.join(temp_dir, "old_db.mmdb")
        with open(old_file, "w") as f:
            f.write("test")

        # Create manager and set current file
        manager = GeoDBManager(mock_config)
        manager.current_db_file_path = old_file

        # Test cleanup with new file
        new_file = os.path.join(temp_dir, "new_db.mmdb")
        manager._cleanup_old_db_files(new_file)

        # Assertion - old file should be removed
        assert not os.path.exists(old_file)
