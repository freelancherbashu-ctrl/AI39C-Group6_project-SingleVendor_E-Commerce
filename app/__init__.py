from flask import Flask
from app.models.database import db
from config import config


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    # Import models so SQLAlchemy knows about them
    from app.models import settings_model  # noqa: F401

    from app.models import user_models
    from app.models import product_models

    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    return app