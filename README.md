Gunter
Gunter is a simple Flask-based web service that provides geolocation and WHOIS information for IP addresses and domains. It automatically downloads and keeps the GeoLite2-City database updated.

Developed by needful-apps
Python Version: Latest compatible with Flask
License: MIT
PRs Welcome!

📚 Table of Contents
Features

Installation

Using Docker (Recommended)

Using Podman

Local Installation

Running the App

API Endpoints

Configuration

Examples

Legal Notice on External GeoIP Databases

🚀 Features
Geo-IP Lookup: Get detailed geolocation data for any IP address.

WHOIS Lookup: Perform WHOIS queries for IP addresses and domain names.

Reverse DNS: Resolve IP addresses to hostnames.

Automatic Database Updates: Keeps GeoLite2 database up to date.

Swagger UI: API documentation via browser interface.

Easy Containerized Setup: Supports Docker, Podman, and Compose.

⚙️ Installation
Using Docker (Recommended)
bash
Copy
Edit
# Pull image
docker pull ghcr.io/needful-apps/gunter:latest

# Run with MaxMind license key
docker run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter ghcr.io/needful-apps/gunter:latest

# Persistent volume
docker run -d -p 6600:6600 \
  -v gunter_data:/data \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter ghcr.io/needful-apps/gunter:latest
Using Podman
bash
Copy
Edit
# Pull image
podman pull ghcr.io/needful-apps/gunter:latest

# Run with MaxMind license key
podman run -d -p 6600:6600 \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter ghcr.io/needful-apps/gunter:latest

# Persistent volume
podman run -d -p 6600:6600 \
  -v gunter_data:/data:Z \
  -e GUNTER_MAXMIND_LICENSE_KEY=your_maxmind_license_key \
  --name gunter ghcr.io/needful-apps/gunter:latest
Local Installation
bash
Copy
Edit
# Clone repo
git clone https://github.com/needful-apps/Gunter.git
cd Gunter

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
Formatting Code (Optional)
bash
Copy
Edit
# Format using Black and isort
./scripts/format_code.sh

# Or install pre-commit hook
pre-commit install
▶️ Running the App
bash
Copy
Edit
python app.py
Runs on: http://0.0.0.0:6600

First startup will fetch the GeoLite2 database.

📡 API Endpoints
GET /api/geo-lookup/<ip_or_domain>
Returns geolocation + WHOIS data.

Query Parameters:

lang: Language code (e.g. en, de, fr). Default: en

exclude_whois: Set to true to skip WHOIS

GET /api/whois/<target>
Returns WHOIS info for IP/domain.

GET /api/status
Returns GeoLite2 database update status.
(Can be disabled via config)

API Documentation
Swagger UI: http://localhost:6600/api/docs

🧩 Configuration
Configure the service using environment variables:

Variable	Description	Default
GUNTER_ENABLE_STATUS	Enable /api/status endpoint	true
GUNTER_ENABLE_API_DOCS	Enable Swagger UI at /api/docs	true
GUNTER_LANG	Default language for responses (en, de, fr, etc.)	de
GUNTER_MAXMIND_LICENSE_KEY	MaxMind license key for GeoLite2 download	(Required for automatic DB)
GUNTER_DB_FILE	Path to a local .mmdb file	None
GUNTER_DB_URL	URL to external .mmdb file	None

Priority of databases:

GUNTER_DB_URL (highest)

GUNTER_DB_FILE

MaxMind GeoLite2 (if license key provided)

🧪 Examples
Geo Lookup
bash
Copy
Edit
curl http://localhost:6600/api/geo-lookup/8.8.8.8
WHOIS Lookup
bash
Copy
Edit
curl http://localhost:6600/api/whois/example.com
Using Docker with Custom MMDB
bash
Copy
Edit
docker run -d -p 6600:6600 \
  -v $(pwd)/data:/data \
  -e GUNTER_DB_FILE=/data/dbip-city-isp.mmdb \
  --name gunter-custom gunter-local
Using External MMDB URL
bash
Copy
Edit
docker run -d -p 6600:6600 \
  -e GUNTER_DB_URL=https://example.com/your.mmdb \
  --name gunter-external gunter-local
🧷 Docker Compose
bash
Copy
Edit
# Start service
docker-compose up -d

# Run with tests
docker-compose up test
⚖️ Legal Notice on External GeoIP Databases
This application includes automatic downloading of the free MaxMind GeoLite2 database (see MaxMind EULA).

No third-party or commercial databases are bundled or distributed.

You are responsible for having valid licenses for any external .mmdb files you provide.

The maintainers do not assume liability for misuse or licensing violations.

