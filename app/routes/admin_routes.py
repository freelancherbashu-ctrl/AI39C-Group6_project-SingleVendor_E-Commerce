from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy import func
from app.models.database import db
from app.models.product_models import Product, Category, Order, OrderItem
from app.controllers.admin import save_product_image, delete_product_image

admin_bp = Blueprint(
    "admin", __name__,
    url_prefix="/admin",
    template_folder="../templates/admin",
)


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


# ===== PRODUCTS =====
@admin_bp.route("/products")
def products():
    q = request.args.get("q", "").strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    items = query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items, q=q)


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
    query = Order.query
    if status in ("pending", "processing", "completed", "cancelled"):
        query = query.filter_by(status=status)
    items = query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=items, active_status=status)


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
