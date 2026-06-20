import os
import uuid
from datetime import datetime
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

@admin_bp.context_processor
def inject_pending_orders():
    """Inject pending_orders count into all admin templates for the notification bell."""
    if session.get("admin"):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Pending'")
            count = cursor.fetchone()[0]
            cursor.close()
            return {"pending_orders": count}
        except Exception:
            pass
    return {"pending_orders": 0}

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
    """Delete an uploaded image file only if it lives inside the managed subfolder.
    Handles Windows file-locking (WinError 32) gracefully — if the file is still
    held by the dev-server reloader, the delete is skipped silently rather than
    crashing the request.
    """
    if not image_path:
        return
    # Only delete files uploaded by admin — ignore seeded/static images
    if f"images/{subfolder}/" not in image_path:
        return
    relative = image_path.lstrip("/")
    if relative.startswith("static/"):
        relative = relative[len("static/"):]
    abs_path = os.path.join(current_app.root_path, 'static', relative)
    if not os.path.isfile(abs_path):
        return
    try:
        os.remove(abs_path)
    except PermissionError:
        # Windows: file is locked by another process (e.g. the Flask reloader).
        # The old image will remain on disk but the DB record is already updated,
        # so this is harmless — the file will be orphaned but won't block the operation.
        current_app.logger.warning(
            "Could not delete image (file locked): %s — it may be cleaned up manually.", abs_path
        )
    except OSError as exc:
        current_app.logger.warning("Could not delete image %s: %s", abs_path, exc)


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
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE order_status = 'Completed'")
    revenue = cursor.fetchone()[0] or 0
    cursor.execute("""
        SELECT id, customer_name, total_price, order_status, created_at
        FROM orders ORDER BY created_at DESC LIMIT 5
    """)
    recent_orders = cursor.fetchall()
    total_products   = len(Product.get_all(mysql))
    total_categories = len(Category.get_all(mysql))
    low_stock        = Product.get_low_stock(mysql, threshold=5)
    return render_template("admin/dashboard.html",
        total_orders=total_orders,
        pending_orders=pending_orders,
        cancelled_orders=cancelled_orders,
        total_users=total_users,
        revenue=revenue,
        recent_orders=recent_orders,
        total_products=total_products,
        total_categories=total_categories,
        low_stock=low_stock,
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
            SELECT id, user_id, phone, total_price, order_status, payment_method, created_at
            FROM orders WHERE order_status = %s ORDER BY created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT id, user_id, phone, total_price, order_status, payment_method, created_at
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


@admin_bp.route("/orders/<int:order_id>/json")
@admin_required
def order_detail_json(order_id):
    """JSON endpoint for the order drawer on the orders list page."""
    from flask import jsonify
    order = Order.get_by_id(mysql, order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404
    items = []
    for it in (order.get("order_items") or []):
        items.append({
            "name":     it.get("name", ""),
            "image":    it.get("image", ""),
            "qty":      it.get("qty", 1),
            "price":    float(it.get("price", 0)),
            "subtotal": float(it.get("subtotal", 0)),
            "on_sale":  it.get("on_sale", False),
        })
    return jsonify({
        "id":             order["id"],
        "customer_name":  order["customer_name"],
        "phone":          order["phone"],
        "area":           order.get("area", ""),
        "city":           order.get("city", ""),
        "district":       order.get("district", ""),
        "province":       order.get("province", ""),
        "landmark":       order.get("landmark", ""),
        "payment_method": order.get("payment_method", ""),
        "payment_status": order.get("payment_status", "Pending"),
        "order_status":   order["order_status"],
        "total_price":    float(order["total_price"]),
        "created_at":     order["created_at"].strftime("%d %b %Y, %I:%M %p") if order.get("created_at") else "",
        "items":          items,
    })

@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    new_status = request.form.get("status")
    # Admin can Reject an order, but never Cancel one — cancelling is a
    # customer-only action. "Cancelled" orders only ever arrive via the
    # customer-facing cancel flow or an auto-cancel on payment rejection.
    valid = ("Pending", "Approved", "Processing", "Completed", "Rejected")
    if new_status not in valid:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.orders"))

    # Fetch current order so we can make the right inventory call
    order = Order.get_by_id(mysql, order_id)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for("admin.orders"))

    old_status = order["order_status"]

    # Terminal states can't be reopened or changed further — most importantly,
    # a Cancelled order (e.g. the customer cancelled it) must stay cancelled
    # and never be silently moved forward again.
    terminal_statuses = ("Cancelled", "Rejected", "Completed")
    if old_status in terminal_statuses:
        flash(f"Order #{order_id} is already {old_status} and can't be changed further.", "error")
        return redirect(url_for("admin.orders"))

    # Block processing/completing online payment orders until payment is approved
    online_methods = ("esewa", "khalti")
    restricted     = ("Processing", "Completed", "Approved")
    if (new_status in restricted
            and order.get("payment_method") in online_methods
            and order.get("payment_status") != "Approved"):
        flash("Payment must be approved before changing order to this status.", "error")
        return redirect(url_for("admin.orders"))

    # Reject is only allowed while payment hasn't been approved yet — once
    # payment is approved, the order has to be fulfilled or completed, not rejected.
    if new_status == "Rejected" and order.get("payment_status") == "Approved":
        flash("Can't reject — payment for this order is already approved.", "error")
        return redirect(url_for("admin.orders"))

    # Statuses where stock is still reserved (not yet deducted or released)
    reserved_statuses = ("Pending", "Approved", "Processing")

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE orders SET order_status=%s WHERE id=%s", (new_status, order_id))
    mysql.connection.commit()

    if cursor.rowcount:
        if new_status == "Completed" and old_status in reserved_statuses:
            # COD delivered — convert reservations into real deductions
            Order.confirm_stock(mysql, order_id)
        elif new_status in ("Cancelled", "Rejected") and old_status in reserved_statuses:
            # Order aborted — release the reservations back to available
            Order.release_stock(mysql, order_id)

    flash(f"Order #{order_id} marked as {new_status}.", "success")
    return redirect(url_for("admin.orders"))

# ── USERS ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.get_all(mysql)
    return render_template("admin/users.html", users=all_users, admin=session["admin"])

@admin_bp.route("/users/<int:user_id>/toggle-block", methods=["POST"])
@admin_required
def toggle_block_user(user_id):
    result = User.toggle_block(mysql, user_id)
    if result is None:
        flash("User not found.", "error")
    elif result:
        flash("User has been blocked.", "success")
    else:
        flash("User has been unblocked.", "success")
    return redirect(url_for("admin.users"))

# ── PRODUCTS ──────────────────────────────────────────────────────────────────

@admin_bp.route("/products")
@admin_required
def products():
    all_products = Product.get_all(mysql)
    categories   = Category.get_all(mysql)
    return render_template("admin/products.html", products=all_products, categories=categories, admin=session["admin"])

@admin_bp.route("/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    categories = Category.get_all(mysql)
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        price       = request.form.get("price", "0").strip()
        category    = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        stock       = request.form.get("stock", "0").strip()
        image_file  = request.files.get("image")

        if not name or not category:
            flash("Name and category are required.", "error")
            return redirect(url_for("admin.products"))
        try:
            price = int(price)
        except ValueError:
            flash("Price must be a number.", "error")
            return redirect(url_for("admin.products"))
        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError
        except ValueError:
            flash("Stock must be a non-negative number.", "error")
            return redirect(url_for("admin.products"))

        image_path = _save_image(image_file, "products") or "/static/images/placeholder.png"

        pid, err = Product.create(mysql, name, price, category, image_path, description, stock)
        if pid:
            flash(f"Product '{name}' added successfully.", "success")
            return redirect(url_for("admin.products"))
        flash(f"Error adding product: {err}", "error")

    return redirect(url_for("admin.products"))

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
        stock       = request.form.get("stock", "0").strip()
        image_file  = request.files.get("image")

        if not name or not category:
            flash("Name and category are required.", "error")
            return redirect(url_for("admin.products"))
        try:
            price = int(price)
        except ValueError:
            flash("Price must be a number.", "error")
            return redirect(url_for("admin.products"))
        try:
            stock = int(stock)
            if stock < 0:
                raise ValueError
        except ValueError:
            flash("Stock must be a non-negative number.", "error")
            return redirect(url_for("admin.products"))

        # Only replace image if a new file was uploaded; delete the old one first
        new_image = _save_image(image_file, "products")
        if new_image:
            _delete_image(product["image"], "products")
            image_path = new_image
        else:
            image_path = product["image"]

        ok, err = Product.update(mysql, product_id, name, price, category, image_path, description, stock)
        if ok:
            flash(f"Product '{name}' updated successfully.", "success")
        else:
            flash(f"Error updating product: {err or 'Unknown error'}", "error")
        return redirect(url_for("admin.products"))

    return redirect(url_for("admin.products"))

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

@admin_bp.route("/products/<int:product_id>/stock", methods=["POST"])
@admin_required
def update_stock(product_id):
    try:
        new_stock = int(request.form.get("stock", 0))
        if new_stock < 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Stock must be a non-negative number.", "error")
        return redirect(url_for("admin.products"))
    Product.update_stock(mysql, product_id, new_stock)
    flash("Stock updated.", "success")
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
            try:
                os.remove(pic_path)
            except (PermissionError, OSError) as exc:
                current_app.logger.warning("Could not delete profile pic %s: %s", pic_path, exc)

    if User.delete(mysql, user_id):
        flash(f"User '{user['full_name']}' deleted.", "success")
    else:
        flash("Could not delete user.", "error")
    return redirect(url_for("admin.users"))

# ── FLASH SALES ───────────────────────────────────────────────────────────────

@admin_bp.route("/flash-sales")
@admin_required
def flash_sales():
    sales    = FlashSale.get_all(mysql)
    products = Product.get_all(mysql)
    return render_template("admin/flash_sales.html", sales=sales, products=products,
                            now=datetime.now(), admin=session["admin"])

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
        if starts_at >= ends_at:
            flash("End time must be after start time.", "error")
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
        if not product_id or not starts_at or not ends_at:
            flash("Product, start time, and end time are required.", "error")
            return render_template("admin/flash_sale_form.html",
                                   products=products, sale=sale,
                                   action="Edit", admin=session["admin"])
        if starts_at >= ends_at:
            flash("End time must be after start time.", "error")
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

# ── PAYMENTS ──────────────────────────────────────────────────────────────────

@admin_bp.route("/payments")
@admin_required
def payments():
    status = request.args.get("status", "")
    cursor = mysql.connection.cursor()
    if status:
        cursor.execute("""
            SELECT o.id, o.user_id, o.total_price, o.payment_method,
                   o.payment_status, o.order_status, o.created_at, o.transaction_code
            FROM orders o
            WHERE o.payment_method IN ('esewa','khalti') AND o.payment_status = %s
            ORDER BY o.created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT o.id, o.user_id, o.total_price, o.payment_method,
                   o.payment_status, o.order_status, o.created_at, o.transaction_code
            FROM orders o
            WHERE o.payment_method IN ('esewa','khalti')
            ORDER BY o.created_at DESC
        """)
    rows = cursor.fetchall()
    return render_template("admin/payments.html", payments=rows,
                           active_status=status, admin=session["admin"])

@admin_bp.route("/payments/<int:order_id>/approve", methods=["POST"])
@admin_required
def approve_payment(order_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE orders SET payment_status='Approved', order_status='Approved'
        WHERE id=%s AND payment_status='Pending' AND order_status = 'Pending'
    """, (order_id,))
    mysql.connection.commit()
    if cursor.rowcount:
        Order.confirm_stock(mysql, order_id)
        flash(f"Payment for Order #{order_id} approved.", "success")
    else:
        flash("Could not approve — payment may already be processed, or the order was cancelled.", "error")
    return redirect(url_for("admin.payments"))

@admin_bp.route("/payments/<int:order_id>/reject", methods=["POST"])
@admin_required
def reject_payment(order_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE orders SET payment_status='Rejected', order_status='Cancelled'
        WHERE id=%s AND payment_status='Pending' AND order_status = 'Pending'
    """, (order_id,))
    mysql.connection.commit()
    if cursor.rowcount:
        Order.release_stock(mysql, order_id)
        flash(f"Payment for Order #{order_id} rejected. Order auto-cancelled.", "error")
    else:
        flash("Could not reject — payment may already be processed, or the order was already cancelled.", "error")
    return redirect(url_for("admin.payments"))

# ── REPORTS ───────────────────────────────────────────────────────────────────

@admin_bp.route("/reports")
@admin_required
def reports():
    cursor = mysql.connection.cursor()

    # Monthly sales (last 12 months)
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') AS month,
               COUNT(*) AS total_orders,
               SUM(total_price) AS revenue
        FROM orders
        WHERE order_status = 'Completed'
          AND created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month ASC
    """)
    monthly_sales = cursor.fetchall()

    # Top products by revenue
    cursor.execute("""
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.name')) AS product_name,
            SUM(JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.qty'))) AS total_qty,
            SUM(JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.subtotal'))) AS total_revenue
        FROM orders o
        JOIN JSON_TABLE(o.items_json, '$[*]' COLUMNS (value JSON PATH '$')) AS item
        WHERE o.order_status = 'Completed'
          AND o.items_json IS NOT NULL AND o.items_json != ''
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    top_products = cursor.fetchall()

    # Summary stats
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status = 'Completed'")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE order_status = 'Completed'")
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM orders WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW()) AND order_status = 'Completed'")
    this_month_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_price) FROM orders WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW()) AND order_status = 'Completed'")
    this_month_revenue = cursor.fetchone()[0] or 0

    return render_template("admin/reports.html",
        monthly_sales=monthly_sales,
        top_products=top_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        this_month_orders=this_month_orders,
        this_month_revenue=this_month_revenue,
        admin=session["admin"]
    )

