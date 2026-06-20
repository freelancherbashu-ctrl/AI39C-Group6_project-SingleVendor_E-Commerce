import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from app.models.database import db
from app.models.product_models import Product, Category, Order, OrderItem
from app.models.settings_model import Setting
from app.controllers.admin import save_product_image, delete_product_image
from app.controllers.auth import admin_required

admin_bp = Blueprint(
    "admin", __name__,
    url_prefix="/admin",
    template_folder="../templates/admin",
)

# Apply auth gate to every admin route. No-op until auth teammate's
# module is ready; flipping admin_required's body turns it on for all routes.
@admin_bp.before_request
@admin_required
def _gate():
    pass

# ===== ADMIN HOME (admin_index) =====
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
    cursor.execute("""
        SELECT SUM(total_price) FROM orders
        WHERE (payment_method IN ('esewa','khalti') AND payment_status = 'Approved')
           OR (payment_method = 'cod' AND order_status = 'Completed')
    """)
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
            SELECT id, customer_name, phone, total_price, order_status, payment_method, created_at, user_id
            FROM orders WHERE order_status = %s ORDER BY created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT id, customer_name, phone, total_price, order_status, payment_method, created_at, user_id
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
    today = datetime.utcnow().date()
    labels, values = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        total = (db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
                 .filter(Order.status == "completed",
                         Order.created_at >= day,
                         Order.created_at < next_day)
                 .scalar() or 0)
        labels.append(day.strftime("%b %d"))
        values.append(float(total))
    return jsonify({"labels": labels, "values": values})


# ===== PRODUCTS =====
@admin_bp.route("/products")
def products():
    q = request.args.get("q", "").strip()
    cat_id = request.args.get("category_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if cat_id:
        query = query.filter(Product.category_id == cat_id)

    pagination = (query.order_by(Product.created_at.desc())
                       .paginate(page=page, per_page=per_page, error_out=False))
    categories = Category.query.order_by(Category.name).all()

    return render_template("admin/products.html",
                           products=pagination.items,
                           pagination=pagination,
                           categories=categories,
                           q=q,
                           selected_cat=cat_id)


@admin_bp.route("/products/add", methods=["GET", "POST"])
def add_product():
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        try:
            image_name = save_product_image(request.files.get("image"))
            product = Product(
                name=request.form["name"].strip(),
                description=request.form.get("description", "").strip(),
                price=float(request.form.get("price") or 0),
                stock=int(request.form.get("stock") or 0),
                category_id=int(request.form["category_id"]) if request.form.get("category_id") else None,
                image=image_name,
                is_active=bool(request.form.get("is_active")),
            )
            db.session.add(product)
            db.session.commit()
            flash("Product added successfully.", "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template("admin/product_form.html", product=None, categories=categories)


@admin_bp.route("/products/edit/<int:pid>", methods=["GET", "POST"])
def edit_product(pid):
    product = Product.query.get_or_404(pid)
    categories = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        try:
            product.name = request.form["name"].strip()
            product.description = request.form.get("description", "").strip()
            product.price = float(request.form.get("price") or 0)
            product.stock = int(request.form.get("stock") or 0)
            product.category_id = int(request.form["category_id"]) if request.form.get("category_id") else None
            product.is_active = bool(request.form.get("is_active"))
            new_image = save_product_image(request.files.get("image"))
            if new_image:
                delete_product_image(product.image)
                product.image = new_image
            db.session.commit()
            flash("Product updated.", "success")
            return redirect(url_for("admin.products"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "danger")
    return render_template("admin/product_form.html", product=product, categories=categories)


@admin_bp.route("/products/delete/<int:pid>", methods=["POST"])
def delete_product(pid):
    product = Product.query.get_or_404(pid)
    delete_product_image(product.image)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted.", "info")
    return redirect(url_for("admin.products"))

@admin_bp.route("/products/bulk", methods=["POST"])
def bulk_products():
    action = request.form.get("action")
    ids = request.form.getlist("ids", type=int)
    if not ids:
        flash("No products selected.", "warning")
        return redirect(url_for("admin.products"))

    items = Product.query.filter(Product.id.in_(ids)).all()
    count = 0
    if action == "activate":
        for p in items:
            p.is_active = True
            count += 1
        msg = f"Activated {count} product(s)."
    elif action == "deactivate":
        for p in items:
            p.is_active = False
            count += 1
        msg = f"Deactivated {count} product(s)."
    elif action == "delete":
        for p in items:
            delete_product_image(p.image)
            db.session.delete(p)
            count += 1
        msg = f"Deleted {count} product(s)."
    else:
        flash("Unknown action.", "danger")
        return redirect(url_for("admin.products"))

    db.session.commit()
    flash(msg, "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:pid>/stock", methods=["POST"])
def adjust_stock(pid):
    product = Product.query.get_or_404(pid)
    try:
        delta = int(request.form.get("delta", 0))
    except ValueError:
        delta = 0
    product.stock = max(0, product.stock + delta)
    db.session.commit()
    flash(f"Stock for '{product.name}' is now {product.stock}.", "success")
    return redirect(request.referrer or url_for("admin.products"))

# ===== CATEGORIES =====
@admin_bp.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        name = request.form["name"].strip()
        desc = request.form.get("description", "").strip()
        if not name:
            flash("Name required.", "warning")
        elif Category.query.filter_by(name=name).first():
            flash("Category already exists.", "warning")
        else:
            db.session.add(Category(name=name, description=desc))
            db.session.commit()
            flash("Category added.", "success")
        return redirect(url_for("admin.categories"))
    items = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=items)


@admin_bp.route("/categories/edit/<int:cid>", methods=["POST"])
def edit_category(cid):
    cat = Category.query.get_or_404(cid)
    cat.name = request.form["name"].strip()
    cat.description = request.form.get("description", "").strip()
    db.session.commit()
    flash("Category updated.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/categories/delete/<int:cid>", methods=["POST"])
def delete_category(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "info")
    return redirect(url_for("admin.categories"))


# ===== ORDERS =====
@admin_bp.route("/orders")
def orders():
    status = request.args.get("status")
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Order.query
    if status in ("pending", "processing", "completed", "cancelled"):
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Order.customer_name.ilike(like),
            Order.customer_email.ilike(like),
            Order.customer_phone.ilike(like),
        ))

    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)

    return render_template("admin/orders.html",
                           orders=pagination.items,
                           pagination=pagination,
                           active_status=status,
                           q=q,
                           filter_total=0,
                           filter_count=pagination.total)

