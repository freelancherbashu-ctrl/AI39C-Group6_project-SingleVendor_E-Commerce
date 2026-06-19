import os


class Config:
    """Base configuration for the application."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MangoMan@2064",)
    MYSQL_DB = os.environ.get("MYSQL_DB", "single_vendor_ecommerce")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))

    SESSION_TYPE = "filesystem"
