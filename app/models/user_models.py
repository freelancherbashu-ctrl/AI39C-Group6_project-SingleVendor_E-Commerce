from app.models.database import Database
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def create(name, email, password):
        db = Database()
        hashed_password = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'customer')",
            (name, email, hashed_password)
        )
        db.close()
        return True

    @staticmethod
    def find_by_email(email):
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE email = %s", (email,))
        db.close()
        return user

    @staticmethod
    def find_by_id(user_id):
        db = Database()
        user = db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
        db.close()
        return user