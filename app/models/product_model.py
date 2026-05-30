import re
from .database import Database

class ProductModel:
    def generate_slug(self, name):
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        return slug.strip('-')
    
    def save(self, category_id, name, slug, description, price, stock, image, status):
        db = Database()
        db.execute(
            "INSERT INTO products (category_id, name, slug, description, price, stock, image, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (category_id, name, slug, description, price, stock, image, status)
        )
        db.close()
    
    def find_all(self):
        db = Database()
        result = db.fetch_all("""
            SELECT p.*, c.name as category_name 
            FROM products p 
            JOIN categories c ON p.category_id = c.id 
            ORDER BY p.id DESC
        """)
        db.close()
        return result