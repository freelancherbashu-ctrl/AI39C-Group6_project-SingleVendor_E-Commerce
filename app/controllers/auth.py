import os
from functools import wraps
from flask import render_template, session, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from app.data.products import products
from app.data.categories import categories
from app.models.order import Order
from app.models.user import User
from app.extensions import mysql

UPLOAD_FOLDER   = os.path.join(os.path.dirname(__file__), '..', 'static', 'profile_pics')
ALLOWED_EXT     = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
product_map     = {str(p["id"]): p for p in products}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def _build_items_snapshot(cart):
    items = []
    for pid, qty in cart.items():
        p = product_map.get(str(pid))
        if p:
            items.append({
                "id": p["id"], "name": p["name"], "price": p["price"],
                "image": p["image"], "qty": qty, "subtotal": p["price"] * qty
            })
    return items

def _calc_total(items):
    return sum(i["subtotal"] for i in items)

def _cart_count():
    return sum(session.get("cart", {}).values())

def _current_user():
    return session.get("user")

def _refresh_user_session(user_id):
    """Re-read user from DB and update session so header reflects changes."""
    u = User.get_by_id(mysql, user_id)
    if u:
        session["user"] = {
            "id": u["id"], "full_name": u["full_name"],
            "email": u["email"], "profile_picture": u["profile_picture"]
        }
        session.modified = True

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── controller ────────────────────────────────────────────────────────────────

