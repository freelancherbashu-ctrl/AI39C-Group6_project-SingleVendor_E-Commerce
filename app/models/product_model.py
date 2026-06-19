from app.models.database import Database
import re

class Product:
    table = "products"
    
    def __init__(self, name=None, slug=None, description=None, price=None, 
                 stock=None, category_id=None, image=None, status='active'):
        self.name = name
        self.slug = slug
        self.description = description
        self.price = price
        self.stock = stock
        self.category_id = category_id
        self.image = image
        self.status = status
    
    @staticmethod
    def generate_slug(name):
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        return slug.strip('-')
    
    def save(self):
        db = Database()
        db.execute("""
            INSERT INTO products 
            (name, slug, description, price, stock, category_id, image, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (self.name, self.slug, self.description, self.price, self.stock, 
              self.category_id, self.image, self.status))
        db.close()
    
    def update(self, product_id):
        db = Database()
        db.execute("""
            UPDATE products SET 
                name=%s, slug=%s, description=%s, price=%s, stock=%s, 
                category_id=%s, image=%s, status=%s 
            WHERE id=%s
        """, (self.name, self.slug, self.description, self.price, self.stock, 
              self.category_id, self.image, self.status, product_id))
        db.close()
    
    @classmethod
    def get_all(cls):
        db = Database()
        results = db.fetch_all("SELECT * FROM products ORDER BY name")
        db.close()
        return results
    
    @classmethod
    def get_by_category(cls, category_id):
        db = Database()
        results = db.fetch_all("SELECT * FROM products WHERE category_id = %s ORDER BY name", (category_id,))
        db.close()
        return results
    
    @classmethod
    def get_by_id(cls, product_id):
        db = Database()
        result = db.fetch_one("SELECT * FROM products WHERE id = %s", (product_id,))
        db.close()
        return result
    
    @classmethod
    def get_by_slug(cls, slug):
        db = Database()
        result = db.fetch_one("SELECT * FROM products WHERE slug = %s", (slug,))
        db.close()
        return result
    
    @classmethod
    def get_active(cls):
        db = Database()
        results = db.fetch_all("SELECT * FROM products WHERE status = 'active' ORDER BY name")
        db.close()
        return results
    
    @classmethod
    def search(cls, query):
        db = Database()
        results = db.fetch_all("""
            SELECT * FROM products 
            WHERE name LIKE %s OR description LIKE %s
            ORDER BY name
        """, (f"%{query}%", f"%{query}%"))
        db.close()
        return results
    
    @classmethod
    def slug_exists(cls, slug, exclude_id=None):
        db = Database()
        if exclude_id:
            result = db.fetch_one(
                "SELECT id FROM products WHERE slug = %s AND id != %s",
                (slug, exclude_id)
            )
        else:
            result = db.fetch_one("SELECT id FROM products WHERE slug = %s", (slug,))
        db.close()
        return result is not None
    
    @classmethod
    def delete(cls, product_id):
        db = Database()
        db.execute("DELETE FROM products WHERE id = %s", (product_id,))
        db.close()
        return True