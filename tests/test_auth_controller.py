"""
Comprehensive tests for app/controllers/auth.py (AuthController).

Covers every public method on AuthController: auth, profile, password-reset/OTP,
pages, cart, buy-now, checkout, payment, orders, search, wishlist, reviews,
coupons, and refunds — plus the module-level helper functions.

Run with:
    pytest tests/test_auth_controller.py -v
or:
    python -m unittest tests.test_auth_controller -v
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# The project ships a Windows venv inside the repo (venv/Lib/site-packages) that
# contains flask_mysqldb / flask_mail / flask_wtf / pymysql — none of which are
# on the system interpreter. Make them importable without needing network access.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_VENDORED_SITE_PACKAGES = os.path.join(_PROJECT_ROOT, "venv", "Lib", "site-packages")
if os.path.isdir(_VENDORED_SITE_PACKAGES) and _VENDORED_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, _VENDORED_SITE_PACKAGES)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask

from app.routes.authroute import auth_bp
from app.controllers import auth as auth_module
from app.extensions import csrf, mail


def make_app():
    """Build a minimal Flask app around the real auth blueprint, without
    touching a real database (no create_app(), no init_table calls)."""
    app = Flask(
        __name__,
        template_folder=os.path.join(_PROJECT_ROOT, "app", "templates"),
        static_folder=os.path.join(_PROJECT_ROOT, "app", "static"),
    )
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        WTF_CSRF_ENABLED=False,
        MAIL_SUPPRESS_SEND=True,
        SERVER_NAME="localhost",
    )
    csrf.init_app(app)  # registers csrf_token() in the Jinja context, used by base.html
    mail.init_app(app)
    app.register_blueprint(auth_bp)

    # Templates reference url_for('google.login') / 'google.authorized' for the
    # "Sign in with Google" button. We don't exercise OAuth here, so register a
    # tiny stub blueprint purely so url_for() resolves inside rendered templates.
    from flask import Blueprint
    google_stub = Blueprint("google", __name__)
    google_stub.add_url_rule("/login/google", "login", lambda: "", methods=["GET"])
    app.register_blueprint(google_stub)

    return app


class AuthControllerTestCase(unittest.TestCase):
    """Base class: fresh app + client per test, plus small helpers."""

    def setUp(self):
        self.app = make_app()
        self.client = self.app.test_client()

    def login_session(self, user_id=1, full_name="Jane Doe",
                       email="jane@example.com", profile_picture=None):
        with self.client.session_transaction() as sess:
            sess["user"] = {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "profile_picture": profile_picture,
            }
        return {"id": user_id, "full_name": full_name, "email": email,
                "profile_picture": profile_picture}

    def get_flashes(self):
        with self.client.session_transaction() as sess:
            return sess.get("_flashes", [])

    def assert_flash_rendered(self, resp, text):
        """Assert a flash message containing `text` was rendered into the page.
        (Flashes are popped by base.html's get_flashed_messages() during
        render_template, so by the time the response comes back the session no
        longer holds them — we have to look in the rendered HTML instead.)"""
        html = resp.get_data(as_text=True)
        self.assertIn(text, html)


# ───────────────────────────── HELPER FUNCTIONS ──────────────────────────────

class HelperFunctionTests(AuthControllerTestCase):

    def test_allowed_accepts_known_extensions(self):
        for name in ("a.png", "a.JPG", "a.jpeg", "a.gif", "a.webp"):
            self.assertTrue(auth_module._allowed(name))

    def test_allowed_rejects_unknown_or_missing_extension(self):
        self.assertFalse(auth_module._allowed("a.exe"))
        self.assertFalse(auth_module._allowed("no_extension"))

    def test_calc_total_sums_subtotals(self):
        items = [{"subtotal": 10}, {"subtotal": 5.5}]
        self.assertEqual(auth_module._calc_total(items), 15.5)

    def test_calc_total_empty(self):
        self.assertEqual(auth_module._calc_total([]), 0)

    def test_cart_count_sums_quantities(self):
        with self.app.test_request_context():
            from flask import session
            session["cart"] = {"1": 2, "2": 3}
            self.assertEqual(auth_module._cart_count(), 5)

    def test_cart_count_defaults_to_zero(self):
        with self.app.test_request_context():
            self.assertEqual(auth_module._cart_count(), 0)

    def test_current_user_returns_session_user(self):
        with self.app.test_request_context():
            from flask import session
            session["user"] = {"id": 1}
            self.assertEqual(auth_module._current_user(), {"id": 1})

    def test_current_user_none_when_absent(self):
        with self.app.test_request_context():
            self.assertIsNone(auth_module._current_user())

    @patch("app.controllers.auth.User")
    def test_refresh_user_session_updates_session_when_user_found(self, mock_user):
        mock_user.get_by_id.return_value = {
            "id": 1, "full_name": "Jane", "email": "j@x.com", "profile_picture": "p.png"
        }
        with self.app.test_request_context():
            from flask import session
            auth_module._refresh_user_session(1)
            self.assertEqual(session["user"]["full_name"], "Jane")
            self.assertEqual(session["user"]["profile_picture"], "p.png")

    @patch("app.controllers.auth.User")
    def test_refresh_user_session_noop_when_user_missing(self, mock_user):
        mock_user.get_by_id.return_value = None
        with self.app.test_request_context():
            from flask import session
            auth_module._refresh_user_session(999)
            self.assertNotIn("user", session)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_build_items_snapshot_applies_sale_price(self, mock_product, mock_flashsale):
        mock_flashsale.get_sale_map.return_value = {7: {"sale_price": 80, "discount": 20}}
        mock_product.get_by_id.return_value = {
            "id": 7, "name": "Widget", "price": 100, "image": "w.png"
        }
        with self.app.test_request_context():
            items = auth_module._build_items_snapshot({"7": 2})
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertTrue(item["on_sale"])
        self.assertEqual(item["price"], 80)
        self.assertEqual(item["original_price"], 100)
        self.assertEqual(item["subtotal"], 160)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_build_items_snapshot_drops_stale_products(self, mock_product, mock_flashsale):
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = None
        with self.app.test_request_context():
            from flask import session
            session["cart"] = {"99": 1}
            items = auth_module._build_items_snapshot(session["cart"])
            self.assertEqual(items, [])
            self.assertEqual(session["cart"], {})

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_refresh_buy_now_returns_none_for_empty_input(self, mock_product, mock_flashsale):
        self.assertIsNone(auth_module._refresh_buy_now(None))
        self.assertIsNone(auth_module._refresh_buy_now({}))

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_refresh_buy_now_returns_none_when_product_gone(self, mock_product, mock_flashsale):
        mock_product.get_by_id.return_value = None
        self.assertIsNone(auth_module._refresh_buy_now({"id": 1, "qty": 2}))

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_refresh_buy_now_recomputes_price_from_current_sale(self, mock_product, mock_flashsale):
        mock_flashsale.get_sale_map.return_value = {5: {"sale_price": 40}}
        mock_product.get_by_id.return_value = {"id": 5, "name": "X", "price": 50, "image": "x.png"}
        result = auth_module._refresh_buy_now({"id": 5, "qty": 3})
        self.assertEqual(result["price"], 40)
        self.assertEqual(result["subtotal"], 120)
        self.assertTrue(result["on_sale"])


# ───────────────────────────────────── AUTH ──────────────────────────────────

class LoginTests(AuthControllerTestCase):

    def test_get_shows_login_form(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)

    def test_already_logged_in_redirects_home(self):
        self.login_session()
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location) or self.assertIn("/", resp.location)

    @patch("app.controllers.auth.User")
    def test_post_blocked_account(self, mock_user):
        mock_user.verify.return_value = "blocked"
        resp = self.client.post("/login", data={"email": "a@a.com", "password": "secret"})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "suspended")

    @patch("app.controllers.auth.User")
    def test_post_invalid_credentials(self, mock_user):
        mock_user.verify.return_value = None
        resp = self.client.post("/login", data={"email": "a@a.com", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "Invalid email or password")
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)

    @patch("app.controllers.auth.User")
    def test_post_success_sets_session_and_redirects(self, mock_user):
        mock_user.verify.return_value = {"id": 1, "full_name": "Jane Doe"}
        mock_user.get_by_id.return_value = {
            "id": 1, "full_name": "Jane Doe", "email": "jane@example.com",
            "profile_picture": None,
        }
        resp = self.client.post("/login", data={"email": "jane@example.com", "password": "secret"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"]["id"], 1)
            self.assertEqual(sess["user"]["full_name"], "Jane Doe")


class RegisterTests(AuthControllerTestCase):

    def test_get_shows_register_form(self):
        resp = self.client.get("/register")
        self.assertEqual(resp.status_code, 200)

    def test_already_logged_in_redirects_home(self):
        self.login_session()
        resp = self.client.get("/register")
        self.assertEqual(resp.status_code, 302)

    def test_post_missing_fields(self):
        resp = self.client.post("/register", data={"full_name": "", "email": "", "password": ""})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "All fields are required")

    def test_post_password_mismatch(self):
        resp = self.client.post("/register", data={
            "full_name": "Jane", "email": "j@x.com",
            "password": "secret1", "confirm_password": "secret2",
        })
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "do not match")

    def test_post_password_too_short(self):
        resp = self.client.post("/register", data={
            "full_name": "Jane", "email": "j@x.com",
            "password": "abc", "confirm_password": "abc",
        })
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "at least 6 characters")

    @patch("app.controllers.auth.User")
    def test_post_duplicate_email_does_not_redirect(self, mock_user):
        mock_user.create.return_value = (False, "Email already registered.")
        resp = self.client.post("/register", data={
            "full_name": "Jane", "email": "j@x.com",
            "password": "secret1", "confirm_password": "secret1",
        })
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "already registered")

    @patch("app.controllers.auth.User")
    def test_post_success_redirects_to_login(self, mock_user):
        mock_user.create.return_value = (True, "Account created.")
        resp = self.client.post("/register", data={
            "full_name": "Jane", "email": "j@x.com",
            "password": "secret1", "confirm_password": "secret1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)


class LogoutTests(AuthControllerTestCase):

    def test_clears_session_and_redirects(self):
        self.login_session(full_name="Jane Doe")
        resp = self.client.get("/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user", sess)
        self.assertTrue(any("logged out successfully" in f[1] for f in self.get_flashes()))

    def test_logout_with_no_session_user_uses_default_name(self):
        resp = self.client.get("/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(any("User logged out successfully" in f[1] for f in self.get_flashes()))


# ──────────────────────────────────── PROFILE ────────────────────────────────

class ProfileTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.User")
    def test_shows_profile_when_logged_in(self, mock_user):
        self.login_session()
        mock_user.get_by_id.return_value = {"id": 1, "full_name": "Jane Doe", "email": "jane@example.com"}
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)


class EditProfileTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/profile/edit")
        self.assertEqual(resp.status_code, 302)

    @patch("app.controllers.auth.User")
    def test_get_shows_form(self, mock_user):
        self.login_session()
        mock_user.get_by_id.return_value = {"id": 1, "full_name": "Jane Doe", "email": "jane@example.com"}
        resp = self.client.get("/profile/edit")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.User")
    def test_post_empty_name_rejected(self, mock_user):
        self.login_session()
        mock_user.get_by_id.return_value = {"id": 1, "full_name": "Jane Doe", "email": "jane@example.com"}
        resp = self.client.post("/profile/edit", data={"full_name": ""})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "Name is required")
        mock_user.update_profile.assert_not_called()

    @patch("app.controllers.auth.User")
    def test_post_success_refreshes_session_and_redirects(self, mock_user):
        self.login_session()
        mock_user.update_profile.return_value = (True, "Profile updated.")
        mock_user.get_by_id.return_value = {
            "id": 1, "full_name": "Jane Updated", "email": "jane@example.com",
            "profile_picture": None,
        }
        resp = self.client.post("/profile/edit", data={"full_name": "Jane Updated"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/profile", resp.location)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user"]["full_name"], "Jane Updated")

    @patch("app.controllers.auth.User")
    def test_post_failure_does_not_redirect(self, mock_user):
        self.login_session()
        mock_user.update_profile.return_value = (False, "Update failed.")
        mock_user.get_by_id.return_value = {"id": 1, "full_name": "Jane Doe", "email": "jane@example.com"}
        resp = self.client.post("/profile/edit", data={"full_name": "New Name"})
        self.assertEqual(resp.status_code, 200)


class UploadPictureTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/profile/upload_picture", data={})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_no_file_selected(self):
        self.login_session()
        resp = self.client.post("/profile/upload_picture", data={}, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(any("No file selected" in f[1] for f in self.get_flashes()))

    def test_disallowed_extension_rejected(self):
        self.login_session()
        from io import BytesIO
        data = {"profile_picture": (BytesIO(b"data"), "virus.exe")}
        resp = self.client.post("/profile/upload_picture", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(any("Only image files are allowed" in f[1] for f in self.get_flashes()))

    @patch("app.controllers.auth.os.remove")
    @patch("app.controllers.auth.os.path.isfile", return_value=True)
    @patch("app.controllers.auth.User")
    def test_success_saves_file_and_updates_user(self, mock_user, mock_isfile, mock_remove):
        self.login_session(profile_picture="old.png")
        mock_user.get_by_id.return_value = {
            "id": 1, "full_name": "Jane", "email": "jane@example.com", "profile_picture": "new.png",
        }
        from io import BytesIO
        with patch("app.controllers.auth.os.path.join", side_effect=lambda *a: "/".join(a)):
            data = {"profile_picture": (BytesIO(b"fakeimagebytes"), "new.png")}
            resp = self.client.post("/profile/upload_picture", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 302)
        mock_user.update_picture.assert_called_once()
        self.assertTrue(any("Profile picture updated" in f[1] for f in self.get_flashes()))


class ChangePasswordTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/profile/change_password")
        self.assertEqual(resp.status_code, 302)

    @patch("app.controllers.auth.User")
    def test_google_only_account_blocked(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = True
        resp = self.client.get("/profile/change_password")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/profile", resp.location)
        self.assertTrue(any("Google" in f[1] for f in self.get_flashes()))

    @patch("app.controllers.auth.User")
    def test_post_missing_fields(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = False
        resp = self.client.post("/profile/change_password", data={"old_password": "", "new_password": ""})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "All fields are required")

    @patch("app.controllers.auth.User")
    def test_post_mismatched_new_passwords(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = False
        resp = self.client.post("/profile/change_password", data={
            "old_password": "old123", "new_password": "newpass1", "confirm_password": "newpass2",
        })
        self.assert_flash_rendered(resp, "do not match")

    @patch("app.controllers.auth.User")
    def test_post_new_password_too_short(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = False
        resp = self.client.post("/profile/change_password", data={
            "old_password": "old123", "new_password": "abc", "confirm_password": "abc",
        })
        self.assert_flash_rendered(resp, "at least 6 characters")

    @patch("app.controllers.auth.User")
    def test_post_success_redirects_to_profile(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = False
        mock_user.change_password.return_value = (True, "Password changed.")
        resp = self.client.post("/profile/change_password", data={
            "old_password": "old123", "new_password": "newpass1", "confirm_password": "newpass1",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/profile", resp.location)

    @patch("app.controllers.auth.User")
    def test_post_wrong_old_password_does_not_redirect(self, mock_user):
        self.login_session()
        mock_user.is_google_only.return_value = False
        mock_user.change_password.return_value = (False, "Old password is incorrect.")
        resp = self.client.post("/profile/change_password", data={
            "old_password": "wrong", "new_password": "newpass1", "confirm_password": "newpass1",
        })
        self.assertEqual(resp.status_code, 200)


# ───────────────────────────── PASSWORD RESET / OTP ──────────────────────────

class ForgotPasswordTests(AuthControllerTestCase):

    def test_get_shows_form(self):
        resp = self.client.get("/forgot_password")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.User")
    def test_post_google_only_account(self, mock_user):
        mock_user.create_otp.return_value = (None, "This account uses Google login — password reset is not available.")
        resp = self.client.post("/forgot_password", data={"email": "g@x.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/forgot_password", resp.location)

    @patch("app.controllers.auth.mail")
    @patch("app.controllers.auth.User")
    def test_post_otp_sent_renders_verify_page(self, mock_user, mock_mail):
        mock_user.create_otp.return_value = ("123456", None)
        mock_mail.send.return_value = None
        resp = self.client.post("/forgot_password", data={"email": "j@x.com"})
        self.assertEqual(resp.status_code, 200)
        mock_mail.send.assert_called_once()

    @patch("app.controllers.auth.mail")
    @patch("app.controllers.auth.User")
    def test_post_mail_send_failure(self, mock_user, mock_mail):
        mock_user.create_otp.return_value = ("123456", None)
        mock_mail.send.side_effect = Exception("smtp down")
        resp = self.client.post("/forgot_password", data={"email": "j@x.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/forgot_password", resp.location)

    @patch("app.controllers.auth.User")
    def test_post_unknown_email_shows_generic_message(self, mock_user):
        mock_user.create_otp.return_value = (None, None)
        resp = self.client.post("/forgot_password", data={"email": "nobody@x.com"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/forgot_password", resp.location)


class VerifyOtpTests(AuthControllerTestCase):

    def test_get_redirects_to_forgot_password(self):
        resp = self.client.get("/verify_otp")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/forgot_password", resp.location)

    @patch("app.controllers.auth.User")
    def test_post_invalid_otp(self, mock_user):
        mock_user.verify_otp.return_value = None
        resp = self.client.post("/verify_otp", data={"email": "j@x.com", "otp": "000000"})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "Invalid or expired OTP")

    @patch("app.controllers.auth.User")
    def test_post_valid_otp_redirects_to_reset_password(self, mock_user):
        mock_user.verify_otp.return_value = 1
        mock_user.create_reset_token.return_value = "tok123"
        resp = self.client.post("/verify_otp", data={"email": "j@x.com", "otp": "123456"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/reset_password/tok123", resp.location)


class ResetPasswordTests(AuthControllerTestCase):

    @patch("app.controllers.auth.User")
    def test_invalid_token_redirects(self, mock_user):
        mock_user.verify_reset_token.return_value = None
        resp = self.client.get("/reset_password/badtoken")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/forgot_password", resp.location)

    @patch("app.controllers.auth.User")
    def test_valid_token_shows_form(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        resp = self.client.get("/reset_password/goodtoken")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.User")
    def test_post_empty_password_rejected(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        resp = self.client.post("/reset_password/goodtoken", data={"new_password": "", "confirm_password": ""})
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "Password cannot be empty")

    @patch("app.controllers.auth.User")
    def test_post_mismatched_passwords(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        resp = self.client.post("/reset_password/goodtoken", data={
            "new_password": "abcdef", "confirm_password": "abcdeg",
        })
        self.assert_flash_rendered(resp, "Passwords do not match")

    @patch("app.controllers.auth.User")
    def test_post_too_short(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        resp = self.client.post("/reset_password/goodtoken", data={
            "new_password": "abc", "confirm_password": "abc",
        })
        self.assert_flash_rendered(resp, "at least 6 characters")

    @patch("app.controllers.auth.User")
    def test_post_success_redirects_to_login(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        mock_user.reset_password.return_value = (True, "Password reset.")
        resp = self.client.post("/reset_password/goodtoken", data={
            "new_password": "abcdef", "confirm_password": "abcdef",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.User")
    def test_post_failure_does_not_redirect(self, mock_user):
        mock_user.verify_reset_token.return_value = 1
        mock_user.reset_password.return_value = (False, "Token expired.")
        resp = self.client.post("/reset_password/goodtoken", data={
            "new_password": "abcdef", "confirm_password": "abcdef",
        })
        self.assertEqual(resp.status_code, 200)


# ──────────────────────────────────── PAGES ──────────────────────────────────

class HomeTests(AuthControllerTestCase):

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_no_search_lists_all_products(self, mock_product, mock_flashsale):
        mock_product.get_all.return_value = [{"id": 1, "name": "A", "price": 10}]
        mock_flashsale.get_active.return_value = []
        resp = self.client.get("/home")
        self.assertEqual(resp.status_code, 200)
        mock_product.get_all.assert_called_once()

    @patch("app.controllers.auth.Category")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_search_sorts_low_to_high(self, mock_product, mock_flashsale, mock_category):
        mock_product.search.return_value = [
            {"id": 1, "name": "B", "price": 30}, {"id": 2, "name": "A", "price": 10},
        ]
        mock_category.get_all.return_value = []
        mock_flashsale.get_active.return_value = []
        resp = self.client.get("/home?search=shirt&sort=low")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.Category")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_search_sorts_high_to_low(self, mock_product, mock_flashsale, mock_category):
        mock_product.search.return_value = [
            {"id": 1, "name": "B", "price": 30}, {"id": 2, "name": "A", "price": 10},
        ]
        mock_category.get_all.return_value = []
        mock_flashsale.get_active.return_value = []
        resp = self.client.get("/home?search=shirt&sort=high")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.Category")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_search_includes_matching_categories(self, mock_product, mock_flashsale, mock_category):
        mock_product.search.return_value = []
        mock_category.get_all.return_value = [{"id": 1, "name": "Shoes"}, {"id": 2, "name": "Hats"}]
        mock_flashsale.get_active.return_value = []
        resp = self.client.get("/home?search=shoe")
        self.assertEqual(resp.status_code, 200)


class AllCategoriesTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Product")
    @patch("app.controllers.auth.Category")
    def test_attaches_product_counts(self, mock_category, mock_product):
        mock_category.get_all.return_value = [{"id": 1, "name": "Shoes"}]
        mock_product.get_by_category.return_value = [{"name": "Nike"}, {"name": "Adidas"}]
        resp = self.client.get("/all_categories")
        self.assertEqual(resp.status_code, 200)


class SingleCategoryTests(AuthControllerTestCase):

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_sorts_low(self, mock_product, mock_flashsale):
        mock_product.get_by_category.return_value = [{"id": 1, "price": 30}, {"id": 2, "price": 10}]
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.get("/single_category/Shoes?sort=low")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_default_sort_popular(self, mock_product, mock_flashsale):
        mock_product.get_by_category.return_value = [{"id": 1, "price": 30}]
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.get("/single_category/Shoes")
        self.assertEqual(resp.status_code, 200)


class ViewProductTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Product")
    def test_404_when_not_found(self, mock_product):
        mock_product.get_by_id.return_value = None
        resp = self.client.get("/view_product/999")
        self.assertEqual(resp.status_code, 404)

    @patch("app.models.review.Review")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_renders_for_anonymous_user(self, mock_product, mock_flashsale, mock_review):
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shirt", "price": 20, "image": "s.png", "available": 10}
        mock_flashsale.get_sale_map.return_value = {}
        mock_review.get_for_product.return_value = []
        mock_review.get_avg_rating.return_value = (0, 0)
        resp = self.client.get("/view_product/1")
        self.assertEqual(resp.status_code, 200)

    @patch("app.models.review.Review")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_logged_in_user_can_review_when_eligible(self, mock_product, mock_flashsale, mock_review):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shirt", "price": 20, "image": "s.png", "available": 10}
        mock_flashsale.get_sale_map.return_value = {}
        mock_review.get_for_product.return_value = []
        mock_review.get_avg_rating.return_value = (0, 0)
        mock_review.get_user_review_for_product.return_value = None
        mock_review.can_review.return_value = True
        resp = self.client.get("/view_product/1")
        self.assertEqual(resp.status_code, 200)


class ViewProductJsonTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Product")
    def test_404_when_missing(self, mock_product):
        mock_product.get_by_id.return_value = None
        resp = self.client.get("/view_product/1/json")
        self.assertEqual(resp.status_code, 404)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_returns_sale_info(self, mock_product, mock_flashsale):
        mock_product.get_by_id.return_value = {
            "id": 1, "name": "Shirt", "price": 100, "image": "s.png",
            "description": "nice", "category": "tops",
        }
        mock_flashsale.get_sale_map.return_value = {1: {"sale_price": 80, "discount": 20}}
        resp = self.client.get("/view_product/1/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["sale_price"], 80.0)
        self.assertEqual(data["discount"], 20)


class CategoriesJsonTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Category")
    def test_returns_list_with_image_paths(self, mock_category):
        mock_category.get_all.return_value = [{"id": 1, "name": "Shoes", "image": "shoes.png"}]
        resp = self.client.get("/categories/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data[0]["image"], "/static/shoes.png")

    @patch("app.controllers.auth.Category")
    def test_missing_image_returns_empty_string(self, mock_category):
        mock_category.get_all.return_value = [{"id": 1, "name": "Shoes"}]
        resp = self.client.get("/categories/json")
        data = resp.get_json()
        self.assertEqual(data[0]["image"], "")


class OrderDetailsTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/order_details/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.Order")
    def test_not_found_redirects_to_my_orders(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = None
        resp = self.client.get("/order_details/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_my_orders", resp.location)

    @patch("app.controllers.auth.Order")
    def test_other_users_order_redirects(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {"id": 1, "user_id": 2}
        resp = self.client.get("/order_details/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_my_orders", resp.location)

    @patch("app.controllers.auth.Order")
    def test_owner_can_view(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {
            "id": 1, "user_id": 1, "total_price": 100, "order_status": "Pending",
            "customer_name": "Jane", "phone": "123", "payment_method": "cod",
            "order_items": [],
        }
        resp = self.client.get("/order_details/1")
        self.assertEqual(resp.status_code, 200)


class OrderDetailsJsonTests(AuthControllerTestCase):

    def test_requires_login_401(self):
        resp = self.client.get("/order_details/1/json")
        self.assertEqual(resp.status_code, 401)

    @patch("app.controllers.auth.Order")
    def test_404_for_missing_or_other_users_order(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {"id": 1, "user_id": 2}
        resp = self.client.get("/order_details/1/json")
        self.assertEqual(resp.status_code, 404)

    @patch("app.controllers.auth.Order")
    def test_returns_order_payload(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {
            "id": 1, "user_id": 1, "customer_name": "Jane", "phone": "123",
            "order_status": "Pending", "total_price": 50, "order_items": [
                {"name": "Shirt", "image": "s.png", "qty": 2, "subtotal": 40, "on_sale": False}
            ],
        }
        resp = self.client.get("/order_details/1/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["items"][0]["name"], "Shirt")
        self.assertEqual(data["created_at"], "")


# ───────────────────────────────────── CART ──────────────────────────────────

class CartPageTests(AuthControllerTestCase):

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_empty_cart(self, mock_product, mock_flashsale):
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.get("/cart")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_stale_items_are_removed_with_flash(self, mock_product, mock_flashsale):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"5": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = None
        resp = self.client.get("/cart")
        self.assertEqual(resp.status_code, 200)
        self.assert_flash_rendered(resp, "no longer available")
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"], {})

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_valid_items_compute_total(self, mock_product, mock_flashsale):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"5": 2}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 5, "name": "Mug", "price": 10, "image": "m.png"}
        resp = self.client.get("/cart")
        self.assertEqual(resp.status_code, 200)

    def test_visiting_cart_clears_buy_now(self):
        with self.client.session_transaction() as sess:
            sess["buy_now"] = {"id": 1, "qty": 1}
        with patch("app.controllers.auth.FlashSale") as mock_flashsale:
            mock_flashsale.get_sale_map.return_value = {}
            self.client.get("/cart")
        with self.client.session_transaction() as sess:
            self.assertNotIn("buy_now", sess)


class AddToCartTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/cart/add/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.Product")
    def test_product_not_found(self, mock_product):
        self.login_session()
        mock_product.get_by_id.return_value = None
        resp = self.client.post("/cart/add/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.Product")
    def test_out_of_stock(self, mock_product):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 0, "price": 10}
        resp = self.client.post("/cart/add/1")
        self.assertEqual(resp.status_code, 302)

    @patch("app.controllers.auth.Wishlist")
    @patch("app.controllers.auth.Product")
    def test_quantity_capped_at_available_stock(self, mock_product, mock_wishlist):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 3, "price": 10}
        resp = self.client.post("/cart/add/1", data={"quantity": "10"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"]["1"], 3)

    @patch("app.controllers.auth.Wishlist")
    @patch("app.controllers.auth.Product")
    def test_success_adds_and_removes_from_wishlist(self, mock_product, mock_wishlist):
        self.login_session(user_id=7)
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 5, "price": 10}
        resp = self.client.post("/cart/add/1", data={"quantity": "2"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"]["1"], 2)
        mock_wishlist.remove.assert_called_once_with(auth_module.mysql, 7, 1)


class UpdateCartTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Product")
    def test_increase_within_stock(self, mock_product):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 5}
        resp = self.client.post("/cart/update/1", data={"action": "increase"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"]["1"], 2)

    @patch("app.controllers.auth.Product")
    def test_increase_blocked_at_stock_limit(self, mock_product):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 5}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 5}
        resp = self.client.post("/cart/update/1", data={"action": "increase"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"]["1"], 5)

    @patch("app.controllers.auth.Product")
    def test_increase_product_missing(self, mock_product):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_product.get_by_id.return_value = None
        resp = self.client.post("/cart/update/1", data={"action": "increase"})
        self.assertEqual(resp.status_code, 302)

    def test_decrease_removes_item_at_zero(self):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        resp = self.client.post("/cart/update/1", data={"action": "decrease"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertNotIn("1", sess["cart"])

    def test_decrease_above_zero_keeps_item(self):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 3}
        resp = self.client.post("/cart/update/1", data={"action": "decrease"})
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"]["1"], 2)


class RemoveFromCartTests(AuthControllerTestCase):

    def test_removes_item_and_flashes(self):
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 2}
        resp = self.client.post("/cart/remove/1")
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertNotIn("1", sess["cart"])


# ─────────────────────────────────── BUY NOW ─────────────────────────────────

class BuyNowTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/buy_now/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.Product")
    def test_product_not_found(self, mock_product):
        self.login_session()
        mock_product.get_by_id.return_value = None
        resp = self.client.post("/buy_now/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.Product")
    def test_out_of_stock(self, mock_product):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 0}
        resp = self.client.post("/buy_now/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_product/1", resp.location)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_quantity_capped_at_stock(self, mock_product, mock_flashsale):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 2, "price": 10, "image": "s.png"}
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.post("/buy_now/1", data={"quantity": "5"})
        self.assertEqual(resp.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["buy_now"]["qty"], 2)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_success_sets_buy_now_session_and_redirects_to_checkout(self, mock_product, mock_flashsale):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "available": 5, "price": 10, "image": "s.png"}
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.post("/buy_now/1", data={"quantity": "2"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/checkout", resp.location)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["buy_now"]["subtotal"], 20)


# ─────────────────────────────────── CHECKOUT ────────────────────────────────

class CheckoutTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/checkout")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_nothing_to_checkout_redirects_home(self):
        self.login_session()
        resp = self.client.get("/checkout")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_buy_now_item_no_longer_available(self, mock_product, mock_flashsale):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["buy_now"] = {"id": 1, "qty": 1}
        mock_product.get_by_id.return_value = None
        resp = self.client.get("/checkout")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)
        with self.client.session_transaction() as sess:
            self.assertNotIn("buy_now", sess)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_buy_now_renders_checkout(self, mock_product, mock_flashsale):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["buy_now"] = {"id": 1, "qty": 2}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 10, "image": "s.png"}
        resp = self.client.get("/checkout")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_cart_renders_checkout_and_clears_buy_now(self, mock_product, mock_flashsale):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 10, "image": "s.png"}
        resp = self.client.get("/checkout")
        self.assertEqual(resp.status_code, 200)


class PlaceOrderTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/place_order")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_redirects_home_when_nothing_to_order(self):
        self.login_session()
        resp = self.client.post("/place_order")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_buy_now_item_gone_redirects_home(self, mock_product, mock_flashsale):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["buy_now"] = {"id": 1, "qty": 1}
        mock_product.get_by_id.return_value = None
        resp = self.client.post("/place_order")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.Order")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_esewa_redirects_to_payment_without_creating_order(self, mock_product, mock_flashsale, mock_order):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 10, "image": "s.png"}
        resp = self.client.post("/place_order", data={"payment": "esewa", "name": "Jane", "phone": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/payment/esewa", resp.location)
        mock_order.create.assert_not_called()
        with self.client.session_transaction() as sess:
            self.assertIn("pending_order_data", sess)

    @patch("app.controllers.auth.Order")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_cod_creates_order_immediately(self, mock_product, mock_flashsale, mock_order):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 10, "image": "s.png"}
        mock_order.create.return_value = (55, None)
        resp = self.client.post("/place_order", data={"payment": "cod", "name": "Jane", "phone": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/order_confirmed/55", resp.location)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["cart"], {})
            self.assertNotIn("buy_now", sess)

    @patch("app.controllers.auth.Order")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_cod_out_of_stock_redirects_to_cart(self, mock_product, mock_flashsale, mock_order):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 10, "image": "s.png"}
        mock_order.create.return_value = (None, ["Shoe"])
        resp = self.client.post("/place_order", data={"payment": "cod", "name": "Jane", "phone": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/cart", resp.location)

    @patch("app.models.coupon.Coupon")
    @patch("app.controllers.auth.Order")
    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    def test_cod_with_valid_coupon_applies_discount(self, mock_product, mock_flashsale, mock_order, mock_coupon):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["cart"] = {"1": 1}
        mock_flashsale.get_sale_map.return_value = {}
        mock_product.get_by_id.return_value = {"id": 1, "name": "Shoe", "price": 100, "image": "s.png"}
        mock_coupon.validate.return_value = ({"id": 9, "discount_amount": 20}, None)
        mock_order.create.return_value = (77, None)
        resp = self.client.post("/place_order", data={
            "payment": "cod", "name": "Jane", "phone": "1",
            "coupon_id": "9", "coupon_code": "SAVE20",
        })
        self.assertEqual(resp.status_code, 302)
        mock_coupon.apply.assert_called_once()


class PaymentPageTests(AuthControllerTestCase):

    def test_renders_with_session_totals(self):
        with self.client.session_transaction() as sess:
            sess["last_order_total"] = 100
            sess["last_order_id"] = 5
        resp = self.client.get("/payment/esewa")
        self.assertEqual(resp.status_code, 200)


class SubmitPaymentTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/payment/submit")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_missing_transaction_code(self):
        self.login_session()
        resp = self.client.post("/payment/submit", data={"transaction_code": ""})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_my_orders", resp.location)

    def test_no_pending_order_redirects_to_cart(self):
        self.login_session()
        resp = self.client.post("/payment/submit", data={"transaction_code": "TXN123"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/cart", resp.location)

    @patch("app.controllers.auth.mysql")
    @patch("app.controllers.auth.Order")
    def test_success_creates_order_and_clears_session(self, mock_order, mock_mysql):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["pending_order_data"] = {"user_id": 1, "items": [], "total": 100}
        mock_order.create.return_value = (10, None)
        mock_cursor = MagicMock()
        mock_mysql.connection.cursor.return_value = mock_cursor
        resp = self.client.post("/payment/submit", data={"transaction_code": "TXN123"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/order_confirmed/10", resp.location)
        mock_cursor.execute.assert_called_once()
        with self.client.session_transaction() as sess:
            self.assertNotIn("pending_order_data", sess)

    @patch("app.controllers.auth.mysql")
    @patch("app.controllers.auth.Order")
    def test_out_of_stock_redirects_to_cart_and_clears_pending(self, mock_order, mock_mysql):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["pending_order_data"] = {"user_id": 1, "items": [], "total": 100}
        mock_order.create.return_value = (None, ["Shoe"])
        resp = self.client.post("/payment/submit", data={"transaction_code": "TXN123"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/cart", resp.location)
        with self.client.session_transaction() as sess:
            self.assertNotIn("pending_order_data", sess)

    @patch("app.models.coupon.Coupon")
    @patch("app.controllers.auth.mysql")
    @patch("app.controllers.auth.Order")
    def test_applies_pending_coupon_on_success(self, mock_order, mock_mysql, mock_coupon):
        self.login_session()
        with self.client.session_transaction() as sess:
            sess["pending_order_data"] = {"user_id": 1, "items": [], "total": 80}
            sess["pending_coupon_id"] = "9"
            sess["pending_coupon_code"] = "SAVE20"
            sess["pending_coupon_pretax_total"] = 100
        mock_order.create.return_value = (11, None)
        mock_coupon.validate.return_value = ({"id": 9}, None)
        resp = self.client.post("/payment/submit", data={"transaction_code": "TXN999"})
        self.assertEqual(resp.status_code, 302)
        mock_coupon.apply.assert_called_once_with(auth_module.mysql, 9, 1, 11)


# ───────────────────────────────────── ORDERS ────────────────────────────────

class OrderConfirmedTests(AuthControllerTestCase):

    @patch("app.controllers.auth.Order")
    def test_not_found_redirects_home(self, mock_order):
        mock_order.get_by_id.return_value = None
        resp = self.client.get("/order_confirmed/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.Order")
    def test_other_users_order_redirects_home(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {"id": 1, "user_id": 2}
        resp = self.client.get("/order_confirmed/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/home", resp.location)

    @patch("app.controllers.auth.Order")
    def test_owner_can_view(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_by_id.return_value = {"id": 1, "user_id": 1, "total_price": 10, "order_status": "Pending"}
        resp = self.client.get("/order_confirmed/1")
        self.assertEqual(resp.status_code, 200)

    @patch("app.controllers.auth.Order")
    def test_anonymous_can_view_any_order(self, mock_order):
        mock_order.get_by_id.return_value = {"id": 1, "user_id": 99, "total_price": 10, "order_status": "Pending"}
        resp = self.client.get("/order_confirmed/1")
        self.assertEqual(resp.status_code, 200)


class ViewMyOrdersTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/view_my_orders")
        self.assertEqual(resp.status_code, 302)

    @patch("app.controllers.auth.Order")
    def test_lists_orders_for_current_user(self, mock_order):
        self.login_session(user_id=1)
        mock_order.get_all_by_user.return_value = [{"id": 1, "total_price": 50, "order_status": "Pending"}]
        resp = self.client.get("/view_my_orders")
        self.assertEqual(resp.status_code, 200)
        mock_order.get_all_by_user.assert_called_once_with(auth_module.mysql, 1)


class CancelOrderTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/cancel_order/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.Order")
    def test_success(self, mock_order):
        self.login_session()
        mock_order.cancel.return_value = True
        resp = self.client.post("/cancel_order/1")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_my_orders", resp.location)

    @patch("app.controllers.auth.Order")
    def test_cannot_be_cancelled(self, mock_order):
        self.login_session()
        mock_order.cancel.return_value = False
        resp = self.client.post("/cancel_order/1")
        self.assertEqual(resp.status_code, 302)


# ───────────────────────────────────── SEARCH ────────────────────────────────

class SearchSuggestTests(AuthControllerTestCase):

    def test_empty_query_returns_empty_list(self):
        resp = self.client.get("/search/suggest?q=")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])

    @patch("app.controllers.auth.Category")
    @patch("app.controllers.auth.Product")
    def test_combines_product_and_category_matches(self, mock_product, mock_category):
        mock_product.search.return_value = [{"id": 1, "name": "Red Shoe"}]
        mock_category.get_all.return_value = [{"id": 1, "name": "Shoes"}, {"id": 2, "name": "Hats"}]
        resp = self.client.get("/search/suggest?q=sho")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        labels = [d["label"] for d in data]
        self.assertIn("Red Shoe", labels)
        self.assertIn("Shoes", labels)

    @patch("app.controllers.auth.Category")
    @patch("app.controllers.auth.Product")
    def test_results_capped_at_ten(self, mock_product, mock_category):
        mock_product.search.return_value = [{"id": i, "name": f"P{i}"} for i in range(15)]
        mock_category.get_all.return_value = []
        resp = self.client.get("/search/suggest?q=p")
        data = resp.get_json()
        self.assertLessEqual(len(data), 10)


# ──────────────────────────────────── WISHLIST ───────────────────────────────

class ViewWishlistTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/wishlist")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    @patch("app.controllers.auth.FlashSale")
    @patch("app.controllers.auth.Product")
    @patch("app.controllers.auth.Wishlist")
    def test_renders_wishlist_products(self, mock_wishlist, mock_product, mock_flashsale):
        self.login_session()
        mock_wishlist.get_product_ids.return_value = [1, 2]
        mock_product.get_by_id.side_effect = lambda mysql, pid: {"id": pid, "name": f"P{pid}", "price": 10, "image": "p.png"}
        mock_flashsale.get_sale_map.return_value = {}
        resp = self.client.get("/wishlist")
        self.assertEqual(resp.status_code, 200)


class ToggleWishlistTests(AuthControllerTestCase):

    def test_requires_login_401(self):
        resp = self.client.post("/wishlist/toggle/1")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], "login_required")

    @patch("app.controllers.auth.Product")
    def test_product_not_found_404(self, mock_product):
        self.login_session()
        mock_product.get_by_id.return_value = None
        resp = self.client.post("/wishlist/toggle/1")
        self.assertEqual(resp.status_code, 404)

    @patch("app.controllers.auth.Wishlist")
    @patch("app.controllers.auth.Product")
    def test_adds_when_not_already_wishlisted(self, mock_product, mock_wishlist):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1}
        mock_wishlist.is_wishlisted.return_value = False
        mock_wishlist.get_count.return_value = 1
        resp = self.client.post("/wishlist/toggle/1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["wishlisted"])
        mock_wishlist.add.assert_called_once()

    @patch("app.controllers.auth.Wishlist")
    @patch("app.controllers.auth.Product")
    def test_removes_when_already_wishlisted(self, mock_product, mock_wishlist):
        self.login_session()
        mock_product.get_by_id.return_value = {"id": 1}
        mock_wishlist.is_wishlisted.return_value = True
        mock_wishlist.get_count.return_value = 0
        resp = self.client.post("/wishlist/toggle/1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["wishlisted"])
        mock_wishlist.remove.assert_called_once()


class WishlistStatusTests(AuthControllerTestCase):

    def test_anonymous_user_gets_default_response(self):
        resp = self.client.get("/wishlist/status/1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["wishlisted"])
        self.assertEqual(data["wishlist_count"], 0)

    @patch("app.controllers.auth.Wishlist")
    def test_product_id_zero_returns_count_only(self, mock_wishlist):
        self.login_session()
        mock_wishlist.get_count.return_value = 3
        resp = self.client.get("/wishlist/status/0")
        data = resp.get_json()
        self.assertEqual(data["wishlist_count"], 3)
        self.assertFalse(data["wishlisted"])
        mock_wishlist.is_wishlisted.assert_not_called()

    @patch("app.controllers.auth.Wishlist")
    def test_normal_product_checks_wishlist_status(self, mock_wishlist):
        self.login_session()
        mock_wishlist.get_count.return_value = 2
        mock_wishlist.is_wishlisted.return_value = True
        resp = self.client.get("/wishlist/status/5")
        data = resp.get_json()
        self.assertTrue(data["wishlisted"])


# ──────────────────────────────────── REVIEWS ────────────────────────────────

class SubmitReviewTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/product/1/review", data={"rating": "5"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_invalid_rating_rejected(self):
        self.login_session()
        resp = self.client.post("/product/1/review", data={"rating": "0", "comment": "meh"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_product/1", resp.location)

    @patch("app.models.review.Review")
    def test_creates_new_review(self, mock_review):
        self.login_session()
        mock_review.get_user_review_for_product.return_value = None
        mock_review.create.return_value = (True, "Review submitted!")
        resp = self.client.post("/product/1/review", data={"rating": "5", "comment": "Great!", "order_id": "9"})
        self.assertEqual(resp.status_code, 302)
        mock_review.create.assert_called_once()

    @patch("app.models.review.Review")
    def test_updates_existing_review(self, mock_review):
        self.login_session()
        mock_review.get_user_review_for_product.return_value = {"id": 5}
        mock_review.update.return_value = (True, "Updated")
        resp = self.client.post("/product/1/review", data={"rating": "4", "comment": "Pretty good"})
        self.assertEqual(resp.status_code, 302)
        mock_review.update.assert_called_once()
        mock_review.create.assert_not_called()


# ──────────────────────────────────── COUPONS ────────────────────────────────

class ValidateCouponTests(AuthControllerTestCase):

    def test_requires_login_401(self):
        resp = self.client.post("/coupon/validate", data={"code": "SAVE10", "cart_total": "100"})
        self.assertEqual(resp.status_code, 401)

    @patch("app.models.coupon.Coupon")
    def test_invalid_coupon_returns_400(self, mock_coupon):
        self.login_session()
        mock_coupon.validate.return_value = (None, "Coupon expired.")
        resp = self.client.post("/coupon/validate", data={"code": "OLD10", "cart_total": "100"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "Coupon expired.")

    @patch("app.models.coupon.Coupon")
    def test_valid_coupon_returns_discount_info(self, mock_coupon):
        self.login_session()
        mock_coupon.validate.return_value = ({
            "id": 1, "code": "SAVE10", "discount_amount": 10,
            "discount_type": "fixed", "discount_value": 10,
        }, None)
        resp = self.client.post("/coupon/validate", data={"code": "SAVE10", "cart_total": "100"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["discount_amount"], 10)


# ──────────────────────────────────── REFUNDS ────────────────────────────────

class RequestRefundTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.post("/order/1/refund", data={"reason": "broken"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.location)

    def test_missing_reason_rejected(self):
        self.login_session()
        resp = self.client.post("/order/1/refund", data={"reason": ""})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/view_my_orders", resp.location)

    @patch("app.models.refund.Refund")
    def test_success(self, mock_refund):
        self.login_session()
        mock_refund.request.return_value = (True, "Refund request submitted!")
        resp = self.client.post("/order/1/refund", data={"reason": "Item damaged"})
        self.assertEqual(resp.status_code, 302)
        mock_refund.request.assert_called_once()

    @patch("app.models.refund.Refund")
    def test_failure_still_redirects_with_error_flash(self, mock_refund):
        self.login_session()
        mock_refund.request.return_value = (False, "Refund window has expired.")
        resp = self.client.post("/order/1/refund", data={"reason": "Item damaged"})
        self.assertEqual(resp.status_code, 302)


class MyRefundsTests(AuthControllerTestCase):

    def test_requires_login(self):
        resp = self.client.get("/my_refunds")
        self.assertEqual(resp.status_code, 302)

    @patch("app.models.refund.Refund")
    def test_lists_refunds_for_user(self, mock_refund):
        self.login_session()
        mock_refund.get_by_user.return_value = [{"id": 1, "reason": "broken", "order_total": 50, "status": "Pending"}]
        resp = self.client.get("/my_refunds")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()