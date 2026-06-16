import secrets
from werkzeug.security import generate_password_hash, check_password_hash


class User:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(256) DEFAULT NULL,
            google_id VARCHAR(100) DEFAULT NULL,
            profile_picture VARCHAR(255) DEFAULT NULL,
            reset_token VARCHAR(64) DEFAULT NULL,
            reset_token_expiry DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()
        # Safe column upgrades for existing tables
        for sql in [
            "ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255) DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN reset_token VARCHAR(64) DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN google_id VARCHAR(100) DEFAULT NULL",
            "ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(256) DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN is_blocked TINYINT(1) NOT NULL DEFAULT 0",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()

    @staticmethod
    def _hash(password):
        # FIXED: use werkzeug bcrypt-based hashing instead of raw SHA-256
        return generate_password_hash(password)

    @staticmethod
    def _verify_hash(password, password_hash):
        # Handle legacy SHA-256 hashes that may still be in the DB
        import hashlib
        sha256 = hashlib.sha256(password.encode()).hexdigest()
        if password_hash == sha256:
            return True
        return check_password_hash(password_hash, password)

    @staticmethod
    def create(mysql, full_name, email, password):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """, (full_name, email, User._hash(password)))
            mysql.connection.commit()
            return True, "Account created successfully!"
        except Exception:
            mysql.connection.rollback()
            return False, "An account with this email already exists."

    @staticmethod
    def verify(mysql, email, password):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, full_name, email, profile_picture, password_hash, is_blocked
        FROM users
        WHERE email = %s
        """, (email,))
        row = cursor.fetchone()
        if row and row[4] and User._verify_hash(password, row[4]):
            if row[5]:  # is_blocked
                return "blocked"
            return {
                "id": row[0], "full_name": row[1],
                "email": row[2], "profile_picture": row[3]
            }
        return None

    @staticmethod
    def get_by_id(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, full_name, email, profile_picture, created_at, is_blocked
        FROM users WHERE id = %s
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], "full_name": row[1], "email": row[2],
                "profile_picture": row[3], "created_at": row[4],
                "is_blocked": bool(row[5])
            }
        return None

    @staticmethod
    def get_all(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, full_name, email, created_at, is_blocked
        FROM users ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        return [{"id": r[0], "full_name": r[1], "email": r[2],
                 "created_at": r[3], "is_blocked": bool(r[4])} for r in rows]

    @staticmethod
    def toggle_block(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT is_blocked FROM users WHERE id=%s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        new_val = 0 if row[0] else 1
        cursor.execute("UPDATE users SET is_blocked=%s WHERE id=%s", (new_val, user_id))
        mysql.connection.commit()
        return bool(new_val)  # True = now blocked

    @staticmethod
    def update_profile(mysql, user_id, full_name, email):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
            UPDATE users SET full_name=%s, email=%s WHERE id=%s
            """, (full_name, email, user_id))
            mysql.connection.commit()
            return True, "Profile updated successfully!"
        except Exception:
            mysql.connection.rollback()
            return False, "That email is already in use by another account."

    @staticmethod
    def update_picture(mysql, user_id, filename):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        UPDATE users SET profile_picture=%s WHERE id=%s
        """, (filename, user_id))
        mysql.connection.commit()

    @staticmethod
    def change_password(mysql, user_id, old_password, new_password):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, password_hash FROM users WHERE id=%s
        """, (user_id,))
        row = cursor.fetchone()
        if not row or not row[1] or not User._verify_hash(old_password, row[1]):
            return False, "Current password is incorrect."
        cursor.execute("""
        UPDATE users SET password_hash=%s WHERE id=%s
        """, (User._hash(new_password), user_id))
        mysql.connection.commit()
        return True, "Password changed successfully!"

    @staticmethod
    def create_reset_token(mysql, email):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, password_hash, google_id FROM users WHERE email=%s",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        # Google-only account: has a google_id but no password set
        if row[2] and not row[1]:
            return "google_account"
        token = secrets.token_hex(32)
        cursor.execute("""
        UPDATE users
        SET reset_token=%s,
            reset_token_expiry = DATE_ADD(NOW(), INTERVAL 1 HOUR)
        WHERE email=%s
        """, (token, email))
        mysql.connection.commit()
        return token

    @staticmethod
    def verify_reset_token(mysql, token):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id FROM users
        WHERE reset_token=%s AND reset_token_expiry > NOW()
        """, (token,))
        row = cursor.fetchone()
        return row[0] if row else None

    @staticmethod
    def reset_password(mysql, token, new_password):
        user_id = User.verify_reset_token(mysql, token)
        if not user_id:
            return False, "Reset link is invalid or has expired."
        cursor = mysql.connection.cursor()
        cursor.execute("""
        UPDATE users
        SET password_hash=%s, reset_token=NULL, reset_token_expiry=NULL
        WHERE id=%s
        """, (User._hash(new_password), user_id))
        mysql.connection.commit()
        return True, "Password reset successfully! Please log in."

    @staticmethod
    def delete(mysql, user_id):
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
            mysql.connection.commit()
            return True
        except Exception:
            mysql.connection.rollback()
            return False

    @staticmethod
    def get_or_create_google_user(mysql, google_id, email, full_name):
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, full_name, email FROM users WHERE google_id=%s",
            (google_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "full_name": row[1], "email": row[2]}

        cursor.execute(
            "SELECT id, full_name, email FROM users WHERE email=%s",
            (email,)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE users SET google_id=%s WHERE email=%s",
                (google_id, email)
            )
            mysql.connection.commit()
            return {"id": row[0], "full_name": row[1], "email": row[2]}

        cursor.execute(
            "INSERT INTO users (full_name, email, google_id) VALUES (%s, %s, %s)",
            (full_name, email, google_id)
        )
        mysql.connection.commit()
        return {"id": cursor.lastrowid, "full_name": full_name, "email": email}

    @staticmethod
    def create_otp(mysql, email):
        """Generate a 6-digit OTP, store it in reset_token (expires in 10 min).
        Returns (otp, None) on success or (None, error_message) on failure."""
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT id, password_hash, google_id FROM users WHERE email=%s",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            return None, "No account found with that email."
        if row[2] and not row[1]:
            return None, "This account uses Google login — password reset is not available."
        import random
        otp = str(random.randint(100000, 999999))
        cursor.execute("""
        UPDATE users
        SET reset_token=%s,
            reset_token_expiry = DATE_ADD(NOW(), INTERVAL 10 MINUTE)
        WHERE email=%s
        """, (otp, email))
        mysql.connection.commit()
        return otp, None

    @staticmethod
    def verify_otp(mysql, email, otp):
        """Check OTP is correct and not expired. Returns user_id or None."""
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id FROM users
        WHERE email=%s AND reset_token=%s AND reset_token_expiry > NOW()
        """, (email, otp))
        row = cursor.fetchone()
        return row[0] if row else None