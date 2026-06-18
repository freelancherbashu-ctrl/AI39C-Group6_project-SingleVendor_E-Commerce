from app.models.base_model import BaseModel
from app.models.database import Database
from werkzeug.security import generate_password_hash, check_password_hash


class User(BaseModel):

    @property
    def table(self):
        return "users"

    def __init__(self, name=None, email=None, password=None, role="user"):
        self.name = name
        self.email = email
        self.role = role
        self.password = password

    def save(self):
        db = Database()
        db.execute(
           "INSERT INTO users (name, email, password, role, profile_picture) VALUES (%s, %s, %s, %s, %s)",
           (self.name, self.email, self.password, self.role, 'default_pp.jpg')
        )
        db.close()

    def find_by(self, field, value):
        db = Database()
        result = db.fetch_one(
            f"SELECT * FROM users WHERE {field}=%s",
            (value,)
        )
        db.close()
        return result

    @classmethod
    def from_db(cls, data):
        if not data:
            return None
        user = cls()
        user.name = data["name"]
        user.email = data["email"]
        user.role = data["role"]
        user.password = data["password"]
        return user

    def __str__(self):
        return f"User({self.name}, {self.email}, {self.role})"