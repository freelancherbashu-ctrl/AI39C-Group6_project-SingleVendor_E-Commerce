import os
import uuid
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from app.extensions import mysql
from app.models.admin import Admin
from app.models.order import Order
from app.models.product import Product
from app.models.category import Category
from app.models.flash_sale import FlashSale
from app.models.user import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def _save_image(file, subfolder):
    """Save an uploaded image to static/images/<subfolder>/, return the URL path or None."""
    if not file or file.filename == '':
        return None
    if not _allowed(file.filename):
        return None
    ext      = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder   = os.path.join(current_app.root_path, 'static', 'images', subfolder)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return f"/static/images/{subfolder}/{filename}"

def _delete_image(image_path, subfolder):
    """Delete an uploaded image file only if it lives inside the managed subfolder."""
    if not image_path:
        return
    # Only delete files uploaded by admin — ignore seeded images
    if f"images/{subfolder}/" not in image_path:
        return
    relative = image_path.lstrip("/")
    if relative.startswith("static/"):
        relative = relative[len("static/"):]
    abs_path = os.path.join(current_app.root_path, 'static', relative)
    if os.path.isfile(abs_path):
        os.remove(abs_path)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            flash("Please log in to access the admin area.", "error")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated

# ── AUTH ──────────────────────────────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.verify(mysql, username, password)
        if admin:
            session["admin"] = {"id": admin["id"], "username": admin["username"]}
            session.modified = True
            flash(f"Welcome, {admin['username']}!", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")

@admin_bp.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin.login"))

# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Pending'")
    pending_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Cancelled'")
    cancelled_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE order_status != 'Cancelled'")
    revenue = cursor.fetchone()[0] or 0
    cursor.execute("""
        SELECT id, customer_name, total_price, order_status, created_at
        FROM orders ORDER BY created_at DESC LIMIT 5
    """)
    recent_orders = cursor.fetchall()
    total_products   = len(Product.get_all(mysql))
    total_categories = len(Category.get_all(mysql))
    return render_template("admin/dashboard.html",
        total_orders=total_orders,
        pending_orders=pending_orders,
        cancelled_orders=cancelled_orders,
        total_users=total_users,
        revenue=revenue,
        recent_orders=recent_orders,
        total_products=total_products,
        total_categories=total_categories,
        admin=session["admin"]
    )

# ── ORDERS ────────────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status", "")
    cursor = mysql.connection.cursor()
    if status:
        cursor.execute("""
            SELECT id, customer_name, phone, total_price, order_status, payment_method, created_at
            FROM orders WHERE order_status = %s ORDER BY created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT id, customer_name, phone, total_price, order_status, payment_method, created_at
            FROM orders ORDER BY created_at DESC
        """)
    rows = cursor.fetchall()
    return render_template("admin/orders.html", orders=rows,
                           active_status=status, admin=session["admin"])

@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = Order.get_by_id(mysql, order_id)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for("admin.orders"))
    return render_template("admin/order_detail.html", order=order, admin=session["admin"])

@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    new_status = request.form.get("status")
    valid = ("Pending", "Processing", "Completed", "Cancelled")
    if new_status not in valid:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.orders"))
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE orders SET order_status=%s WHERE id=%s", (new_status, order_id))
    mysql.connection.commit()
    flash(f"Order #{order_id} marked as {new_status}.", "success")
    return redirect(url_for("admin.order_detail", order_id=order_id))

# ── USERS ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@admin_required
def users():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, full_name, email, created_at FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return render_template("admin/users.html", users=rows, admin=session["admin"])

# ── PRODUCTS ──────────────────────────────────────────────────────────────────

@admin_bp.route("/products")
@admin_required
def products():
    all_products = Product.get_all(mysql)
    return render_template("admin/products.html", products=all_products, admin=session["admin"])

@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    categories = Category.get_all(mysql)
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        price       = request.form.get("price", "0").strip()
        category    = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image_file  = request.files.get("image")

        if not name or not category:
            flash("Name and category are required.", "error")
            return render_template("admin/product_form.html",
                                   categories=categories, admin=session["admin"],
                                   action="Add", product=None)
        try:
            price = int(price)
        except ValueError:
            flash("Price must be a number.", "error")
            return render_template("admin/product_form.html",
                                   categories=categories, admin=session["admin"],
                                   action="Add", product=None)

        image_path = _save_image(image_file, "products") or "/static/images/placeholder.png"

        pid, err = Product.create(mysql, name, price, category, image_path, description)
        if pid:
            flash(f"Product '{name}' added successfully.", "success")
            return redirect(url_for("admin.products"))
        flash(f"Error adding product: {err}", "error")

    return render_template("admin/product_form.html",
                           categories=categories, admin=session["admin"],
                           action="Add", product=None)

