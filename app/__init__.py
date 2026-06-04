from flask import Flask
from app.models.database import db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meropasal.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    db.init_app(app)

    from app.models import user_models
    from app.models import product_models

    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    return app