@admin_bp.route("/reports/export.csv")
@admin_required
def export_reports_csv():
    """Downloadable CSV of the same monthly revenue + top products data shown on the reports page."""
    import csv, io
    from flask import Response

    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') AS month,
               COUNT(*) AS total_orders,
               SUM(total_price) AS revenue
        FROM orders
        WHERE order_status = 'Completed'
          AND created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month ASC
    """)
    monthly_sales = cursor.fetchall()

    cursor.execute("""
        SELECT
            JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.name')) AS product_name,
            SUM(JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.qty'))) AS total_qty,
            SUM(JSON_UNQUOTE(JSON_EXTRACT(item.value, '$.subtotal'))) AS total_revenue
        FROM orders o
        JOIN JSON_TABLE(o.items_json, '$[*]' COLUMNS (value JSON PATH '$')) AS item
        WHERE o.order_status = 'Completed'
          AND o.items_json IS NOT NULL AND o.items_json != ''
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    top_products = cursor.fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["MeroPasal — Sales Report"])
    writer.writerow([])
    writer.writerow(["Monthly Revenue (last 12 months)"])
    writer.writerow(["Month", "Orders", "Revenue (Rs.)"])
    for month, orders_count, revenue in monthly_sales:
        writer.writerow([month, orders_count, f"{revenue or 0:.2f}"])
    writer.writerow([])
    writer.writerow(["Top Products by Revenue"])
    writer.writerow(["Product", "Units Sold", "Revenue (Rs.)"])
    for name, qty, revenue in top_products:
        writer.writerow([name, qty, f"{revenue or 0:.2f}"])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=meropasal_sales_report.csv"}
    )


