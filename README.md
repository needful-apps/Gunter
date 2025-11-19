# Gunter

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
[![needful-apps](https://img.shields.io/badge/by-needful--apps-008080)](https://needful-apps.de)

Gunter is a simple Flask-based web service that provides geolocation and WHOIS information for IP addresses and domains. It automatically downloads and keeps the GeoLite2-City database updated.

Developed by [needful-apps](https://needful-apps.de).

## Table of Contents

- [Features](#features)
- [Installation](#installation)
  - [Docker/Podman (Recommended)](#dockerpodman-recommended)
  - [Local Installation](#local-installation)
  - [Docker Compose](#docker-compose)
- [API Usage](#api-usage)
  - [Endpoints](#endpoints)
  - [Example Requests](#example-requests)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Database Options](#database-options)
- [Legal Notice](#legal-notice)

## Features

- **Geo-IP Lookup**: Get detailed geolocation data for any IP address
- **WHOIS Lookup**: Perform WHOIS queries for both IP addresses and domain names
- **Reverse DNS**: Resolve IP addresses to hostnames
- **Automatic Database Updates**: Regularly checks for and downloads the latest GeoLite2 database
- **Flexible Database Sources**: Support for MaxMind, custom MMDB files, or external URLs
- **CORS Support**: Configurable Cross-Origin Resource Sharing
- **API Documentation**: Built-in Swagger UI for API exploration

## Installation

### Docker/Podman (Recommended)

For quick setup, you can run Gunter using Docker or Podman. You'll need a free MaxMind license key, which you can obtain from [MaxMind](https://www.maxmind.com/en/geolite2/signup).

**Docker:**
```bash
# Download container
docker pull ghcr.io/needful-apps/gunter:latest

# Start container with MaxMind license key
docker run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter \
  ghcr.io/needful-apps/gunter:latest

# Start container with persistent data
docker run -d -p 6600:6600 \
  -v gunter_data:/data \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter \
  ghcr.io/needful-apps/gunter:latest
```

**Podman:**
```bash
# Download container
podman pull ghcr.io/needful-apps/gunter:latest

# Start container with MaxMind license key
podman run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter \
  ghcr.io/needful-apps/gunter:latest

# Start container with persistent data
podman run -d -p 6600:6600 \
  -v gunter_data:/data:Z \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter \
  ghcr.io/needful-apps/gunter:latest
```

The server will be available at `http://localhost:6600`.

### Local Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:needful-apps/Gunter.git
   cd Gunter
   ```

2. **Install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```
   The server will start on `http://0.0.0.0:6600`. The first run will download the GeoLite2 database.

**For development:**
```bash
pip install -r requirements-dev.txt

# Format code with Black and isort
./scripts/format_code.sh

# Or install pre-commit hooks
pre-commit install
```

For detailed information about code formatting, see [FORMATTING.md](FORMATTING.md).

### Docker Compose

```bash
# Start the service
docker-compose up -d

# Start the service with tests
docker-compose up test
```

## API Usage

### Endpoints

- **`GET /api/geo-lookup/<ip>`** - Retrieves geolocation data for the given IP
  - Query Parameters:
    - `lang`: Language for the response (e.g., `en`, `de`, `fr`). Defaults to configured language.
    - `exclude_whois`: Set to `true` to omit WHOIS data from the response.

- **`GET /api/whois/<target>`** - Retrieves WHOIS data for an IP address or domain

- **`GET /api/status`** - Shows the current status of the GeoLite2 database (can be disabled via configuration)

- **`GET /api/docs`** - Interactive Swagger UI for API exploration (can be disabled via configuration)

### Example Requests

```bash
# Geo-lookup for an IP
curl http://localhost:6600/api/geo-lookup/8.8.8.8

# Geo-lookup in German
curl http://localhost:6600/api/geo-lookup/8.8.8.8?lang=de

# Geo-lookup without WHOIS data
curl http://localhost:6600/api/geo-lookup/8.8.8.8?exclude_whois=true

# WHOIS query for an IP
curl http://localhost:6600/api/whois/8.8.8.8

# Geo-lookup for a domain
curl http://localhost:6600/api/geo-lookup/example.com
```

You can also explore and test the API using the built-in Swagger UI at `http://localhost:6600/api/docs`.

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GUNTER_MAXMIND_LICENSE_KEY` | Your MaxMind license key for downloading GeoLite2 database | - | Recommended |
| `GUNTER_DB_FILE` | Path to a custom MMDB database file | - | No |
| `GUNTER_DB_URL` | URL to an external MMDB database (http, https, ftp, ftps) | - | No |
| `GUNTER_LANG` | Default language for API responses (`en`, `de`, `fr`, etc.) | `de` | No |
| `GUNTER_CORS_ORIGINS` | Comma-separated list of allowed CORS origins (use `*` for all) | - | No |
| `GUNTER_ENABLE_STATUS` | Enable/disable the `/api/status` endpoint | `true` | No |
| `GUNTER_ENABLE_API_DOCS` | Enable/disable the `/api/docs` endpoint | `true` | No |

**Examples:**

```bash
# Set language to English
docker run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_key \
  -e GUNTER_LANG=en \
  --name gunter ghcr.io/needful-apps/gunter:latest

# Enable CORS for specific origins
docker run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_key \
  -e GUNTER_CORS_ORIGINS=https://example.com,https://another.site \
  --name gunter ghcr.io/needful-apps/gunter:latest

# Enable CORS for all origins
docker run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_key \
  -e GUNTER_CORS_ORIGINS=* \
  --name gunter ghcr.io/needful-apps/gunter:latest
```

### Database Options

Gunter supports multiple database sources with the following priority:

1. **External URL** (`GUNTER_DB_URL`) - Highest priority
2. **Custom local file** (`GUNTER_DB_FILE`) - Medium priority
3. **MaxMind GeoLite2** (`GUNTER_MAXMIND_LICENSE_KEY`) - Default option

**Using a custom MMDB file:**
```bash
docker run -d -p 6600:6600 \
  -v $(pwd)/data:/data \
  -e GUNTER_DB_FILE=/data/dbip-city-isp.mmdb \
  --name gunter ghcr.io/needful-apps/gunter:latest
```

**Using an external URL:**
```bash
docker run -d -p 6600:6600 \
  -e GUNTER_DB_URL=https://example.com/your.mmdb \
  --name gunter ghcr.io/needful-apps/gunter:latest
```

**Notes:**
- Custom local files (`GUNTER_DB_FILE`) do not auto-update
- External URLs (`GUNTER_DB_URL`) are re-downloaded on scheduled updates
- MaxMind databases are automatically updated when using `GUNTER_MAXMIND_LICENSE_KEY`

## Legal Notice

By default, this application automatically downloads and uses the free MaxMind GeoLite2 database. See the [MaxMind license](https://www.maxmind.com/en/geolite2/eula) for terms of use.

**Important:**
- No third-party or commercial databases (other than MaxMind GeoLite2) are included or distributed with this software
- It is your responsibility to ensure you have the appropriate license and rights to use any external database you provide
- The maintainers of this project do not provide, redistribute, or assume liability for the use of any external or commercial GeoIP databases

---

**License:** MIT  
**Developed by:** [needful-apps](https://needful-apps.de)
