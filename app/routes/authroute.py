from flask import Blueprint
from app.controllers.auth import AuthController

auth_bp = Blueprint("auth", __name__)
controller = AuthController()


@auth_bp.route("/all_categories", methods=["GET"])
def all_categories():
    return controller.all_categories()


@auth_bp.route("/cart", methods=["GET"])
def cart():
    return controller.cart()

@auth_bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    return controller.add_to_cart(product_id)

@auth_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    return controller.update_cart(product_id)

@auth_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    return controller.remove_from_cart(product_id)

@auth_bp.route("/dashboard", methods=["GET"])
def dashboard():
    return controller.dashboard()


@auth_bp.route("/order_details", methods=["GET"])
def order_details():
    return controller.order_details()


@auth_bp.route("/profile", methods=["GET"])
def profile():
    return controller.profile()


@auth_bp.route("/single_category/<category>", methods=["GET"])
def single_category(category):
    return controller.single_category(category)


@auth_bp.route("/view_my_orders", methods=["GET"])
def view_my_orders():
    return controller.view_my_orders()


@auth_bp.route("/view_product/<int:id>")
def view_product(id):
    return controller.view_product(id)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    return controller.login()

@auth_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    return controller.checkout()

