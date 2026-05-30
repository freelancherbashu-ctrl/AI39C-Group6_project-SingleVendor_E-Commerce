from flask import Blueprint
from app.controllers.product_controller import ProductController

product_bp = Blueprint('product', __name__)
controller = ProductController()

@product_bp.route('/add-product/<int:category_id>', methods=['GET', 'POST'])
def add_product(category_id):
    return controller.add_product(category_id)

@product_bp.route('/products')
def products_list():
    return controller.products_list()