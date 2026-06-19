from app.models.database import Database

class Category:
    table = "categories"
    
    def __init__(self, name=None, description=None, image=None):
        self.name = name
        self.description = description
        self.image = image
    
    def save(self):
        db = Database()
        db.execute(
            "INSERT INTO categories (name, description, image) VALUES (%s, %s, %s)",
            (self.name, self.description, self.image)
        )
        db.close()
    
    def update(self, category_id):
        db = Database()
        db.execute(
            "UPDATE categories SET name=%s, description=%s, image=%s WHERE id=%s",
            (self.name, self.description, self.image, category_id)
        )
        db.close()
    
    @classmethod
    def get_all(cls):
        db = Database()
        results = db.fetch_all("SELECT * FROM categories ORDER BY name")
        db.close()
        return results
    
    @classmethod
    def get_by_id(cls, category_id):
        db = Database()
        result = db.fetch_one("SELECT * FROM categories WHERE id = %s", (category_id,))
        db.close()
        return result
    
    @classmethod
    def delete(cls, category_id):
        db = Database()
        db.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        db.close()
        return True