# ── REFUNDS ───────────────────────────────────────────────────────────────────

@admin_bp.route("/refunds")
@admin_required
def refunds():
    from app.models.refund import Refund
    status = request.args.get("status")
    all_refunds = Refund.get_all_admin(mysql, status=status)
    return render_template("admin/refunds.html", refunds=all_refunds,
                           active_status=status, admin=session["admin"])

@admin_bp.route("/refunds/<int:refund_id>/update", methods=["POST"])
@admin_required
def update_refund(refund_id):
    from app.models.refund import Refund
    status     = request.form.get("status")
    admin_note = request.form.get("admin_note", "").strip()
    ok = Refund.update_status(mysql, refund_id, status, admin_note or None)
    if ok:
        flash(f"Refund #{refund_id} updated to {status}.", "success")
    else:
        flash("Failed to update refund.", "error")
    return redirect(url_for("admin.refunds"))

@admin_bp.route("/refunds/<int:refund_id>/json")
@admin_required
def refund_json(refund_id):
    from flask import jsonify
    from app.models.refund import Refund
    refund = Refund.get_by_id(mysql, refund_id)
    if not refund:
        return jsonify({"error": "Not found"}), 404
    refund["created_at"] = str(refund["created_at"]) if refund["created_at"] else None
    refund["updated_at"] = str(refund["updated_at"]) if refund["updated_at"] else None
    return jsonify(refund)


