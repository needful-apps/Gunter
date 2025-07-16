import ipaddress
import json
import logging
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union, cast

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
    DB_FILE_PREFIX = "GeoLite2-City"
    DB_FILE_SUFFIX = ".mmdb"
    DB_DOWNLOAD_URL = "https://git.io/GeoLite2-City.mmdb"
    GITHUB_RELEASE_API_URL = (
        "https://api.github.com/repos/P3TERX/GeoLite.mmdb/releases/latest"
    )
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 6600
    SCHEDULER_UPDATE_DAYS = 1

    # Feature flags - can be controlled via environment variables
    ENABLE_STATUS_ENDPOINT = (
        os.environ.get("GUNTER_ENABLE_STATUS", "true").lower() == "true"
    )
    ENABLE_API_DOCS = os.environ.get("GUNTER_ENABLE_API_DOCS", "true").lower() == "true"


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("rich")

app = Flask(__name__)

# --- Initialize config first ---
config = Config()

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

# Always add the core functional namespaces
api.add_namespace(geo_ns)
api.add_namespace(whois_ns)

# Conditionally create and add the status namespace if enabled
if config.ENABLE_STATUS_ENDPOINT:
    status_ns = Namespace("status", description="Status endpoint")
    api.add_namespace(status_ns)

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
        """Downloads the GeoLite2 database, loads it, and cleans up old versions."""
        log.info("Attempting to download and load GeoLite2-City.mmdb...")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        new_db_filename = (
            f"{self.config.DB_FILE_PREFIX}-{timestamp}{self.config.DB_FILE_SUFFIX}"
        )
        new_db_filepath = os.path.join(os.getcwd(), new_db_filename)

        try:
            response = requests.get(
                self.config.DB_DOWNLOAD_URL, stream=True, timeout=60
            )
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            with Progress() as progress:
                task = progress.add_task(
                    "[cyan]Downloading GeoLite2-City.mmdb...", total=total_size
                )
                with open(new_db_filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))
            log.info(f"Successfully downloaded: {new_db_filepath}")

            if self.mmdb_reader:
                self.mmdb_reader.close()

            self.mmdb_reader = maxminddb.open_database(new_db_filepath)
            self.last_db_update_time = datetime.now()
            log.info(f"GeoLite2-City.mmdb successfully loaded from {new_db_filepath}.")

            self._cleanup_old_db_files(new_db_filepath)
            self.current_db_file_path = new_db_filepath

        except (
            requests.exceptions.RequestException,
            maxminddb.InvalidDatabaseError,
        ) as e:
            log.error(f"Error during database update: {e}")
            self.mmdb_reader = None
            self._cleanup_failed_download(new_db_filepath)
        except Exception as e:
            log.error(f"An unexpected error occurred: {e}")
            self.mmdb_reader = None
            self._cleanup_failed_download(new_db_filepath)

    def check_for_new_release_and_update(self):
        """Checks GitHub for a new version and updates if necessary."""
        log.info("Checking for new GeoLite2-City.mmdb releases on GitHub...")
        try:
            response = requests.get(self.config.GITHUB_RELEASE_API_URL, timeout=10)
            response.raise_for_status()
            latest_release = response.json()
            latest_tag = latest_release.get("tag_name")

            if not latest_tag:
                log.warning("Could not find 'tag_name' in the latest GitHub release.")
                return

            log.info(f"Latest GitHub release tag: {latest_tag}")
            if latest_tag != self.current_db_version_tag:
                log.info(
                    f"New release found! Current: {self.current_db_version_tag}, Latest: {latest_tag}"
                )
                self.current_db_version_tag = latest_tag
                self.download_and_load_database()
            else:
                log.info("GeoLite2-City.mmdb is already up to date.")
        except requests.exceptions.RequestException as e:
            log.error(f"Error checking GitHub releases: {e}")
        except json.JSONDecodeError:
            log.error("Error parsing GitHub API response.")

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
            # Die python-whois Bibliothek hat sich geändert, query existiert nicht mehr
            # Jetzt wird direkt whois() verwendet
            domain_info = whois.whois(domain)
            log.info(f"Domain WHOIS lookup for {domain} successful.")
            # Konvertiere das Ergebnis in ein serialisierbares Dictionary
            if domain_info:
                # Filtere und konvertiere Datumswerte
                info_dict: Dict[str, Union[str, List[str], Dict[str, Any], None]] = {}
                for k, v in domain_info.items():
                    if isinstance(v, datetime):
                        info_dict[k] = v.isoformat()
                    elif isinstance(v, list) and v and isinstance(v[0], datetime):
                        # Explizit die Liste von formatierten Zeitstempeln erstellen
                        formatted_dates = [item.isoformat() for item in v]
                        info_dict[k] = formatted_dates  # Explizite Zuweisung der Liste
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


