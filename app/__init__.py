import os
from flask import Flask
from app.extensions import mysql, mail

def create_app():
    app = Flask(__name__)
    app.config.from_object("config")

    # Allow OAuth over HTTP for local development (http://127.0.0.1).
    # Remove this line when deploying to a real HTTPS server.
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    mysql.init_app(app)
    mail.init_app(app)

    from app.routes.authroute import auth_bp
    from app.routes.googleroute import create_google_blueprint, google_callback_bp
    from app.routes.admin_routes import admin_bp

    google_auth_bp = create_google_blueprint(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(google_auth_bp, url_prefix="/login")
    app.register_blueprint(google_callback_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from app.models.order import Order
        from app.models.user import User
        from app.models.wishlist import Wishlist
        from app.models.admin import Admin
        from app.models.product import Product
        from app.models.category import Category
        from app.models.flash_sale import FlashSale

        User.init_table(mysql)
        Order.init_table(mysql)
        Wishlist.init_table(mysql)
        Admin.init_table(mysql)
        Product.init_table(mysql)
        Category.init_table(mysql)
        FlashSale.init_table(mysql)

        # Seed default data on first run
        Category.seed(mysql)
        Product.seed(mysql)

    return app