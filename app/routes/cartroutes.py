from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models.cart_models import CartItem
from app.models.product_models import Product
from app.routes.customerroutes import login_required

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart")
@login_required
def view():
    customer_id = session["customer_id"]
    items = CartItem.get_cart(customer_id)
    total = sum(item["line_total"] for item in items)
    return render_template("cart.html", items=items, total=total)


@cart_bp.route("/cart/add", methods=["POST"])
@login_required
def add():
    customer_id = session["customer_id"]
    product_id = int(request.form.get("product_id", 0))
    quantity = int(request.form.get("quantity", 1))

    product = Product.find_by_id(product_id)
    if not product or quantity < 1 or quantity > product["stock"]:
        flash("Invalid product or quantity.")
        return redirect(url_for("product.listing"))

    CartItem.add_or_update(customer_id, product_id, quantity)
    flash(f"'{product['name']}' added to cart.")
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/update", methods=["POST"])
@login_required
def update():
    customer_id = session["customer_id"]
    product_id = int(request.form.get("product_id", 0))
    quantity = int(request.form.get("quantity", 1))
    CartItem.update_quantity(customer_id, product_id, quantity)
    flash("Cart updated.")
    return redirect(url_for("cart.view"))


@cart_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove():
    customer_id = session["customer_id"]
    product_id = int(request.form.get("product_id", 0))
    CartItem.remove(customer_id, product_id)
    flash("Item removed from cart.")
    return redirect(url_for("cart.view"))
