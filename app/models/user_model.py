from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base_model import BaseModel
from app.models.database import Database


class User(BaseModel):

    # ---------------- TABLE NAME ----------------
    @property
    def table(self):
        return "users"

    # ---------------- INIT ----------------
    def __init__(self, name=None, email=None, password=None, role="user"):

        self.name = name
        self.email = email
        self.role = role
        self.__password = None

        if password:
            self.set_password(password)

    # ---------------- PASSWORD SET ----------------
    def set_password(self, password):

        self.__password = generate_password_hash(password)

    # ---------------- PASSWORD CHECK ----------------
    def check_password(self, password):

        if not self.__password:
            return False

        return check_password_hash(self.__password, password)

    # ---------------- SAVE USER ----------------
    def save(self):

        db = Database()

        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (self.name, self.email, self.__password, self.role)
        )

        db.close()

    # ---------------- EMAIL EXISTS CHECK ----------------
    def email_exists(self):

        db = Database()

        result = db.fetch_one(
            "SELECT id FROM users WHERE email=%s",
            (self.email,)
        )

        db.close()

        return result is not None

    # ---------------- BUILD OBJECT FROM DB ----------------
    @classmethod
    def from_db(cls, data):

        if not data:
            return None

        user = cls()

        user.name = data["name"]
        user.email = data["email"]
        user.role = data["role"]
        user.__password = data["password"]

        return user

    # ---------------- STRING REPRESENTATION ----------------
    def __str__(self):

        return f"User({self.name}, {self.email}, {self.role})"