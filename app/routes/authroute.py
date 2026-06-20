from flask import Blueprint
from app.controllers.auth import AuthController

from app.auth import login_required, admin_required

class AuthRoutes:

    def __init__(self):

        self.bp = Blueprint("authroutes", __name__)
        self.controller = AuthController()

    def register(self):

        # ---------------- AUTH ROUTES ----------------
        self.bp.route("/login", methods=["GET", "POST"])(
            self.controller.login
        )

@auth_bp.route("/profile/upload_picture",  methods=["POST"])
def upload_picture():  return controller.upload_picture()

@auth_bp.route("/profile/change_password", methods=["GET", "POST"])
def change_password(): return controller.change_password()

@auth_bp.route("/forgot_password",         methods=["GET", "POST"])
def forgot_password(): return controller.forgot_password()

@auth_bp.route("/verify_otp",              methods=["GET", "POST"])
def verify_otp(): return controller.verify_otp()

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


 

        # ---------------- RESET FLOW ----------------
        self.bp.route("/forgot-password", methods=["GET", "POST"])(
            self.controller.forgot_password
        )

        self.bp.route("/reset_password/<token>", methods=["GET", "POST"])(
            self.controller.reset_password
        )

@auth_bp.route("/wishlist/status/<int:product_id>")
def wishlist_status(product_id): return controller.wishlist_status(product_id)
# Reviews
@auth_bp.route("/product/<int:product_id>/review", methods=["POST"])
def submit_review(product_id): return controller.submit_review(product_id)

# Refunds
@auth_bp.route("/orders/<int:order_id>/refund", methods=["POST"])
def request_refund(order_id): return controller.request_refund(order_id)

@auth_bp.route("/my_refunds")
def my_refunds(): return controller.my_refunds()

# Coupons
@auth_bp.route("/coupon/validate", methods=["POST"])
def validate_coupon(): return controller.validate_coupon()
