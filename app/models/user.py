import hashlib
import os
import secrets

class User:

    @staticmethod
    def init_table(mysql):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(64) NOT NULL,
            profile_picture VARCHAR(255) DEFAULT NULL,
            reset_token VARCHAR(64) DEFAULT NULL,
            reset_token_expiry DATETIME DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        mysql.connection.commit()
        # Safe upgrades for existing tables
        for sql in [
            "ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255) DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN reset_token VARCHAR(64) DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN reset_token_expiry DATETIME DEFAULT NULL",
        ]:
            try:
                cursor.execute(sql)
                mysql.connection.commit()
            except Exception:
                mysql.connection.rollback()

    @staticmethod
    def _hash(password):
        return hashlib.sha256(password.encode()).hexdigest()

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
        SELECT id, full_name, email, profile_picture
        FROM users
        WHERE email = %s AND password_hash = %s
        """, (email, User._hash(password)))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], "full_name": row[1],
                "email": row[2], "profile_picture": row[3]
            }
        return None

    @staticmethod
    def get_by_id(mysql, user_id):
        cursor = mysql.connection.cursor()
        cursor.execute("""
        SELECT id, full_name, email, profile_picture, created_at
        FROM users WHERE id = %s
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0], "full_name": row[1], "email": row[2],
                "profile_picture": row[3], "created_at": row[4]
            }
        return None

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
        SELECT id FROM users WHERE id=%s AND password_hash=%s
        """, (user_id, User._hash(old_password)))
        if not cursor.fetchone():
            return False, "Current password is incorrect."
        cursor.execute("""
        UPDATE users SET password_hash=%s WHERE id=%s
        """, (User._hash(new_password), user_id))
        mysql.connection.commit()
        return True, "Password changed successfully!"

    @staticmethod
    def create_reset_token(mysql, email):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        row = cursor.fetchone()
        if not row:
            return None
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
