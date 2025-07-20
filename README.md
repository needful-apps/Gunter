# Gunter

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
[![needful-apps](https://img.shields.io/badge/by-needful--apps-008080)](https://needful-apps.de)

Gunter is a simple Flask-based web service that provides geolocation and WHOIS information for IP addresses and domains. It automatically downloads and keeps the GeoLite2-City database updated. Developed by [needful-apps](https://needful-apps.de).

## Features

- **Geo-IP Lookup**: Get detailed geolocation data for any IP address.
- **WHOIS Lookup**: Perform WHOIS queries for both IP addresses and domain names.
- **Reverse DNS**: Resolve IP addresses to hostnames.
- **Automatic Database Updates**: The service regularly checks for and downloads the latest GeoLite2 database from a public repository.
- **Simple API**: Easy-to-use JSON API endpoints.
- **OpenAPI Documentation**: Interactive API documentation with Swagger UI for easy exploration and testing.

## Installation

### Option 1: Container (recommended)

1. **Docker:**
    ```bash
    # Download container
    docker pull ghcr.io/needful-apps/gunter:latest

    # Start container
    docker run -d -p 6600:6600 --name gunter ghcr.io/needful-apps/gunter:latest

    # Start container with persistent data
    docker run -d -p 6600:6600 -v gunter_data:/data --name gunter ghcr.io/needful-apps/gunter:latest
    ```

2. **Podman:**
    ```bash
    # Download container
    podman pull ghcr.io/needful-apps/gunter:latest

    # Start container
    podman run -d -p 6600:6600 --name gunter ghcr.io/needful-apps/gunter:latest

    # Start container with persistent data
    podman run -d -p 6600:6600 -v gunter_data:/data:Z --name gunter ghcr.io/needful-apps/gunter:latest
    ```

The server will then be available at `http://localhost:6600`.

### Option 2: Local Installation

1.  **Clone the repository:**
  ```bash
  git clone git@github.com:needful-apps/Gunter.git
  cd Gunter
  ```

2.  **Install dependencies:**
  It's recommended to use a virtual environment.
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows use `venv\Scripts\activate`
  pip install -r requirements.txt

  # For development:
  pip install -r requirements-dev.txt
  ```

3.  **Code-Formatting and Quality:**
  ```bash
  # Format code with Black and isort
  ./scripts/format_code.sh

  # Or install pre-commit hooks for automatic formatting
  pre-commit install
  ```
  For detailed information about code formatting, see [FORMATTING.md](FORMATTING.md).

4.  **Run the application:**
  ```bash
  python app.py
  ```
  The server will start on `http://0.0.0.0:6600`. The first run will download the GeoLite2 database, which may take a moment.

## API Endpoints

- `GET /api/geo-lookup/<ip>`: Retrieves geolocation data for the given IP.
  - Query Parameters:
    - `lang`: Language for the response (e.g., `en`, `de`, `fr`). Defaults to `de`.
    - `exclude_whois`: Set to `true` to omit WHOIS data from the response.

- `GET /api/whois/<target>`: Retrieves WHOIS data for an IP address.

- `GET /api/status`: Shows the current status of the GeoLite2 database. (Can be disabled via configuration)

- `GET /api/docs`: OpenAPI/Swagger documentation interface for exploring and testing the API. (Can be disabled via configuration)

## Example Usage

```bash
# Geo-lookup for an IP
curl http://localhost:6600/api/geo-lookup/8.8.8.8

# WHOIS query for an IP
curl http://localhost:6600/api/whois/8.8.8.8

# Geo-lookup for a domain
curl http://localhost:6600/api/geo-lookup/example.com

# Check GeoLite2 database status
curl http://localhost:6600/api/status
```

You can also explore and test the API using the built-in Swagger UI by accessing `http://localhost:6600/api/docs` in your browser (if the API docs are enabled).

### Docker-Compose

Alternatively, the service can be started with Docker Compose:

```bash
# Start the service
docker-compose up -d

# Start the service with tests
docker-compose up test

# Continuous test execution (test watch)
docker-compose up test-watch
```

## Configuration Options

The service can be configured using the following environment variables:

- `GUNTER_ENABLE_STATUS`: Controls whether the `/api/status` endpoint is enabled. Set to `false` to disable. Default: `true`.
- `GUNTER_ENABLE_API_DOCS`: Controls whether the OpenAPI documentation at `/api/docs` is enabled. Set to `false` to disable. Default: `true`.
- `GUNTER_LANG`: Sets the default language for all API responses (e.g. `en`, `de`, `fr`). If not set, defaults to `de`. This can be overridden per request using the `?lang=` query parameter.
- `GUNTER_DB_FILE`: (optional) Path to a custom MMDB database file (e.g. from db-ip.com). If set, this file will be used instead of the default MaxMind GeoLite2 database. Example: `-e GUNTER_DB_FILE=/data/dbip-city-isp.mmdb`
- `GUNTER_DB_URL`: (optional, recommended for automation) URL to an external MMDB database (supports http, https, ftp, ftps). If set, the database will be downloaded from this source at startup and on every scheduled update. Example: `-e GUNTER_DB_URL=https://example.com/your.mmdb`

### Example: Setting environment variables

```bash
# Docker (set default language to English)
docker run -d -p 6600:6600 -e GUNTER_ENABLE_STATUS=false -e GUNTER_ENABLE_API_DOCS=false -e GUNTER_LANG=en --name gunter ghcr.io/needful-apps/gunter:latest

# Podman (set default language to French)
podman run -d -p 6600:6600 -e GUNTER_ENABLE_STATUS=false -e GUNTER_ENABLE_API_DOCS=false -e GUNTER_LANG=fr --name gunter ghcr.io/needful-apps/gunter:latest
```


### Example: Using a custom or external MMDB database

You may use your own GeoIP database files (e.g. commercial or custom MMDB files such as those from db-ip.com) by placing them in the data directory or mounting them as a volume. To use a specific file, set the `GUNTER_DB_FILE` environment variable to the path of your MMDB file.

```bash
# Mount your own db-ip.com MMDB file and set the environment variable
docker run -d -p 6600:6600 -v $(pwd)/data:/data -e GUNTER_DB_FILE=/data/dbip-city-isp.mmdb --name gunter-custom gunter-local
```

Alternatively, you can provide a direct download URL (http, https, ftp, ftps) for your MMDB file. This is useful for automated updates from a remote source:

```bash
# Download and use an external MMDB file from a URL (checked on every update)
docker run -d -p 6600:6600 -e GUNTER_DB_URL=https://example.com/your.mmdb --name gunter-external gunter-local
```

**Note:**
- If you use a custom MMDB database via `GUNTER_DB_FILE`, no updates or downloads of the MaxMind GeoLite2 database will be performed. The application will exclusively use the specified file and will not check for new versions of the MaxMind database.
- If you use an external URL via `GUNTER_DB_URL`, this source takes precedence over `GUNTER_DB_FILE` and the MaxMind GeoLite2 database. The file will be downloaded at startup and on every scheduled update.

---

## Legal Notice on External GeoIP Databases

By default, this application automatically downloads and uses the free MaxMind GeoLite2 database (see [MaxMind license](https://www.maxmind.com/en/geolite2/eula)).

**No third-party or commercial databases (other than MaxMind GeoLite2) are included or distributed with this software.**

**It is your responsibility to ensure you have the appropriate license and rights to use any external database you provide.**

The maintainers of this project do not provide, redistribute, or assume liability for the use of any external or commercial GeoIP databases.
