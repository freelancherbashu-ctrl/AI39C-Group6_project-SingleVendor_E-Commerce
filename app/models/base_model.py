from abc import ABC, abstractmethod
from .database import Database

class BaseModel(ABC):
    @property
    @abstractmethod
    def table(self):
        pass
    
    def find_all(self):
        db = Database()
        result = db.fetch_all(f"SELECT * FROM {self.table}")
        db.close()
        return result
    
    def find_by_id(self, id):
        db = Database()
        result = db.fetch_one(f"SELECT * FROM {self.table} WHERE id = %s", (id,))
        db.close()
        return result
    
    def delete_by_id(self, id):
        db = Database()
        db.execute(f"DELETE FROM {self.table} WHERE id = %s", (id,))
        db.close()