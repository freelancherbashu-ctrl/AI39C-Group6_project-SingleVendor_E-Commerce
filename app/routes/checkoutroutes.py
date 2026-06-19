from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.controllers.checkout import place_order
from app.models.cart_models import CartItem
from app.models.order_models import Order, OrderItem
from app.routes.customerroutes import login_required

checkout_bp = Blueprint("checkout", __name__)


@checkout_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    customer_id = session["customer_id"]
    if request.method == "POST":
        success, message, order_id = place_order(customer_id)
        flash(message)
        if success:
            return redirect(url_for("checkout.order_detail", order_id=order_id))
        return redirect(url_for("cart.view"))

    items = CartItem.get_cart(customer_id)
    total = sum(item["line_total"] for item in items)
    return render_template("checkout.html", items=items, total=total)


@checkout_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    customer_id = session["customer_id"]
    order = Order.find_by_id(order_id)
    if not order or order["customer_id"] != customer_id:
        flash("Order not found.")
        return redirect(url_for("customer.orders"))
    items = OrderItem.find_by_order(order_id)
    return render_template("order_detail.html", order=order, items=items)
