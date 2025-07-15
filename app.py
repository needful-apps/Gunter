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


# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
)
log = logging.getLogger("rich")

app = Flask(__name__)

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


# --- Service Initialization ---
config = Config()
db_manager = GeoDBManager(config)
whois_service = WhoisService()

# --- Flask API Endpoints ---


@app.route("/api/geo-lookup/<ip>", methods=["GET"])
def geo_lookup(ip: str):
    """
    API endpoint for a GeoLite2 IP lookup.
    Accepts 'lang' and 'exclude_whois' as query parameters.
    """
    if not db_manager.mmdb_reader:
        return (
            jsonify(
                {"error": "GeoLite2 database not available. Please try again later."}
            ),
            503,
        )

    try:
        record = db_manager.mmdb_reader.get(ip)
        if not record:
            return jsonify({"error": "IP address not found in the database."}), 404

        lang = request.args.get("lang", "de").lower()
        # Ensure we're working with a dictionary that can be modified
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
        return jsonify(processed_record)
    except ValueError:
        return jsonify({"error": "Invalid IP address format."}), 400
    except Exception as e:
        log.error(f"Error during IP lookup for {ip}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    """API endpoint to get the current status of the GeoLite2 database."""
    return jsonify(db_manager.get_status())


@app.route("/api/whois/<target>", methods=["GET"])
def whois_lookup(target: str):
    """API endpoint for a WHOIS lookup for an IP or domain."""
    try:
        whois_data = whois_service.get_whois_data(target)
        return jsonify(whois_data)
    except Exception as e:
        log.error(f"Error during WHOIS lookup for {target}: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


# --- Scheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=db_manager.check_for_new_release_and_update,
    trigger="interval",
    days=config.SCHEDULER_UPDATE_DAYS,
    id="daily_db_update",
)

# --- Application Start ---
if __name__ == "__main__":
    log.info("Performing initial database download on startup...")
    db_manager.download_and_load_database()
    log.info("Initial database load complete.")

    scheduler.start()
    log.info(
        f"Scheduler started. Checking every {config.SCHEDULER_UPDATE_DAYS} day(s)."
    )

    # Waitress is a production-ready WSGI server used directly here.
    # It's a simple alternative to Gunicorn without needing an external process.
    log.info(
        f"Starting Flask app with Waitress on http://{config.FLASK_HOST}:{config.FLASK_PORT}"
    )
    serve(app, host=config.FLASK_HOST, port=config.FLASK_PORT)
