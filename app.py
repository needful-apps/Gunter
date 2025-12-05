import ipaddress
import json
import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

import maxminddb
import requests
import whois
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
from flask_restx import Api, Namespace, Resource, fields
from ipwhois import IPWhois
from rich.logging import RichHandler
from rich.progress import Progress
from waitress import serve


# --- Configuration ---
class Config:
    CUSTOM_DB_FILE = os.environ.get("GUNTER_DB_FILE")
    EXTERNAL_DB_URL = os.environ.get("GUNTER_DB_URL")
    DEFAULT_LANG = os.environ.get("GUNTER_LANG", "de")
    DB_FILE_PREFIX = "GeoLite2-City"
    DB_FILE_SUFFIX = ".mmdb"
    MAXMIND_LICENSE_KEY = os.environ.get("GUNTER_MAXMIND_LICENSE_KEY")
    MAXMIND_DOWNLOAD_URL = (
        f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={os.environ.get('GUNTER_MAXMIND_LICENSE_KEY','')}&suffix=tar.gz"
        if os.environ.get("GUNTER_MAXMIND_LICENSE_KEY")
        else None
    )
    DB_DIR = os.environ.get("GUNTER_DB_DIR", "/data")
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 6600
    SCHEDULER_UPDATE_DAYS = 1
    ENABLE_STATUS_ENDPOINT = (
        os.environ.get("GUNTER_ENABLE_STATUS", "true").lower() == "true"
    )
    ENABLE_API_DOCS = os.environ.get("GUNTER_ENABLE_API_DOCS", "true").lower() == "true"
    CORS_ORIGINS = os.environ.get("GUNTER_CORS_ORIGINS")


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("rich")