@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product    = Product.get_by_id(mysql, product_id)
    categories = Category.get_all(mysql)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin.products"))

    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        price       = request.form.get("price", "0").strip()
        category    = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        image_file  = request.files.get("image")

        if not name or not category:
            flash("Name and category are required.", "error")
            return render_template("admin/product_form.html",
                                   categories=categories, admin=session["admin"],
                                   action="Edit", product=product)
        try:
            price = int(price)
        except ValueError:
            flash("Price must be a number.", "error")
            return render_template("admin/product_form.html",
                                   categories=categories, admin=session["admin"],
                                   action="Edit", product=product)

        # Only replace image if a new file was uploaded; delete the old one first
        new_image = _save_image(image_file, "products")
        if new_image:
            _delete_image(product["image"], "products")
            image_path = new_image
        else:
            image_path = product["image"]

        ok, err = Product.update(mysql, product_id, name, price, category, image_path, description)
        if ok:
            flash(f"Product '{name}' updated.", "success")
            return redirect(url_for("admin.products"))
        flash(f"Error updating product: {err}", "error")

    return render_template("admin/product_form.html",
                           categories=categories, admin=session["admin"],
                           action="Edit", product=product)

@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = Product.get_by_id(mysql, product_id)
    if product:
        _delete_image(product["image"], "products")
        if Product.delete(mysql, product_id):
            flash(f"Product '{product['name']}' deleted.", "success")
        else:
            flash("Could not delete product.", "error")
    else:
        flash("Product not found.", "error")
    return redirect(url_for("admin.products"))

# ── CATEGORIES ────────────────────────────────────────────────────────────────

@admin_bp.route("/categories")
@admin_required
def categories():
    all_categories = Category.get_all(mysql)
    return render_template("admin/categories.html", categories=all_categories, admin=session["admin"])

@admin_bp.route("/categories/add", methods=["GET", "POST"])
@admin_required
def add_category():
    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/category_form.html",
                                   admin=session["admin"], action="Add", category=None)

        image_path = _save_image(image_file, "categories") or "images/placeholder.png"
        # Category model stores paths relative to /static/ for legacy templates
        # strip leading /static/ if present so it stays consistent
        if image_path.startswith("/static/"):
            image_path = image_path[len("/static/"):]

        cid, err = Category.create(mysql, name, image_path)
        if cid:
            flash(f"Category '{name}' added.", "success")
            return redirect(url_for("admin.categories"))
        flash(f"Error: {err}", "error")

    return render_template("admin/category_form.html",
                           admin=session["admin"], action="Add", category=None)

