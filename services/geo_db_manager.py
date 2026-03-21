"""GeoLite2 database management service."""

import os
import tarfile
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import maxminddb
import requests
from rich.progress import Progress

from config import Config
from logging_config import log


class GeoDBManager:
    """Manages the lifecycle of the GeoLite2 database."""

    def __init__(self, config: Config):
        self.config = config
        self.mmdb_reader: Optional[maxminddb.Reader] = None
        self.last_db_update_time: Optional[datetime] = None
        self.current_db_version_tag: str = "N/A"
        self.current_db_file_path: Optional[str] = None

    def _cleanup_old_db_files(self, new_db_filepath: str) -> None:
        """Removes old, unused DB files."""
        if (
            self.current_db_file_path
            and self.current_db_file_path != new_db_filepath
            and os.path.exists(self.current_db_file_path)
        ):
            try:
                os.remove(self.current_db_file_path)
                log.info(
                    f"Successfully removed old database file: {self.current_db_file_path}"
                )
            except OSError as e:
                log.error(
                    f"Error deleting old database file {self.current_db_file_path}: {e}"
                )

    def _cleanup_failed_download(self, filepath: str) -> None:
        """Removes a partially downloaded or invalid file."""
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                log.info(f"Removed corrupt or incomplete database file: {filepath}")
            except OSError as e:
                log.error(f"Error removing corrupt file {filepath}: {e}")

    def _download_from_ftp(self, parsed_url, filepath: str) -> None:
        """Download database from FTP/FTPS server."""
        import ftplib

        ftp_host = parsed_url.hostname
        ftp_port = parsed_url.port or (990 if parsed_url.scheme == "ftps" else 21)
        ftp_user = parsed_url.username or "anonymous"
        ftp_pass = parsed_url.password or ""
        ftp_path = parsed_url.path

        ftp_class = ftplib.FTP_TLS if parsed_url.scheme == "ftps" else ftplib.FTP
        with closing(ftp_class()) as ftp:
            ftp.connect(ftp_host, ftp_port, timeout=30)
            ftp.login(ftp_user, ftp_pass)
            with open(filepath, "wb") as f:
                ftp.retrbinary(f"RETR {ftp_path}", f.write)

    def _download_from_http(self, url: str, filepath: str) -> None:
        """Download database from HTTP/HTTPS URL."""
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        with Progress() as progress:
            task = progress.add_task(
                f"[cyan]Downloading MMDB from {url}...", total=total_size
            )
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))

    def _load_external_database(self) -> bool:
        """Download and load database from external URL. Returns True if successful."""
        url = self.config.EXTERNAL_DB_URL
        if not url:
            return False

        parsed = urlparse(url)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        ext = os.path.splitext(parsed.path)[-1] or ".mmdb"
        new_db_filename = f"external-{timestamp}{ext}"
        new_db_filepath = os.path.join(self.config.DB_DIR, new_db_filename)

        log.info(f"Downloading MMDB from external source: {url}")
        try:
            if parsed.scheme.startswith("ftp"):
                self._download_from_ftp(parsed, new_db_filepath)
            else:
                self._download_from_http(url, new_db_filepath)

            log.info(f"Successfully downloaded external MMDB: {new_db_filepath}")
            self._load_database_file(new_db_filepath)
            return True
        except Exception as e:
            log.error(f"Failed to download/load external MMDB: {e}")
            self.mmdb_reader = None
            self._cleanup_failed_download(new_db_filepath)
            return True  # Return True to indicate this path was attempted

    def _load_custom_database(self) -> bool:
        """Load database from custom file path. Returns True if successful."""
        db_path = self.config.CUSTOM_DB_FILE
        if not db_path:
            return False

        log.info(f"Loading custom MMDB database: {db_path}")
        try:
            self._load_database_file(db_path)
            return True
        except Exception as e:
            log.error(f"Failed to load custom MMDB database: {e}")
            self.mmdb_reader = None
            return True  # Return True to indicate this path was attempted

    def _load_maxmind_database(self) -> bool:
        """Download and load database from MaxMind. Returns True if successful."""
        if not (self.config.MAXMIND_LICENSE_KEY and self.config.MAXMIND_DOWNLOAD_URL):
            log.error(
                "No valid MaxMind license key provided. "
                "Cannot download GeoLite2-City.mmdb. "
                "Please set GUNTER_MAXMIND_LICENSE_KEY."
            )
            self.mmdb_reader = None
            return False

        log.info(
            "Attempting to download GeoLite2-City.mmdb from MaxMind "
            "(official, license key required)..."
        )
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        tar_gz_path = os.path.join(
            self.config.DB_DIR, f"GeoLite2-City-{timestamp}.tar.gz"
        )

        try:
            response = requests.get(
                self.config.MAXMIND_DOWNLOAD_URL, stream=True, timeout=120
            )
            response.raise_for_status()
            with open(tar_gz_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            log.info(f"Downloaded GeoLite2-City archive: {tar_gz_path}")
            extracted_path = self._extract_mmdb_from_archive(tar_gz_path, timestamp)
            self._load_database_file(extracted_path)
            return True
        except Exception as e:
            log.error(
                f"Failed to download/extract/load official MaxMind GeoLite2 DB: {e}"
            )
            self.mmdb_reader = None
            self._cleanup_failed_download(tar_gz_path)
            return False

    def _extract_mmdb_from_archive(self, tar_gz_path: str, timestamp: str) -> str:
        """Extract .mmdb file from tar.gz archive."""
        with tarfile.open(tar_gz_path, "r:gz") as tar:
            mmdb_member = next(
                (m for m in tar.getmembers() if m.name.endswith(".mmdb")), None
            )
            if not mmdb_member:
                raise RuntimeError("No .mmdb file found in the MaxMind archive!")

            extracted_path = os.path.join(
                self.config.DB_DIR, f"GeoLite2-City-{timestamp}.mmdb"
            )
            with open(extracted_path, "wb") as out_f:
                mmdb_file = tar.extractfile(mmdb_member)
                if mmdb_file is None:
                    raise RuntimeError("Could not extract .mmdb file from archive!")
                out_f.write(mmdb_file.read())

        log.info(f"Extracted MMDB: {extracted_path}")
        return extracted_path

    def _load_database_file(self, filepath: str) -> None:
        """Load an MMDB file into the reader."""
        if self.mmdb_reader:
            self.mmdb_reader.close()

        self.mmdb_reader = maxminddb.open_database(filepath)
        self.last_db_update_time = datetime.now()
        self._cleanup_old_db_files(filepath)
        self.current_db_file_path = filepath
        log.info(f"MMDB successfully loaded from {filepath}.")

    def download_and_load_database(self) -> None:
        """
        Downloads and loads the MMDB database from an external URL,
        local file, or GeoLite2. Cleans up old versions.
        """
        os.makedirs(self.config.DB_DIR, exist_ok=True)

        # Try loading in order of priority
        if self._load_external_database():
            return
        if self._load_custom_database():
            return
        self._load_maxmind_database()

    def check_for_new_release_and_update(self) -> None:
        """
        Checks for a new version and updates if necessary.
        Skips if EXTERNAL_DB_URL or CUSTOM_DB_FILE is set.
        """
        if self.config.EXTERNAL_DB_URL or self.config.CUSTOM_DB_FILE:
            log.info(
                "External or custom DB set. Skipping automatic MaxMind update check."
            )
            return

        log.info(
            "Automatic update check is only supported for the legacy GitHub "
            "repository method and is currently bypassed."
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the database."""
        return {
            "database_loaded": self.mmdb_reader is not None,
            "last_database_update_check_utc": (
                self.last_db_update_time.isoformat()
                if self.last_db_update_time
                else "N/A"
            ),
            "current_database_version_tag": self.current_db_version_tag,
            "current_database_file": self.current_db_file_path or "N/A",
            "database_directory": self.config.DB_DIR,
        }
