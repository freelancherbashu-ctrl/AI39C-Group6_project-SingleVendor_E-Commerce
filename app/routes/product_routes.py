# from flask import Blueprint
# from app.controllers.product_controller import ProductController

# product_bp = Blueprint('product', __name__)
# controller = ProductController()

# @product_bp.route('/add-product/<int:category_id>', methods=['GET', 'POST'])
# def add_product(category_id):
#     return controller.add_product(category_id)

# @product_bp.route('/products')
# def products_list():
#     return controller.products_list()




from flask import Blueprint
from app.controllers.product_controller import (
    list_products,
    add_product,
    edit_product,
    delete_product
)

product_bp = Blueprint('product', __name__)

# Routes
product_bp.route('/products')(list_products)
product_bp.route('/products/add', methods=['GET', 'POST'])(add_product)
product_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])(edit_product)
product_bp.route('/products/delete/<int:product_id>', methods=['POST'])(delete_product)