@admin_bp.route("/categories/<int:cat_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_category(cat_id):
    category = Category.get_by_id(mysql, cat_id)
    if not category:
        flash("Category not found.", "error")
        return redirect(url_for("admin.categories"))

    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        image_file = request.files.get("image")

        if not name:
            flash("Category name is required.", "error")
            return render_template("admin/category_form.html",
                                   admin=session["admin"], action="Edit", category=category)

        new_image = _save_image(image_file, "categories")
        if new_image:
            if new_image.startswith("/static/"):
                new_image = new_image[len("/static/"):]
            _delete_image(category["image"], "categories")
            image_path = new_image
        else:
            image_path = category["image"]

        ok, err = Category.update(mysql, cat_id, name, image_path)
        if ok:
            flash(f"Category '{name}' updated.", "success")
            return redirect(url_for("admin.categories"))
        flash(f"Error: {err}", "error")

    return render_template("admin/category_form.html",
                           admin=session["admin"], action="Edit", category=category)

@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def delete_category(cat_id):
    cat = Category.get_by_id(mysql, cat_id)
    if cat:
        _delete_image(cat["image"], "categories")
        if Category.delete(mysql, cat_id):
            flash(f"Category '{cat['name']}' deleted.", "success")
        else:
            flash("Could not delete category.", "error")
    else:
        flash("Category not found.", "error")
    return redirect(url_for("admin.categories"))

@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.get_by_id(mysql, user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    # Delete profile picture from disk if one exists
    pic = user.get("profile_picture")
    if pic:
        pic_path = os.path.join(current_app.root_path, 'static', 'profile_pics', pic)
        if os.path.isfile(pic_path):
            os.remove(pic_path)

    if User.delete(mysql, user_id):
        flash(f"User '{user['full_name']}' deleted.", "success")
    else:
        flash("Could not delete user.", "error")
    return redirect(url_for("admin.users"))

# ── FLASH SALES ───────────────────────────────────────────────────────────────

@admin_bp.route("/flash-sales")
@admin_required
def flash_sales():
    sales = FlashSale.get_all(mysql)
    return render_template("admin/flash_sales.html", sales=sales, admin=session["admin"])

@admin_bp.route("/flash-sales/add", methods=["GET", "POST"])
@admin_required
def add_flash_sale():
    products = Product.get_all(mysql)
    if request.method == "POST":
        product_id = request.form.get("product_id", "").strip()
        discount   = request.form.get("discount", "").strip()
        label      = request.form.get("label", "Flash Sale").strip() or "Flash Sale"
        starts_at  = request.form.get("starts_at", "").strip()
        ends_at    = request.form.get("ends_at", "").strip()
        try:
            discount = float(discount)
            if not (1 <= discount < 100):
                raise ValueError
        except (ValueError, TypeError):
            flash("Discount must be a number between 1 and 99.", "error")
            return render_template("admin/flash_sale_form.html",
                                   products=products, sale=None,
                                   action="Add", admin=session["admin"])
        if not product_id or not starts_at or not ends_at:
            flash("Product, start time, and end time are required.", "error")
            return render_template("admin/flash_sale_form.html",
                                   products=products, sale=None,
                                   action="Add", admin=session["admin"])
        sid, err = FlashSale.create(mysql, int(product_id), discount, starts_at, ends_at, label)
        if sid:
            flash(f"Flash sale created successfully.", "success")
            return redirect(url_for("admin.flash_sales"))
        flash(f"Error: {err}", "error")
    return render_template("admin/flash_sale_form.html",
                           products=products, sale=None,
                           action="Add", admin=session["admin"])

@admin_bp.route("/flash-sales/<int:sale_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_flash_sale(sale_id):
    sale     = FlashSale.get_by_id(mysql, sale_id)
    products = Product.get_all(mysql)
    if not sale:
        flash("Flash sale not found.", "error")
        return redirect(url_for("admin.flash_sales"))
    if request.method == "POST":
        product_id = request.form.get("product_id", "").strip()
        discount   = request.form.get("discount", "").strip()
        label      = request.form.get("label", "Flash Sale").strip() or "Flash Sale"
        starts_at  = request.form.get("starts_at", "").strip()
        ends_at    = request.form.get("ends_at", "").strip()
        is_active  = 1 if request.form.get("is_active") else 0
        try:
            discount = float(discount)
            if not (1 <= discount < 100):
                raise ValueError
        except (ValueError, TypeError):
            flash("Discount must be a number between 1 and 99.", "error")
            return render_template("admin/flash_sale_form.html",
                                   products=products, sale=sale,
                                   action="Edit", admin=session["admin"])
        ok, err = FlashSale.update(mysql, sale_id, int(product_id), discount,
                                   starts_at, ends_at, label, is_active)
        if ok:
            flash("Flash sale updated.", "success")
            return redirect(url_for("admin.flash_sales"))
        flash(f"Error: {err}", "error")
    return render_template("admin/flash_sale_form.html",
                           products=products, sale=sale,
                           action="Edit", admin=session["admin"])

@admin_bp.route("/flash-sales/<int:sale_id>/toggle", methods=["POST"])
@admin_required
def toggle_flash_sale(sale_id):
    FlashSale.toggle_active(mysql, sale_id)
    flash("Sale status updated.", "success")
    return redirect(url_for("admin.flash_sales"))

@admin_bp.route("/flash-sales/<int:sale_id>/delete", methods=["POST"])
@admin_required
def delete_flash_sale(sale_id):
    if FlashSale.delete(mysql, sale_id):
        flash("Flash sale deleted.", "success")
    else:
        flash("Could not delete flash sale.", "error")
    return redirect(url_for("admin.flash_sales"))