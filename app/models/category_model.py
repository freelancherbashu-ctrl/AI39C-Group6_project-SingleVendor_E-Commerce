import re
from .base_model import BaseModel
from .database import Database

class CategoryModel(BaseModel):
    @property
    def table(self):
        return "categories"
    
    def generate_slug(self, name):
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        return slug.strip('-')
    
    def name_exists(self, name, exclude_id=None):
        db = Database()
        if exclude_id:
            result = db.fetch_one("SELECT id FROM categories WHERE name = %s AND id != %s", (name, exclude_id))
        else:
            result = db.fetch_one("SELECT id FROM categories WHERE name = %s", (name,))
        db.close()
        return result is not None
    
    def slug_exists(self, slug, exclude_id=None):
        db = Database()
        if exclude_id:
            result = db.fetch_one("SELECT id FROM categories WHERE slug = %s AND id != %s", (slug, exclude_id))
        else:
            result = db.fetch_one("SELECT id FROM categories WHERE slug = %s", (slug,))
        db.close()
        return result is not None
    
    def save(self, name, slug, description, image, status='active', parent_id=None):
        db = Database()
        db.execute(
            "INSERT INTO categories (name, slug, description, image, status, parent_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, slug, description, image, status, parent_id)
        )
        db.close()
        return True