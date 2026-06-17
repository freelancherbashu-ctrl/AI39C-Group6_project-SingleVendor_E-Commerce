import os

# Base directory of the project (folder containing config.py)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration — shared by all environments."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")

    # ===== MySQL connection =====
    # Format: mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:Bips231%2312@localhost:3306/meropasal_admin"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pool tuning for MySQL (keeps connections healthy)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # File uploads
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "admin", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # In production, override SECRET_KEY and DATABASE_URL via environment variables


# Lookup dictionary so create_app() can pick a config by name
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}