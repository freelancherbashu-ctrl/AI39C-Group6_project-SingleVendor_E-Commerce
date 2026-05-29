from .base_model import BaseModel
from .database import Database

class CategoryModel(BaseModel):
    @property
    def table(self):
        return "categories"
    
    def save(self, name, description, image=None):
        db = Database()
        db.execute(
            "INSERT INTO categories (name, description, image) VALUES (%s, %s, %s)",
            (name, description, image)
        )
        db.close()
        return True
    
    def update(self, id, name, description, image=None):
        db = Database()
        db.execute(
            "UPDATE categories SET name=%s, description=%s, image=%s WHERE id=%s",
            (name, description, image, id)
        )
        db.close()
        return True 