# ── COUPONS ───────────────────────────────────────────────────────────────────

@admin_bp.route("/coupons")
@admin_required
def coupons():
    from app.models.coupon import Coupon
    all_coupons = Coupon.get_all(mysql)
    return render_template("admin/coupons.html", coupons=all_coupons,
                           now=datetime.now(), admin=session["admin"])

@admin_bp.route("/coupons/add", methods=["GET", "POST"])
@admin_required
def add_coupon():
    from app.models.coupon import Coupon
    if request.method == "POST":
        ok, err = Coupon.create(
            mysql,
            code=request.form.get("code", ""),
            discount_type=request.form.get("discount_type", "percent"),
            discount_value=float(request.form.get("discount_value", 0)),
            min_order_amount=float(request.form.get("min_order_amount", 0)),
            max_uses=request.form.get("max_uses") or None,
            valid_from=request.form.get("valid_from"),
            valid_until=request.form.get("valid_until"),
        )
        if ok:
            flash("Coupon created successfully.", "success")
            return redirect(url_for("admin.coupons"))
        flash(f"Error: {err}", "error")
    return render_template("admin/coupon_form.html", coupon=None, admin=session["admin"])

@admin_bp.route("/coupons/<int:coupon_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_coupon(coupon_id):
    from app.models.coupon import Coupon
    coupon = Coupon.get_by_id(mysql, coupon_id)
    if not coupon:
        flash("Coupon not found.", "error")
        return redirect(url_for("admin.coupons"))
    if request.method == "POST":
        ok, err = Coupon.update(
            mysql, coupon_id,
            code=request.form.get("code", ""),
            discount_type=request.form.get("discount_type", "percent"),
            discount_value=float(request.form.get("discount_value", 0)),
            min_order_amount=float(request.form.get("min_order_amount", 0)),
            max_uses=request.form.get("max_uses") or None,
            valid_from=request.form.get("valid_from"),
            valid_until=request.form.get("valid_until"),
            is_active=request.form.get("is_active") == "1",
        )
        if ok:
            flash("Coupon updated.", "success")
            return redirect(url_for("admin.coupons"))
        flash(f"Error: {err}", "error")
    return render_template("admin/coupon_form.html", coupon=coupon, admin=session["admin"])

@admin_bp.route("/coupons/<int:coupon_id>/delete", methods=["POST"])
@admin_required
def delete_coupon(coupon_id):
    from app.models.coupon import Coupon
    Coupon.delete(mysql, coupon_id)
    flash("Coupon deleted.", "success")
    return redirect(url_for("admin.coupons"))


# ── REVIEWS (moderation) ──────────────────────────────────────────────────────

@admin_bp.route("/reviews")
@admin_required
def reviews():
    from app.models.review import Review
    all_reviews = Review.get_all_admin(mysql)
    return render_template("admin/reviews.html", reviews=all_reviews,
                           admin=session["admin"])

@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@admin_required
def delete_review(review_id):
    from app.models.review import Review
    Review.delete(mysql, review_id)
    flash("Review deleted.", "success")
    return redirect(url_for("admin.reviews"))