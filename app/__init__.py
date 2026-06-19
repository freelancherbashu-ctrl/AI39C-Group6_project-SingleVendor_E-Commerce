from flask import Flask
from config import Config
from app.models.database import Database
from app.routes.category_routes import category_bp
from app.routes.product_routes import product_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    with app.app_context():
        Database.create_tables()
    
    app.register_blueprint(category_bp)
    app.register_blueprint(product_bp)
    
    return app