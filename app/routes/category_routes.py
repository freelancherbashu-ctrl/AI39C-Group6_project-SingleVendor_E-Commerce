from flask import Blueprint
from app.controllers.category_controller import CategoryController

category_bp = Blueprint('category', __name__)
controller = CategoryController()

@category_bp.route('/add-category', methods=['GET', 'POST'])
def add_category():
    return controller.add_category()

@category_bp.route('/categories')
def categories_list():
    return controller.list_categories()