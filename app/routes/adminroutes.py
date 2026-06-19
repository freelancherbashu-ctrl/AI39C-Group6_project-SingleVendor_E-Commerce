from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models.product_models import Product
from app.models.order_models import Order

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Admin access required.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped_view


@admin_bp.route("/products")
@admin_required
def products():
    all_products = Product.get_all()
    # Also show inactive products for admin
    from app.models.database import get_db
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
    all_products = cursor.fetchall()
    cursor.close()
    return render_template("admin/products.html", products=all_products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = float(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
        category = request.form.get("category", "").strip()
        image_url = request.form.get("image_url", "").strip()
        Product.create(name, description, price, stock, category, image_url)
        flash(f"Product '{name}' created.")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", product=None)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = Product.find_by_id(product_id)
    if not product:
        flash("Product not found.")
        return redirect(url_for("admin.products"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = float(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
        category = request.form.get("category", "").strip()
        image_url = request.form.get("image_url", "").strip()
        Product.update(product_id, name, description, price, stock, category, image_url)
        flash("Product updated.")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", product=product)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    Product.delete(product_id)
    flash("Product deleted.")
    return redirect(url_for("admin.products"))


@admin_bp.route("/orders")
@admin_required
def orders():
    all_orders = Order.get_all()
    return render_template("admin/orders.html", orders=all_orders)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_update_status(order_id):
    status = request.form.get("status", "pending")
    Order.update_status(order_id, status)
    flash(f"Order #{order_id} status updated to '{status}'.")
    return redirect(url_for("admin.orders"))