# --- Helper Functions ---


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
        "target": fields.String(description="Target of the WHOIS query (IP or domain)"),
        "lookup_timestamp": fields.String(description="Query timestamp"),
        "ip_whois": fields.Raw(description="WHOIS data for IP addresses"),
        "domain_whois": fields.Raw(description="WHOIS data for domains"),
        "reverse_dns": fields.String(description="Reverse DNS result (if available)"),
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
        "registered_country": fields.Raw(description="Registered country information"),
        "database_info": fields.Raw(description="Database status information"),
        "whois_data": fields.Nested(
            whois_data_model, description="WHOIS data (optional)"
        ),
    },
)

# --- Service Initialization ---
db_manager = GeoDBManager(config)
whois_service = WhoisService()


@geo_ns.route("/<string:ip>")
@geo_ns.doc(
    params={"ip": "IP address for geolocation"},
    responses={
        200: "Success",
        400: "Invalid IP address",
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
    @geo_ns.marshal_with(geo_lookup_model, skip_none=True)
    def get(self, ip):
        """
        Performs a GeoLite2 IP lookup.
        Returns detailed geo information and optional WHOIS data.
        """
        if not db_manager.mmdb_reader:
            geo_ns.abort(
                503, error="GeoLite2 database not available. Please try again later."
            )

        try:
            record = db_manager.mmdb_reader.get(ip)
            if not record:
                geo_ns.abort(404, error="IP address not found in the database.")

            lang = request.args.get("lang", "de").lower()
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
                log.info(f"Including WHOIS data for IP: {ip}")
                processed_record["whois_data"] = whois_service.get_whois_data(ip)

            log.info(f"Lookup for IP: {ip}, Lang: {lang} successful.")
            return processed_record
        except ValueError:
            geo_ns.abort(400, error="Invalid IP address format.")
        except Exception as e:
            log.error(f"Error during IP lookup for {ip}: {e}")
            geo_ns.abort(500, error="An internal server error occurred.")


if config.ENABLE_STATUS_ENDPOINT:

    @status_ns.route("")
    class Status(Resource):
        @status_ns.marshal_with(database_status_model)
        def get(self):
            """API endpoint to retrieve the current status of the GeoLite2 database."""
            return db_manager.get_status()


@whois_ns.route("/<string:target>")
@whois_ns.doc(
    params={"target": "IP address or domain name for the WHOIS query"},
    responses={200: "Success", 500: "Internal server error"},
)
class WhoisLookup(Resource):
    @whois_ns.marshal_with(whois_data_model, skip_none=True)
    def get(self, target):
        """
        API endpoint for a WHOIS lookup for an IP or domain.
        Provides detailed WHOIS information and, if an IP address is specified, reverse DNS data.
        """
        try:
            whois_data = whois_service.get_whois_data(target)
            return whois_data
        except Exception as e:
            log.error(f"Error during WHOIS lookup for {target}: {e}")
            whois_ns.abort(500, error="An internal server error occurred.")


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=db_manager.check_for_new_release_and_update,
    trigger="interval",
    days=config.SCHEDULER_UPDATE_DAYS,
    id="daily_db_update",
)

if __name__ == "__main__":
    log.info("Performing initial database download on startup...")
    db_manager.download_and_load_database()
    log.info("Initial database load complete.")

    scheduler.start()
    log.info(
        f"Scheduler started. Checking every {config.SCHEDULER_UPDATE_DAYS} day(s)."
    )

    log.info(
        f"Starting Flask app with Waitress on http://{config.FLASK_HOST}:{config.FLASK_PORT}"
    )
    serve(app, host=config.FLASK_HOST, port=config.FLASK_PORT)
