from abc import ABC, abstractmethod
from app.models.database import Database


class BaseModel(ABC):

    # ---------------- TABLE NAME (must override) ----------------
    @property
    @abstractmethod
    def table(self):
        pass

    # ---------------- FIND BY ID ----------------
    def find_by_id(self, record_id):

        db = Database()

        result = db.fetch_one(
            f"SELECT * FROM {self.table} WHERE id=%s",
            (record_id,)
        )

        db.close()
        return result

    # ---------------- FIND BY COLUMN ----------------
    def find_by(self, column, value):

        db = Database()

        result = db.fetch_one(
            f"SELECT * FROM {self.table} WHERE {column}=%s",
            (value,)
        )

        db.close()
        return result

    # ---------------- FIND ALL ----------------
    def find_all(self):

        db = Database()

        result = db.fetch_all(
            f"SELECT * FROM {self.table}"
        )

        db.close()
        return result

    # ---------------- DELETE BY ID ----------------
    def delete_by_id(self, record_id):

        db = Database()

        db.execute(
            f"DELETE FROM {self.table} WHERE id=%s",
            (record_id,)
        )

        db.close()
