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
def admin_index():
    stats = {
        "total_products": Product.query.count(),
        "total_categories": Category.query.count(),
        "total_orders": Order.query.count(),
        "pending_orders":    Order.query.filter_by(status="pending").count(),
        "processing_orders": Order.query.filter_by(status="processing").count(),
        "completed_orders":  Order.query.filter_by(status="completed").count(),
        "cancelled_orders":  Order.query.filter_by(status="cancelled").count(),
        "revenue": db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
                              .filter(Order.status == "completed").scalar() or 0,
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    low_stock = Product.query.filter(Product.stock <= 5).limit(5).all()
    return render_template("admin/admin_index.html",
                           stats=stats, recent_orders=recent_orders, low_stock=low_stock)

@admin_bp.route("/api/sales-chart")
def api_sales_chart():
    """Returns last 7 days of completed-order revenue as JSON for Chart.js."""
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
                           q=q)

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

    rows = query.order_by(Order.created_at.desc()).all()

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

    filename = f"orders_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@admin_bp.route("/orders/<int:oid>")
def order_detail(oid):
    order = Order.query.get_or_404(oid)
    return render_template("admin/order_detail.html", order=order)


@admin_bp.route("/orders/<int:oid>/status", methods=["POST"])
def update_order_status(oid):
    order = Order.query.get_or_404(oid)
    new_status = request.form.get("status")
    if new_status not in ("pending", "processing", "completed", "cancelled"):
        abort(400)
    order.status = new_status
    db.session.commit()
    flash(f"Order #{oid} marked {new_status}.", "success")
    return redirect(url_for("admin.order_detail", oid=oid))


@admin_bp.route("/orders/<int:oid>/delete", methods=["POST"])
def delete_order(oid):
    order = Order.query.get_or_404(oid)
    db.session.delete(order)
    db.session.commit()
    flash("Order deleted.", "info")
    return redirect(url_for("admin.orders"))


# =========================================================
# SETTINGS
# =========================================================
@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        Setting.set("site_name", request.form.get("site_name", "meropasal").strip())
        Setting.set("low_stock_threshold", request.form.get("low_stock_threshold", "5").strip())
        Setting.set("currency", request.form.get("currency", "Rs.").strip())
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))

    current = {
        "site_name":           Setting.get("site_name", "meropasal"),
        "low_stock_threshold": Setting.get("low_stock_threshold", "5"),
        "currency":            Setting.get("currency", "Rs."),
    }
    return render_template("admin/settings.html", settings=current)
