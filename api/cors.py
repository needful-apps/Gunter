"""CORS handling middleware."""

import os

from flask import Flask, jsonify, request


def setup_cors(app: Flask) -> None:
    """
    Configure CORS handling for the Flask application.

    Args:
        app: The Flask application instance.
    """

    @app.after_request
    def after_request(response):
        cors_origins = os.environ.get("GUNTER_CORS_ORIGINS")
        if cors_origins:
            origin = request.headers.get("Origin")
            if origin:
                if cors_origins == "*":
                    response.headers["Access-Control-Allow-Origin"] = "*"
                else:
                    allowed_origins = [o.strip() for o in cors_origins.split(",")]
                    if origin in allowed_origins:
                        response.headers["Access-Control-Allow-Origin"] = origin

                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, "
                    "Access-Control-Request-Method, Access-Control-Request-Headers"
                )
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            cors_origins = os.environ.get("GUNTER_CORS_ORIGINS")
            if cors_origins:
                origin = request.headers.get("Origin")
                response = jsonify()
                response.status_code = 200
                if origin:
                    if cors_origins == "*":
                        response.headers["Access-Control-Allow-Origin"] = "*"
                    else:
                        allowed_origins = [o.strip() for o in cors_origins.split(",")]
                        if origin in allowed_origins:
                            response.headers["Access-Control-Allow-Origin"] = origin

                    response.headers["Access-Control-Allow-Methods"] = (
                        "GET, POST, PUT, DELETE, OPTIONS"
                    )
                    response.headers["Access-Control-Allow-Headers"] = (
                        "Content-Type, Authorization, "
                        "Access-Control-Request-Method, Access-Control-Request-Headers"
                    )
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                return response
        return None
