import pymysql
from config import Config

class Database:
    def __init__(self):
        try:
            self.connection = pymysql.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                port=Config.MYSQL_PORT,
                cursorclass=pymysql.cursors.DictCursor
            )
            print("✅ Database connected")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connection = None

    def fetch_one(self, query, params=None):
        if not self.connection:
            return None
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def fetch_all(self, query, params=None):
        if not self.connection:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def execute(self, query, params=None):
        if not self.connection:
            return
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            self.connection.commit()

    def close(self):
        if self.connection:
            self.connection.close()

    @staticmethod
    def create_tables():
        db = Database()
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                slug VARCHAR(255) UNIQUE,
                description TEXT,
                image VARCHAR(255),
                parent_id INT DEFAULT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                slug VARCHAR(255) UNIQUE,
                price INT NOT NULL,
                description TEXT,
                category_id INT,
                image VARCHAR(255),
                stock INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)
        
        # Admin user
        admin = db.fetch_one("SELECT * FROM users WHERE email = %s", ("admin@admin.com",))
        if not admin:
            from werkzeug.security import generate_password_hash
            db.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Admin", "admin@admin.com", generate_password_hash("admin123"), "admin")
            )
        
        # Default categories
        categories = [
            ("Electronics", "electronics", "Electronic devices"),
            ("Clothing", "clothing", "Fashion apparel"),
            ("Books", "books", "Books and publications"),
        ]
        
        for name, slug, desc in categories:
            existing = db.fetch_one("SELECT id FROM categories WHERE slug = %s", (slug,))
            if not existing:
                db.execute(
                    "INSERT INTO categories (name, slug, description) VALUES (%s, %s, %s)",
                    (name, slug, desc)
                )
        
        db.close()
        print("✅ Tables created!")