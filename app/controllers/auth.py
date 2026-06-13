import os
from functools import wraps
from flask import render_template, session, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order
from app.models.user import User
from app.models.wishlist import Wishlist
from app.models.flash_sale import FlashSale
from app.extensions import mysql, mail

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'static', 'profile_pics')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def _build_items_snapshot(cart):
    items = []
    stale_pids = []
    sale_map = _get_sale_map()
    for pid, qty in cart.items():
        p = Product.get_by_id(mysql, int(pid))
        if p:
            sale = sale_map.get(p["id"])
            price = sale["sale_price"] if sale else p["price"]
            items.append({
                "id": p["id"], "name": p["name"], "price": price,
                "original_price": p["price"],
                "on_sale": bool(sale),
                "image": p["image"], "qty": qty, "subtotal": price * qty
            })
        else:
            stale_pids.append(pid)
    if stale_pids:
        for pid in stale_pids:
            cart.pop(pid, None)
        session["cart"] = cart
        session.modified = True
    return items

def _calc_total(items):
    return sum(i["subtotal"] for i in items)

def _cart_count():
    return sum(session.get("cart", {}).values())

def _get_sale_map():
    return FlashSale.get_sale_map(mysql)

def _current_user():
    return session.get("user")

def _refresh_user_session(user_id):
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
            return redirect(url_for("auth.home"))
        if request.method == "POST":
            email    = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            user = User.verify(mysql, email, password)
            if user == "blocked":
                flash("Your account has been suspended. Please contact support.", "error")
                return render_template("login.html", cart_count=_cart_count())
            if user:
                full = User.get_by_id(mysql, user["id"])
                session["user"] = {
                    "id":              full["id"],
                    "full_name":       full["full_name"],
                    "email":           full["email"],
                    "profile_picture": full["profile_picture"]
                }
                session.modified = True
                flash(f"{user['full_name']} logged in successfully.", "success")
                return redirect(url_for("auth.home"))
            flash("Invalid email or password.", "error")
        return render_template("login.html", cart_count=_cart_count())

    def register(self):
        if session.get("user"):
            return redirect(url_for("auth.home"))
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
        name = (session.get('user') or {}).get('full_name', 'User')
        session.clear()
        flash(f"{name} logged out successfully.", "success")
        return redirect(url_for("auth.login"))

    # ── PROFILE ───────────────────────────────────────────────────────────────

    def profile(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        full_user = User.get_by_id(mysql, user["id"])
        return render_template("profile.html", user=full_user, cart_count=_cart_count())

    def edit_profile(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email     = user["email"]  # email is not changeable
            if not full_name:
                flash("Name and email are required.", "error")
            else:
                ok, msg = User.update_profile(mysql, user["id"], full_name, email)
                flash(msg, "success" if ok else "error")
                if ok:
                    _refresh_user_session(user["id"])
                    return redirect(url_for("auth.profile"))
        full_user = User.get_by_id(mysql, user["id"])
        return render_template("edit_profile.html", user=full_user, cart_count=_cart_count())

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

        # Delete the previous profile picture if it exists (extension may differ)
        old_pic = user.get("profile_picture")
        if old_pic:
            old_path = os.path.join(UPLOAD_FOLDER, old_pic)
            if os.path.isfile(old_path) and old_path != os.path.join(UPLOAD_FOLDER, filename):
                os.remove(old_path)

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
        return render_template("change_password.html", cart_count=_cart_count(), user=_current_user())

    def forgot_password(self):
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            token = User.create_reset_token(mysql, email)
            if token == "google_account":
                flash("This account uses Google login. Please sign in with Google instead.", "error")
                return redirect(url_for("auth.forgot_password"))
            if token:
                reset_url = url_for("auth.reset_password", token=token, _external=True)
                from flask_mail import Message
                msg = Message(subject="MeroPasal — Password Reset Request", recipients=[email])
                msg.body = f"""Hi,\n\nYou requested a password reset for your MeroPasal account.\n\nClick the link below to reset your password (valid for 1 hour):\n\n{reset_url}\n\nIf you did not request this, you can safely ignore this email.\n\n— MeroPasal Team"""
                msg.html = f"""<p>Hi,</p><p>You requested a password reset for your <strong>MeroPasal</strong> account.</p>
<p><a href="{reset_url}" style="background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;display:inline-block;">Reset My Password</a></p>
<p>This link is valid for <strong>1 hour</strong>. If you did not request this, ignore this email.</p><p>— MeroPasal Team</p>"""
                try:
                    mail.send(msg)
                    flash("A password reset link has been sent to your email.", "success")
                except Exception:
                    flash("Could not send email. Please try again later.", "error")
            else:
                flash("If that email exists, a reset link has been sent.", "success")
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
        return render_template("reset_password.html", token=token, cart_count=_cart_count())

    # ── PAGES ─────────────────────────────────────────────────────────────────

    def home(self):
        search = request.args.get("search", "").strip()
        sort   = request.args.get("sort", "popular")
        if not search:
            filtered_products   = Product.get_all(mysql)
            matching_categories = []
        else:
            filtered_products   = Product.search(mysql, search)
            all_cats = Category.get_all(mysql)
            matching_categories = [c for c in all_cats if search.lower() in c["name"].lower()]
        if search:
            if sort == "low":
                filtered_products = sorted(filtered_products, key=lambda x: x["price"])
            elif sort == "high":
                filtered_products = sorted(filtered_products, key=lambda x: x["price"], reverse=True)
        sales    = FlashSale.get_active(mysql)
        sale_map = {s["product_id"]: s for s in sales}
        return render_template("home_page.html", products=filtered_products,
                               matching_categories=matching_categories, sort=sort,
                               flash_sales=sales, sale_map=sale_map,
                               cart_count=_cart_count(), user=_current_user())

    def all_categories(self):
        return render_template("all_categories.html", categories=Category.get_all(mysql),
                               cart_count=_cart_count(), user=_current_user())

    def single_category(self, category):
        sort     = request.args.get("sort", "popular")
        filtered = Product.get_by_category(mysql, category)
        if sort == "low":
            filtered.sort(key=lambda x: x["price"])
        elif sort == "high":
            filtered.sort(key=lambda x: x["price"], reverse=True)
        return render_template("single_category.html", products=filtered,
                               category=category, sort=sort,
                               sale_map=_get_sale_map(),
                               cart_count=_cart_count(), user=_current_user())

    def view_product(self, id):
        product  = Product.get_by_id(mysql, id)
        sale_map = _get_sale_map()
        sale     = sale_map.get(product["id"]) if product else None
        return render_template("view_product.html", product=product, sale=sale,
                               cart_count=_cart_count(), user=_current_user())

    def view_product_json(self, id):
        from flask import jsonify
        product  = Product.get_by_id(mysql, id)
        if not product:
            return jsonify({"error": "Not found"}), 404
        sale_map = _get_sale_map()
        sale     = sale_map.get(product["id"])
        data = {
            "id":          product["id"],
            "name":        product["name"],
            "price":       float(product["price"]),
            "image":       product["image"],
            "description": product.get("description", ""),
            "category":    product.get("category", ""),
            "sale_price":  float(sale["sale_price"]) if sale else None,
            "discount":    int(sale["discount"])     if sale else None,
        }
        return jsonify(data)

    def categories_json(self):
        from flask import jsonify
        cats = Category.get_all(mysql)
        result = []
        for c in cats:
            result.append({
                "id":    c["id"],
                "name":  c["name"],
                "image": ("/static/" + c["image"]) if c.get("image") else "",
            })
        return jsonify(result)

    def order_details(self, order_id):
        user = _current_user()
        if not user:
            flash("Please log in to view order details.", "warning")
            return redirect(url_for("auth.login"))
        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user["id"]:
            flash("Order not found.", "danger")
            return redirect(url_for("auth.view_my_orders"))
        return render_template("order_details.html", order=order, cart_count=_cart_count())

    def order_details_json(self, order_id):
        """JSON endpoint for the order detail drawer on My Orders page."""
        from flask import jsonify
        user = _current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        order = Order.get_by_id(mysql, order_id)
        if not order or order["user_id"] != user["id"]:
            return jsonify({"error": "Not found"}), 404
        items = []
        for it in (order.get("order_items") or []):
            items.append({
                "name":     it.get("name", ""),
                "image":    it.get("image", ""),
                "qty":      it.get("qty", 1),
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

    # __ CART ──────────────────────────────────────────────────────────────────

    def cart(self):
        session.pop("buy_now", None)
        session.modified = True
        cart     = session.get("cart", {})
        sale_map = _get_sale_map()
        product_map = {}
        stale_pids  = []
        for pid in cart:
            p = Product.get_by_id(mysql, int(pid))
            if p:
                sale = sale_map.get(p["id"])
                if sale:
                    p["sale_price"]     = sale["sale_price"]
                    p["discount"]       = sale["discount"]
                    p["original_price"] = p["price"]
                    p["on_sale"]        = True
                else:
                    p["on_sale"] = False
                product_map[pid] = p
            else:
                stale_pids.append(pid)
        if stale_pids:
            for pid in stale_pids:
                cart.pop(pid, None)
            session["cart"] = cart
            session.modified = True
            flash(f"{len(stale_pids)} item(s) were removed from your cart because they are no longer available.", "error")
        return render_template("cart.html", cart=cart, products=product_map,
                               cart_count=_cart_count(), user=_current_user())

    def add_to_cart(self, product_id):
        if not session.get("user"):
            flash("Please log in to add items to your cart.", "error")
            return redirect(url_for("auth.login"))
        product = Product.get_by_id(mysql, product_id)
        if not product:
            flash("Product not found.", "error")
            return redirect(url_for("auth.home"))
        if product["available"] == 0:
            flash(f"Sorry, {product['name']} is out of stock.", "error")
            return redirect(url_for("auth.view_product", id=product_id))
        cart    = session.get("cart", {})
        pid     = str(product_id)
        qty     = int(request.form.get("quantity", 1))
        new_qty = cart.get(pid, 0) + qty
        if new_qty > product["available"]:
            flash(f"Only {product['available']} unit(s) available.", "error")
            new_qty = product["available"]
        cart[pid] = new_qty
        session["cart"] = cart
        session.modified = True
        # Remove from wishlist if present
        if session.get("user"):
            Wishlist.remove(mysql, session["user"]["id"], product_id)
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
        p = Product.get_by_id(mysql, product_id)
        if not p:
            flash("Product not found.", "error")
            return redirect(url_for("auth.home"))
        sale_map = _get_sale_map()
        sale = sale_map.get(p["id"])
        price = sale["sale_price"] if sale else p["price"]
        qty = int(request.form.get("quantity", 1))
        session["buy_now"] = {
            "id": p["id"], "name": p["name"], "price": price,
            "original_price": p["price"], "on_sale": bool(sale),
            "image": p["image"], "qty": qty, "subtotal": price * qty
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
            return redirect(url_for("auth.home"))
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
            return redirect(url_for("auth.home"))
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

        if payment_method in ("esewa", "khalti"):
            # Don't create order yet — hold data in session until payment code is submitted
            session["pending_order_data"] = order_data
            session["last_order_total"]   = total
            session.modified = True
            return redirect(url_for("auth.payment", method=payment_method))

        # COD — create order immediately
        order_id, failed = Order.create(mysql, order_data)
        if failed:
            flash(f"Sorry, the following item(s) are out of stock: {', '.join(failed)}. Please update your cart.", "error")
            return redirect(url_for("auth.cart"))

        session.pop("buy_now", None)
        session["cart"] = {}
        session.modified = True
        return redirect(url_for("auth.order_confirmed", order_id=order_id))

    # ── PAYMENT ───────────────────────────────────────────────────────────────

    def payment(self, method):
        qr_codes = {"esewa": "images/esewa_qr.png", "khalti": "images/khalti_qr.png"}
        total    = session.get("last_order_total", None)
        order_id = session.get("last_order_id", None)
        return render_template("payment.html", method=method,
                               qr=qr_codes.get(method), total=total,
                               order_id=order_id,
                               cart_count=_cart_count(), user=_current_user())

    def submit_payment(self):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        transaction_code = request.form.get("transaction_code", "").strip()
        if not transaction_code:
            flash("Please enter your transaction code.", "error")
            return redirect(url_for("auth.view_my_orders"))

        order_data = session.get("pending_order_data")
        if not order_data:
            flash("Session expired. Please place your order again.", "error")
            return redirect(url_for("auth.cart"))

        # Now create the order in DB
        order_id, failed = Order.create(mysql, order_data)
        if failed:
            flash(f"Sorry, the following item(s) are out of stock: {', '.join(failed)}. Please update your cart.", "error")
            session.pop("pending_order_data", None)
            session.modified = True
            return redirect(url_for("auth.cart"))

        # Save transaction code
        cursor = mysql.connection.cursor()
        cursor.execute(
            "UPDATE orders SET transaction_code=%s WHERE id=%s",
            (transaction_code, order_id)
        )
        mysql.connection.commit()

        # Clear session
        session.pop("pending_order_data", None)
        session.pop("buy_now", None)
        session["cart"] = {}
        session.modified = True

        flash("Payment submitted! We'll verify your transaction code and confirm your order.", "success")
        return redirect(url_for("auth.order_confirmed", order_id=order_id))

    # ── ORDERS ────────────────────────────────────────────────────────────────

    def order_confirmed(self, order_id):
        user  = _current_user()
        order = Order.get_by_id(mysql, order_id)
        if not order or (user and order["user_id"] != user["id"]):
            flash("Order not found.", "error")
            return redirect(url_for("auth.home"))
        return render_template("order_confirmed.html", order=order,
                               cart_count=_cart_count(), user=user)

    def view_my_orders(self):
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        orders = Order.get_all_by_user(mysql, session["user"]["id"])
        return render_template("view_my_orders.html", orders=orders,
                               cart_count=_cart_count(), user=_current_user())

    def cancel_order(self, order_id):
        user = _current_user()
        if not user:
            return redirect(url_for("auth.login"))
        result = Order.cancel(mysql, order_id, user["id"])
        flash("Order cancelled successfully." if result else "This order cannot be cancelled.",
              "success" if result else "error")
        return redirect(url_for("auth.view_my_orders"))

    # ── SEARCH ────────────────────────────────────────────────────────────────

    def search_suggest(self):
        q = request.args.get("q", "").strip().lower()
        if len(q) < 1:
            return jsonify([])
        suggestions = []
        for p in Product.search(mysql, q):
            suggestions.append({"label": p["name"], "type": "product",
                                "url": url_for("auth.view_product", id=p["id"])})
        for c in Category.get_all(mysql):
            if q in c["name"].lower():
                suggestions.append({"label": c["name"].title(), "type": "category",
                                    "url": url_for("auth.single_category", category=c["name"])})
        return jsonify(suggestions[:10])

    # ── WISHLIST ──────────────────────────────────────────────────────────────

    def view_wishlist(self):
        user = _current_user()
        if not user:
            flash("Please log in to view your wishlist.", "error")
            return redirect(url_for("auth.login"))
        product_ids       = Wishlist.get_product_ids(mysql, user["id"])
        wishlist_products = [p for pid in product_ids
                             for p in [Product.get_by_id(mysql, pid)] if p]
        return render_template("wishlist.html",
                               wishlist_products=wishlist_products,
                               wishlist_count=len(wishlist_products),
                               sale_map=_get_sale_map(),
                               cart_count=_cart_count(),
                               user=user)

    def toggle_wishlist(self, product_id):
        user = _current_user()
        if not user:
            return jsonify({"success": False, "error": "login_required"}), 401
        if not Product.get_by_id(mysql, product_id):
            return jsonify({"success": False, "error": "Product not found"}), 404
        already = Wishlist.is_wishlisted(mysql, user["id"], product_id)
        if already:
            Wishlist.remove(mysql, user["id"], product_id)
            wishlisted = False
            message    = "Removed from wishlist"
        else:
            Wishlist.add(mysql, user["id"], product_id)
            wishlisted = True
            message    = "Added to wishlist"
        count = Wishlist.get_count(mysql, user["id"])
        return jsonify({"success": True, "wishlisted": wishlisted,
                        "message": message, "wishlist_count": count})

    def wishlist_status(self, product_id):
        user = _current_user()
        if not user:
            return jsonify({"wishlisted": False, "wishlist_count": 0})
        count = Wishlist.get_count(mysql, user["id"])
        if product_id == 0:
            return jsonify({"wishlisted": False, "wishlist_count": count})
        wishlisted = Wishlist.is_wishlisted(mysql, user["id"], product_id)
        return jsonify({"wishlisted": wishlisted, "wishlist_count": count})