from flask import Blueprint, redirect, url_for
from app.controllers.category_controller import CategoryController

category_bp = Blueprint('category', __name__)
controller = CategoryController()

@category_bp.route('/')
def home():
    return redirect(url_for('category.categories_list'))

@category_bp.route('/categories')
def categories_list():
    return controller.list_categories()

@category_bp.route('/add-category', methods=['GET', 'POST'])
def add_category():
    return controller.add_category()

@category_bp.route('/delete-category/<int:id>')
def delete_category(id):
    return controller.delete_category(id)