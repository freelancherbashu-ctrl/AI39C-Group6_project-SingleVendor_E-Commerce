from flask import Blueprint, make_response
from app.controllers.auth import AuthController

auth_bp    = Blueprint("auth", __name__)
controller = AuthController()

# Auth
@auth_bp.route("/login",    methods=["GET", "POST"])
def login():      return controller.login()

@auth_bp.route("/register", methods=["GET", "POST"])
def register():   return controller.register()

@auth_bp.route("/logout")
def logout():     return controller.logout()

# Profile
@auth_bp.route("/profile")
def profile():    return controller.profile()

@auth_bp.route("/profile/edit",            methods=["GET", "POST"])
def edit_profile():    return controller.edit_profile()

@auth_bp.route("/profile/upload_picture",  methods=["POST"])
def upload_picture():  return controller.upload_picture()

@auth_bp.route("/profile/change_password", methods=["GET", "POST"])
def change_password(): return controller.change_password()

@auth_bp.route("/forgot_password",         methods=["GET", "POST"])
def forgot_password(): return controller.forgot_password()

@auth_bp.route("/reset_password/<token>",  methods=["GET", "POST"])
def reset_password(token): return controller.reset_password(token)

# Pages
@auth_bp.route("/")
@auth_bp.route("/home", methods=["GET"])
def home():  return controller.home()

@auth_bp.route("/all_categories")
def all_categories(): return controller.all_categories()

@auth_bp.route("/single_category/<category>")
def single_category(category): return controller.single_category(category)

@auth_bp.route("/view_product/<int:id>")
def view_product(id): return controller.view_product(id)

@auth_bp.route("/view_product/<int:id>/json")
def view_product_json(id): return controller.view_product_json(id)

@auth_bp.route("/categories/json")
def categories_json(): return controller.categories_json()

# Cart
@auth_bp.route("/cart")
def cart(): return controller.cart()

@auth_bp.route("/cart/add/<int:product_id>",    methods=["POST"])
def add_to_cart(product_id): return controller.add_to_cart(product_id)

@auth_bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id): return controller.update_cart(product_id)

@auth_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id): return controller.remove_from_cart(product_id)

# Buy Now
@auth_bp.route("/buy_now/<int:product_id>", methods=["POST"])
def buy_now(product_id): return controller.buy_now(product_id)

# Checkout
@auth_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    response = make_response(controller.checkout())
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

@auth_bp.route("/place_order", methods=["POST"])
def place_order(): return controller.place_order()

@auth_bp.route("/order_confirmed/<int:order_id>")
def order_confirmed(order_id): return controller.order_confirmed(order_id)

@auth_bp.route("/payment/<method>")
def payment(method): return controller.payment(method)

@auth_bp.route("/payment/submit", methods=["POST"])
def submit_payment(): return controller.submit_payment()

@auth_bp.route("/view_my_orders")
def view_my_orders(): return controller.view_my_orders()

@auth_bp.route("/cancel_order/<int:order_id>", methods=["POST"])
def cancel_order(order_id): return controller.cancel_order(order_id)

@auth_bp.route("/order_details/<int:order_id>")
def order_details(order_id): return controller.order_details(order_id)

@auth_bp.route("/search/suggest")
def search_suggest(): return controller.search_suggest()


@auth_bp.route("/order_details/<int:order_id>/json")
def order_details_json(order_id): return controller.order_details_json(order_id)

# Wishlist
@auth_bp.route("/wishlist")
def wishlist(): return controller.view_wishlist()

@auth_bp.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
def toggle_wishlist(product_id): return controller.toggle_wishlist(product_id)

@auth_bp.route("/wishlist/status/<int:product_id>")
def wishlist_status(product_id): return controller.wishlist_status(product_id)

# OTP
@auth_bp.route("/verify_otp", methods=["GET", "POST"])
def verify_otp(): return controller.verify_otp()

# Reviews
@auth_bp.route("/product/<int:product_id>/review", methods=["POST"])
def submit_review(product_id): return controller.submit_review(product_id)

# Coupons
@auth_bp.route("/coupon/validate", methods=["POST"])
def validate_coupon(): return controller.validate_coupon()

# Refunds
@auth_bp.route("/order/<int:order_id>/refund", methods=["POST"])
def request_refund(order_id): return controller.request_refund(order_id)

@auth_bp.route("/my_refunds")
def my_refunds(): return controller.my_refunds()