@admin_bp.route("/orders/export.csv")
def orders_export_csv():
    from datetime import datetime

    status = request.args.get("status")
    q = request.args.get("q", "").strip()

    query = Order.query
    if status in ("pending", "processing", "completed", "cancelled"):
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Order.customer_name.ilike(like),
            Order.customer_email.ilike(like),
            Order.customer_phone.ilike(like),
        ))

@admin_bp.route("/payments")
@admin_required
def payments():
    status = request.args.get("status", "")
    cursor = mysql.connection.cursor()
    if status:
        cursor.execute("""
            SELECT o.id, o.customer_name, o.total_price, o.payment_method,
                   o.payment_status, o.order_status, o.created_at, o.transaction_code, o.user_id
            FROM orders o
            WHERE o.payment_method IN ('esewa','khalti') AND o.payment_status = %s
            ORDER BY o.created_at DESC
        """, (status,))
    else:
        cursor.execute("""
            SELECT o.id, o.customer_name, o.total_price, o.payment_method,
                   o.payment_status, o.order_status, o.created_at, o.transaction_code, o.user_id
            FROM orders o
            WHERE o.payment_method IN ('esewa','khalti')
            ORDER BY o.created_at DESC
        """)
    rows = cursor.fetchall()
    return render_template("admin/payments.html", payments=rows,
                           active_status=status, admin=session["admin"])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Order ID", "Customer", "Email", "Phone",
                     "Address", "Amount", "Status", "Created At"])
    for o in rows:
        writer.writerow([
            o.id, o.customer_name, o.customer_email or "", o.customer_phone or "",
            o.address or "", f"{o.total_amount:.2f}", o.status,
            o.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

@admin_bp.route("/payments/<int:order_id>/reject", methods=["POST"])
@admin_required
def reject_payment(order_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE orders SET payment_status='Rejected', order_status='Cancelled'
        WHERE id=%s AND payment_status='Pending'
    """, (order_id,))
    mysql.connection.commit()
    if cursor.rowcount:
        Order.release_stock(mysql, order_id)
        flash(f"Payment for Order #{order_id} rejected. Order auto-cancelled.", "error")
    else:
        flash("Could not reject — payment may already be processed.", "error")
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
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
          AND ((payment_method IN ('esewa','khalti') AND payment_status = 'Approved')
           OR  (payment_method = 'cod' AND order_status = 'Completed'))
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
        WHERE o.order_status NOT IN ('Cancelled', 'Rejected')
          AND o.items_json IS NOT NULL AND o.items_json != ''
        GROUP BY product_name
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    top_products = cursor.fetchall()

    # Summary stats
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_status NOT IN ('Cancelled','Rejected')")
    total_orders = cursor.fetchone()[0]
    cursor.execute("""
        SELECT SUM(total_price) FROM orders
        WHERE (payment_method IN ('esewa','khalti') AND payment_status = 'Approved')
           OR (payment_method = 'cod' AND order_status = 'Completed')
    """)
    total_revenue = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM orders WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW()) AND order_status NOT IN ('Cancelled','Rejected')")
    this_month_orders = cursor.fetchone()[0]
    cursor.execute("""
        SELECT SUM(total_price) FROM orders
        WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW())
          AND ((payment_method IN ('esewa','khalti') AND payment_status = 'Approved')
           OR  (payment_method = 'cod' AND order_status = 'Completed'))
    """)
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
                           admin=session["admin"])

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