class AuthController:

    # ── AUTH ──────────────────────────────────────────────────────────────────

    def login(self):
        if session.get("user"):
            return redirect(url_for("auth.dashboard"))
        if request.method == "POST":
            email    = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            user = User.verify(mysql, email, password)
            if user:
                session["user"] = user
                session.modified = True
                flash(f"Welcome back, {user['full_name']}! 👋", "success")
                return redirect(url_for("auth.dashboard"))
            flash("Invalid email or password.", "error")
        return render_template("login.html", cart_count=_cart_count())

    def register(self):
        if session.get("user"):
            return redirect(url_for("auth.dashboard"))
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email     = request.form.get("email", "").strip()
            password  = request.form.get("password", "")
            confirm   = request.form.get("confirm_password", "")
            if not full_name or not email or not password:
                flash("All fields are required.", "error")
            elif password != confirm:
                flash("Passwords do not match.", "error")
            elif len(password) < 6:
                flash("Password must be at least 6 characters.", "error")
            else:
                ok, msg = User.create(mysql, full_name, email, password)
                flash(msg + (" Please log in." if ok else ""), "success" if ok else "error")
                if ok:
                    return redirect(url_for("auth.login"))
        return render_template("register.html", cart_count=_cart_count())

    def logout(self):
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("auth.login"))

    # ── PROFILE ───────────────────────────────────────────────────────────────

    def profile(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        full_user = User.get_by_id(mysql, user["id"])
        return render_template("profile.html", user=full_user,
                               cart_count=_cart_count())

    def edit_profile(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email     = request.form.get("email", "").strip()
            if not full_name or not email:
                flash("Name and email are required.", "error")
            else:
                ok, msg = User.update_profile(mysql, user["id"], full_name, email)
                flash(msg, "success" if ok else "error")
                if ok:
                    _refresh_user_session(user["id"])
                    return redirect(url_for("auth.profile"))

        full_user = User.get_by_id(mysql, user["id"])
        return render_template("edit_profile.html", user=full_user,
                               cart_count=_cart_count())

    def upload_picture(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))

        file = request.files.get("profile_picture")
        if not file or file.filename == "":
            flash("No file selected.", "error")
            return redirect(url_for("auth.profile"))

        if not _allowed(file.filename):
            flash("Only image files are allowed (png, jpg, jpeg, gif, webp).", "error")
            return redirect(url_for("auth.profile"))

        ext      = file.filename.rsplit('.', 1)[1].lower()
        filename = f"user_{user['id']}.{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        User.update_picture(mysql, user["id"], filename)
        _refresh_user_session(user["id"])
        flash("Profile picture updated!", "success")
        return redirect(url_for("auth.profile"))

    def change_password(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))

        if request.method == "POST":
            old_pw  = request.form.get("old_password", "")
            new_pw  = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not old_pw or not new_pw:
                flash("All fields are required.", "error")
            elif new_pw != confirm:
                flash("New passwords do not match.", "error")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "error")
            else:
                ok, msg = User.change_password(mysql, user["id"], old_pw, new_pw)
                flash(msg, "success" if ok else "error")
                if ok:
                    return redirect(url_for("auth.profile"))

        return render_template("change_password.html", cart_count=_cart_count(),
                               user=_current_user())

    def forgot_password(self):
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            token = User.create_reset_token(mysql, email)
            # Always show success to avoid email enumeration
            # In production: email the reset link. For now: show it as flash.
            if token:
                reset_url = url_for("auth.reset_password", token=token, _external=True)
                flash(f"Reset link (share this with the user): {reset_url}", "success")
            else:
                flash("If that email exists, a reset link has been generated.", "success")
            return redirect(url_for("auth.forgot_password"))
        return render_template("forgot_password.html", cart_count=_cart_count())

    def reset_password(self, token):
        user_id = User.verify_reset_token(mysql, token)
        if not user_id:
            flash("This reset link is invalid or has expired.", "error")
            return redirect(url_for("auth.forgot_password"))

        if request.method == "POST":
            new_pw  = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            if not new_pw:
                flash("Password cannot be empty.", "error")
            elif new_pw != confirm:
                flash("Passwords do not match.", "error")
            elif len(new_pw) < 6:
                flash("Password must be at least 6 characters.", "error")
            else:
                ok, msg = User.reset_password(mysql, token, new_pw)
                flash(msg, "success" if ok else "error")
                if ok:
                    return redirect(url_for("auth.login"))

        return render_template("reset_password.html", token=token,
                               cart_count=_cart_count())

    # ── PAGES ─────────────────────────────────────────────────────────────────

    def dashboard(self):
        search = request.args.get("search", "").strip()
        if search:
            filtered_products = [
                p for p in products
                if search.lower() in p["name"].lower()
                or search.lower() in p["category"].lower()
            ]
            matching_categories = [
                c for c in categories
                if search.lower() in c["name"].lower()
                or any(search.lower() in prod.lower() for prod in c["products"])
            ]
        else:
            filtered_products   = products
            matching_categories = []
        return render_template("dashboard.html", products=filtered_products,
                               matching_categories=matching_categories,
                               cart_count=_cart_count(), user=_current_user())

    def all_categories(self):
        return render_template("all_categories.html", categories=categories,
                               cart_count=_cart_count(), user=_current_user())

    def single_category(self, category):
        sort     = request.args.get("sort", "popular")
        filtered = [p for p in products if p["category"] == category]
        if sort == "low":
            filtered.sort(key=lambda x: x["price"])
        elif sort == "high":
            filtered.sort(key=lambda x: x["price"], reverse=True)
        return render_template("single_category.html", products=filtered,
                               category=category, sort=sort,
                               cart_count=_cart_count(), user=_current_user())

    def view_product(self, id):
        product = next((p for p in products if p["id"] == id), None)
        return render_template("view_product.html", product=product,
                               cart_count=_cart_count(), user=_current_user())

    def order_details(self):
        return render_template("order_details.html", cart_count=_cart_count())

    # ── CART ──────────────────────────────────────────────────────────────────

    def cart(self):
        session.pop("buy_now", None)
        session.modified = True
        cart = session.get("cart", {})
        return render_template("cart.html", cart=cart, products=product_map,
                               cart_count=_cart_count(), user=_current_user())

    def add_to_cart(self, product_id):
        if not session.get("user"):
            flash("Please log in to add items to your cart.", "error")
            return redirect(url_for("auth.login"))
        cart      = session.get("cart", {})
        pid       = str(product_id)
        qty       = int(request.form.get("quantity", 1))
        cart[pid] = cart.get(pid, 0) + qty
        session["cart"] = cart
        session.modified = True
        flash("Added to cart!", "success")
        return redirect(url_for("auth.view_product", id=product_id))

    def update_cart(self, product_id):
        cart   = session.get("cart", {})
        pid    = str(product_id)
        action = request.form.get("action")
        if pid in cart:
            if action == "increase":
                cart[pid] += 1
            elif action == "decrease":
                cart[pid] -= 1
                if cart[pid] <= 0:
                    cart.pop(pid)
        session["cart"] = cart
        session.modified = True
        return redirect(url_for("auth.cart"))

    def remove_from_cart(self, product_id):
        cart = session.get("cart", {})
        cart.pop(str(product_id), None)
        session["cart"] = cart
        session.modified = True
        flash("Item removed from cart.", "success")
        return redirect(url_for("auth.cart"))

    # ── BUY NOW ───────────────────────────────────────────────────────────────

    def buy_now(self, product_id):
        if not session.get("user"):
            flash("Please log in to purchase.", "error")
            return redirect(url_for("auth.login"))
        p = product_map.get(str(product_id))
        if not p:
            flash("Product not found.", "error")
            return redirect(url_for("auth.dashboard"))
        qty = int(request.form.get("quantity", 1))
        session["buy_now"] = {
            "id": p["id"], "name": p["name"], "price": p["price"],
            "image": p["image"], "qty": qty, "subtotal": p["price"] * qty
        }
        session.modified = True
        return redirect(url_for("auth.checkout"))

    # ── CHECKOUT ──────────────────────────────────────────────────────────────

    def checkout(self):
        if not session.get("user"):
            flash("Please log in to checkout.", "error")
            return redirect(url_for("auth.login"))
        buy_now = session.get("buy_now")
        cart    = session.get("cart", {})
        if buy_now:
            items = [buy_now]
            total = buy_now["subtotal"]
        elif cart:
            session.pop("buy_now", None)
            session.modified = True
            items = _build_items_snapshot(cart)
            total = _calc_total(items)
        else:
            flash("Nothing to checkout.", "error")
            return redirect(url_for("auth.dashboard"))
        return render_template("checkout.html", items=items, total=total,
                               cart_count=_cart_count(), user=_current_user())

    def place_order(self):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        buy_now = session.get("buy_now")
        cart    = session.get("cart", {})
        if buy_now:
            items = [buy_now]
        elif cart:
            items = _build_items_snapshot(cart)
        else:
            return redirect(url_for("auth.dashboard"))
        total          = _calc_total(items)
        payment_method = request.form.get("payment")
        order_data = {
            "user_id":  session["user"]["id"],
            "name":     request.form.get("name"),
            "phone":    request.form.get("phone"),
            "province": request.form.get("province"),
            "district": request.form.get("district"),
            "city":     request.form.get("city"),
            "area":     request.form.get("area"),
            "address":  request.form.get("address"),
            "landmark": request.form.get("landmark", ""),
            "payment":  payment_method,
            "total":    total,
            "items":    items,
        }
        order_id = Order.create(mysql, order_data)
        session.pop("buy_now", None)
        session["cart"] = {}
        session.modified = True
        session["last_order_total"] = total
        if payment_method in ("esewa", "khalti"):
            return redirect(url_for("auth.payment", method=payment_method))
        return redirect(url_for("auth.order_confirmed", order_id=order_id))

    # ── PAYMENT ───────────────────────────────────────────────────────────────

    def payment(self, method):
        qr_codes = {"esewa": "images/esewa_qr.png", "khalti": "images/khalti_qr.png"}
        total = session.pop("last_order_total", None)
        return render_template("payment.html", method=method,
                               qr=qr_codes.get(method), total=total,
                               cart_count=_cart_count(), user=_current_user())

    # ── ORDERS ────────────────────────────────────────────────────────────────

    def order_confirmed(self, order_id):
        order = Order.get_by_id(mysql, order_id)
        return render_template("order_confirmed.html", order=order,
                               cart_count=_cart_count(), user=_current_user())

    def view_my_orders(self):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        orders = Order.get_all_by_user(mysql, session["user"]["id"])
        return render_template("view_my_orders.html", orders=orders,
                               cart_count=_cart_count(), user=_current_user())

    def cancel_order(self, order_id):
        result = Order.cancel(mysql, order_id)
        flash("Order cancelled successfully." if result
              else "This order cannot be cancelled.",
              "success" if result else "error")
        return redirect(url_for("auth.view_my_orders"))


auth_controller = AuthController()
