# Gunter

[![Python Version](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)
[![needful-apps](https://img.shields.io/badge/by-needful--apps-008080)](https://needful-apps.de)

Gunter is a simple Flask-based web service that provides geolocation and WHOIS information for IP addresses and domains. It automatically downloads and keeps the GeoLite2-City database updated. Developed by [needful-apps](https://needful-apps.de).

## Features

-   **Geo-IP Lookup**: Get detailed geolocation data for any IP address.
-   **WHOIS Lookup**: Perform WHOIS queries for both IP addresses and domain names.
-   **Reverse DNS**: Resolve IP addresses to hostnames.
-   **Automatic Database Updates**: The service regularly checks for and downloads the latest GeoLite2 database from a public repository.
-   **Simple API**: Easy-to-use JSON API endpoints.

## Installation

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

-   `GET /api/geo-lookup/<ip>`: Retrieves geolocation data for the given IP.
    -   Query Parameters:
        -   `lang`: Language for the response (e.g., `en`, `de`, `fr`). Defaults to `de`.
        -   `exclude_whois`: Set to `true` to omit WHOIS data from the response.

-   `GET /api/whois/<target>`: Retrieves WHOIS data for an IP address.

-   `GET /api/status`: Shows the current status of the GeoLite2 database.

## Example Usage

```bash
# Geo-lookup for an IP
curl http://localhost:6600/api/geo-lookup/8.8.8.8

# WHOIS lookup for an IP
curl http://localhost:6600/api/whois/8.8.8.8
```

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for details on how to get started.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

---

Developed with ❤️ by [Needful Apps](https://needful-apps.de)