# --- Service classes for encapsulated logic ---
class GeoDBManager:
    """Manages the lifecycle of the GeoLite2 database."""

    def __init__(self, config: Config):
        self.config = config
        self.mmdb_reader: Optional[maxminddb.Reader] = None
        self.last_db_update_time: Optional[datetime] = None
        self.current_db_version_tag: str = "N/A"
        self.current_db_file_path: Optional[str] = None

    def _cleanup_old_db_files(self, new_db_filepath: str):
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

    def _cleanup_failed_download(self, filepath: str):
        """Removes a partially downloaded or invalid file."""
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                log.info(f"Removed corrupt or incomplete database file: {filepath}")
            except OSError as e:
                log.error(f"Error removing corrupt file {filepath}: {e}")

    def download_and_load_database(self):
        """Downloads and loads the MMDB database from an external URL, local file, or GeoLite2. Cleans up old versions."""
        import shutil
        from urllib.parse import urlparse

        os.makedirs(self.config.DB_DIR, exist_ok=True)

        # 1. External DB URL (http(s), ftp(s))
        if self.config.EXTERNAL_DB_URL:
            url = self.config.EXTERNAL_DB_URL
            parsed = urlparse(url)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            ext = os.path.splitext(parsed.path)[-1] or ".mmdb"
            new_db_filename = f"external-{timestamp}{ext}"
            new_db_filepath = os.path.join(self.config.DB_DIR, new_db_filename)
            log.info(f"Downloading MMDB from external source: {url}")
            try:
                if parsed.scheme.startswith("ftp"):
                    import ftplib
                    from contextlib import closing

                    ftp_host = parsed.hostname
                    ftp_port = parsed.port or (990 if parsed.scheme == "ftps" else 21)
                    ftp_user = parsed.username or "anonymous"
                    ftp_pass = parsed.password or ""
                    ftp_path = parsed.path
                    with closing(
                        ftplib.FTP_TLS() if parsed.scheme == "ftps" else ftplib.FTP()
                    ) as ftp:
                        ftp.connect(ftp_host, ftp_port, timeout=30)
                        ftp.login(ftp_user, ftp_pass)
                        with open(new_db_filepath, "wb") as f:
                            ftp.retrbinary(f"RETR {ftp_path}", f.write)
                else:
                    response = requests.get(url, stream=True, timeout=60)
                    response.raise_for_status()
                    total_size = int(response.headers.get("content-length", 0))
                    with Progress() as progress:
                        task = progress.add_task(
                            f"[cyan]Downloading MMDB from {url}...", total=total_size
                        )
                        with open(new_db_filepath, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                                progress.update(task, advance=len(chunk))
                log.info(f"Successfully downloaded external MMDB: {new_db_filepath}")
                if self.mmdb_reader:
                    self.mmdb_reader.close()
                self.mmdb_reader = maxminddb.open_database(new_db_filepath)
                self.last_db_update_time = datetime.now()
                self._cleanup_old_db_files(new_db_filepath)
                self.current_db_file_path = new_db_filepath
                log.info(f"External MMDB successfully loaded from {new_db_filepath}.")
            except Exception as e:
                log.error(f"Failed to download/load external MMDB: {e}")
                self.mmdb_reader = None
                self._cleanup_failed_download(new_db_filepath)
            return

        # 2. Local custom DB file
        if self.config.CUSTOM_DB_FILE:
            db_path = self.config.CUSTOM_DB_FILE
            log.info(f"Loading custom MMDB database: {db_path}")
            try:
                if self.mmdb_reader:
                    self.mmdb_reader.close()
                self.mmdb_reader = maxminddb.open_database(db_path)
                self.last_db_update_time = datetime.now()
                self.current_db_file_path = db_path
                log.info(f"Custom MMDB database successfully loaded from {db_path}.")
            except Exception as e:
                log.error(f"Failed to load custom MMDB database: {e}")
                self.mmdb_reader = None
            return

        # 3. Default: Download GeoLite2 (official MaxMind, requires license key)
        import tarfile

        if self.config.MAXMIND_LICENSE_KEY and self.config.MAXMIND_DOWNLOAD_URL:
            log.info(
                "Attempting to download GeoLite2-City.mmdb from MaxMind (official, license key required)..."
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
                with tarfile.open(tar_gz_path, "r:gz") as tar:
                    mmdb_member = next(
                        (m for m in tar.getmembers() if m.name.endswith(".mmdb")), None
                    )
                    if not mmdb_member:
                        raise RuntimeError(
                            "No .mmdb file found in the MaxMind archive!"
                        )
                    extracted_path = os.path.join(
                        self.config.DB_DIR, f"GeoLite2-City-{timestamp}.mmdb"
                    )
                    with open(extracted_path, "wb") as out_f:
                        out_f.write(tar.extractfile(mmdb_member).read())
                log.info(f"Extracted MMDB: {extracted_path}")
                if self.mmdb_reader:
                    self.mmdb_reader.close()
                self.mmdb_reader = maxminddb.open_database(extracted_path)
                self.last_db_update_time = datetime.now()
                self._cleanup_old_db_files(extracted_path)
                self.current_db_file_path = extracted_path
                log.info(
                    f"GeoLite2-City.mmdb successfully loaded from {extracted_path}."
                )
            except Exception as e:
                log.error(
                    f"Failed to download/extract/load official MaxMind GeoLite2 DB: {e}"
                )
                self.mmdb_reader = None
                self._cleanup_failed_download(tar_gz_path)
            return
        log.error(
            "No valid MaxMind license key provided. Cannot download GeoLite2-City.mmdb. Please set GUNTER_MAXMIND_LICENSE_KEY."
        )
        self.mmdb_reader = None

    def check_for_new_release_and_update(self):
        """Checks for a new version and updates if necessary.
        For external URLs and MaxMind, re-downloads the database.
        Skips if CUSTOM_DB_FILE is set (local file)."""
        if self.config.CUSTOM_DB_FILE:
            log.info("Custom DB file set. Skipping automatic update check.")
            return

        # For external URL or MaxMind, re-download to get the latest version
        if self.config.EXTERNAL_DB_URL or (
            self.config.MAXMIND_LICENSE_KEY and self.config.MAXMIND_DOWNLOAD_URL
        ):
            log.info("Checking for database updates...")
            self.download_and_load_database()
            log.info("Database update check completed.")
        else:
            log.info(
                "No external URL or MaxMind license key configured. "
                "Skipping automatic update check."
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


class WhoisService:
    """Provides WHOIS lookups for IPs and domains."""

    def _is_ip(self, target: str) -> bool:
        try:
            ipaddress.ip_address(target)
            return True
        except ValueError:
            return False

    def _get_ip_whois(self, ip: str) -> Dict[str, Any]:
        try:
            ip_whois = IPWhois(ip)
            result = ip_whois.lookup_rdap(depth=1)
            log.info(f"IP WHOIS lookup for {ip} successful.")
            return {
                "asn": result.get("asn"),
                "asn_description": result.get("asn_description"),
                "network": result.get("network", {}),
                "objects": result.get("objects", {}),
            }
        except Exception as e:
            log.error(f"IP WHOIS lookup for {ip} failed: {e}")
            return {"error": f"IP WHOIS lookup failed: {str(e)}"}

    def _get_domain_whois(self, domain: str) -> Dict[str, Any]:
        try:
            domain_info = whois.whois(domain)
            log.info(f"Domain WHOIS lookup for {domain} successful.")
            if domain_info:
                info_dict: Dict[str, Union[str, List[str], Dict[str, Any], None]] = {}
                for k, v in domain_info.items():
                    if isinstance(v, datetime):
                        info_dict[k] = v.isoformat()
                    elif isinstance(v, list) and v and isinstance(v[0], datetime):
                        formatted_dates = [item.isoformat() for item in v]
                        info_dict[k] = formatted_dates
                    elif v is not None:
                        info_dict[k] = v
                return info_dict
            else:
                return {"error": "No WHOIS data found"}
        except Exception as e:
            log.error(f"Domain WHOIS lookup for {domain} failed: {e}")
            return {"error": f"Domain WHOIS lookup failed: {str(e)}"}

    def get_whois_data(self, target: str) -> Dict[str, Any]:
        """Performs a WHOIS lookup for an IP address or domain."""
        data: Dict[str, Any] = {
            "target": target,
            "lookup_timestamp": datetime.now().isoformat(),
        }
        if self._is_ip(target):
            data["ip_whois"] = self._get_ip_whois(target)
            data["reverse_dns"] = self.resolve_ip_to_domain(target)
        else:
            data["domain_whois"] = self._get_domain_whois(target)
        return data

    def resolve_ip_to_domain(self, ip: str) -> Optional[str]:
        """Attempts to resolve an IP address to a domain name via reverse DNS."""
        try:
            domain_name, _, _ = socket.gethostbyaddr(ip)
            log.info(f"Reverse DNS for {ip} successful: {domain_name}")
            return domain_name
        except (socket.herror, socket.gaierror):
            log.debug(f"Reverse DNS for {ip} failed.")
            return None


def filter_names_by_lang(
    data: Union[Dict[str, Any], List[Any]], lang_code: str, fallback_lang: str = "en"
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively processes a dictionary or list to replace 'names' dictionaries
    with a single 'name' field for the specified language.
    """
    if isinstance(data, dict):
        if "names" in data and isinstance(data["names"], dict):
            names = data["names"]
            selected_name = (
                names.get(lang_code)
                or names.get(fallback_lang)
                or next(iter(names.values()), None)
            )
            new_dict: Dict[str, Any] = {
                k: filter_names_by_lang(v, lang_code, fallback_lang)
                for k, v in data.items()
                if k != "names"
            }
            if selected_name:
                new_dict["name"] = selected_name
            return new_dict
        return {
            k: filter_names_by_lang(v, lang_code, fallback_lang)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [filter_names_by_lang(item, lang_code, fallback_lang) for item in data]
    return data


# --- Global Service Instances ---
db_manager = GeoDBManager(Config())
whois_service = WhoisService()


def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    config = Config()

    # Add manual CORS handler
    @app.after_request
    def after_request(response):
        cors_origins = os.environ.get("GUNTER_CORS_ORIGINS")
        if cors_origins:
            origin = request.headers.get("Origin")
            # Always add CORS headers when CORS is enabled
            if cors_origins == "*":
                response.headers["Access-Control-Allow-Origin"] = "*"
            elif origin:
                allowed_origins = [origin.strip() for origin in cors_origins.split(",")]
                if origin in allowed_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"

            # Add these headers for all CORS-enabled responses
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, "
                "Access-Control-Request-Method, "
                "Access-Control-Request-Headers"
            )
        return response

    # Handle preflight requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            cors_origins = os.environ.get("GUNTER_CORS_ORIGINS")
            if cors_origins:
                origin = request.headers.get("Origin")
                response = jsonify()
                response.status_code = 200

                # Always add CORS headers for OPTIONS when CORS is enabled
                if cors_origins == "*":
                    response.headers["Access-Control-Allow-Origin"] = "*"
                elif origin:
                    allowed_origins = [
                        origin.strip() for origin in cors_origins.split(",")
                    ]
                    if origin in allowed_origins:
                        response.headers["Access-Control-Allow-Origin"] = origin
                        response.headers["Access-Control-Allow-Credentials"] = "true"

                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, "
                    "Access-Control-Request-Method, "
                    "Access-Control-Request-Headers"
                )
                return response

    # --- OpenAPI/Swagger Setup ---
    api = Api(
        app,
        version="1.0",
        title="Gunter API",
        description="API for Geolocation, WHOIS queries, and Reverse DNS",
        doc=(
            "/api/docs" if config.ENABLE_API_DOCS else False
        ),  # Disable Swagger UI if not enabled
        prefix="/api",
    )

    # Define namespaces for different endpoints
    geo_ns = Namespace("geo-lookup", description="Geolocation endpoint")
    whois_ns = Namespace("whois", description="WHOIS query endpoint")
    api.add_namespace(geo_ns)
    api.add_namespace(whois_ns)

    if config.ENABLE_STATUS_ENDPOINT:
        status_ns = Namespace("status", description="Status endpoint")
        api.add_namespace(status_ns)

    # --- Models ---
    database_status_model = api.model(
        "DatabaseStatus",
        {
            "database_loaded": fields.Boolean(
                description="Indicates if the database is loaded"
            ),
            "last_database_update_check_utc": fields.String(
                description="Timestamp of the last database update check"
            ),
            "current_database_version_tag": fields.String(
                description="Current database version"
            ),
            "current_database_file": fields.String(
                description="Currently used database file"
            ),
        },
    )

    whois_data_model = api.model(
        "WhoisData",
        {
            "target": fields.String(
                description="Target of the WHOIS query (IP or domain)"
            ),
            "lookup_timestamp": fields.String(description="Query timestamp"),
            "ip_whois": fields.Raw(description="WHOIS data for IP addresses"),
            "domain_whois": fields.Raw(description="WHOIS data for domains"),
            "reverse_dns": fields.String(
                description="Reverse DNS result (if available)"
            ),
        },
    )

    geo_lookup_model = api.model(
        "GeoLookup",
        {
            "city": fields.Raw(description="City information"),
            "country": fields.Raw(description="Country information"),
            "continent": fields.Raw(description="Continent information"),
            "location": fields.Raw(description="Location information (coordinates)"),
            "postal": fields.Raw(description="Postal code information"),
            "subdivisions": fields.Raw(
                description="Subdivisions information (states, provinces)"
            ),
            "registered_country": fields.Raw(
                description="Registered country information"
            ),
            "database_info": fields.Raw(description="Database status information"),
            "whois_data": fields.Nested(
                whois_data_model, description="WHOIS data (optional)"
            ),
        },
    )

    # --- API Resources ---
    @geo_ns.route("/<string:ip>")
    @geo_ns.doc(
        params={"ip": "IP address or domain name for geolocation"},
        responses={
            200: "Success",
            400: "Invalid IP address or domain name",
            404: "IP address not found",
            503: "GeoLite2 database not available",
        },
    )
    class GeoLookup(Resource):
        @geo_ns.doc(
            params={
                "lang": "Language code for the response (e.g., de, en, fr)",
                "exclude_whois": "If true, WHOIS data will be excluded from the response",
            }
        )
        @geo_ns.marshal_with(geo_lookup_model, skip_none=True, code=200)
        def get(self, ip):
            if not db_manager.mmdb_reader:
                return geo_ns.abort(
                    503,
                    error="GeoLite2 database not available. Please try again later.",
                )

            # Store original input for error messages and whois lookups
            original_input = ip
            is_domain = False

            # Try to validate as IP address first
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                # Not a valid IP, try to resolve as domain name
                is_domain = True
                try:
                    resolved_ip = socket.gethostbyname(ip)
                    log.info(f"Resolved domain {ip} to IP {resolved_ip}")
                    ip = resolved_ip
                except (socket.gaierror, socket.herror) as e:
                    log.error(f"Failed to resolve domain {ip}: {e}")
                    return geo_ns.abort(
                        400,
                        error=f"Invalid IP address or unable to resolve domain name: {original_input}",
                    )

            record = db_manager.mmdb_reader.get(ip)
            if not record:
                log.info(f"IP address not found in database: {ip}")
                return geo_ns.abort(404, error="IP address not found in the database.")
            try:
                lang = request.args.get("lang", config.DEFAULT_LANG).lower()
                record_dict: Dict[str, Any] = {}
                if record and isinstance(record, dict):
                    for key, value in record.items():
                        record_dict[key] = value
                processed_record = filter_names_by_lang(record_dict, lang)
                processed_record = cast(Dict[str, Any], processed_record)
                processed_record["database_info"] = {
                    "last_updated_utc": (
                        db_manager.last_db_update_time.isoformat()
                        if db_manager.last_db_update_time
                        else "N/A"
                    ),
                    "version_tag": db_manager.current_db_version_tag,
                }
                if request.args.get("exclude_whois", "false").lower() != "true":
                    # Use original domain for WHOIS if input was a domain, otherwise use resolved IP
                    whois_target = original_input if is_domain else ip
                    log.info(f"Including WHOIS data for: {whois_target}")
                    processed_record["whois_data"] = whois_service.get_whois_data(
                        whois_target
                    )
                log.info(f"Lookup for IP: {ip}, Lang: {lang} successful.")
                return processed_record
            except Exception as e:
                log.error(f"Error during IP lookup for {ip}: {e}")
                response = jsonify({"error": "An internal server error occurred."})
                response.status_code = 500
                return response

    if config.ENABLE_STATUS_ENDPOINT:

        @status_ns.route("")
        class Status(Resource):
            @status_ns.marshal_with(database_status_model)
            def get(self):
                return db_manager.get_status()

    @whois_ns.route("/<string:target>")
    @whois_ns.doc(
        params={"target": "IP address or domain name for the WHOIS query"},
        responses={200: "Success", 500: "Internal server error"},
    )
    class WhoisLookup(Resource):
        @whois_ns.marshal_with(whois_data_model, skip_none=True)
        def get(self, target):
            try:
                whois_data = whois_service.get_whois_data(target)
                return whois_data
            except Exception as e:
                log.error(f"Error during WHOIS lookup for {target}: {e}")
                whois_ns.abort(500, error="An internal server error occurred.")

    return app


if __name__ == "__main__":
    app = create_app()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=db_manager.check_for_new_release_and_update,
        trigger="interval",
        days=Config.SCHEDULER_UPDATE_DAYS,
        id="daily_db_update",
    )
    log.info("Performing initial database download on startup...")
    db_manager.download_and_load_database()
    log.info("Initial database load complete.")
    scheduler.start()
    log.info(
        f"Scheduler started. Checking every {Config.SCHEDULER_UPDATE_DAYS} day(s)."
    )
    log.info(
        f"Starting Flask app with Waitress on http://{Config.FLASK_HOST}:{Config.FLASK_PORT}"
    )
    serve(app, host=Config.FLASK_HOST, port=Config.FLASK_PORT)
