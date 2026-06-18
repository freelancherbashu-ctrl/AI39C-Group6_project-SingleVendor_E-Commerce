





# import pymysql

# class Database:
#     def __init__(self):
#         try:
#             self.connection = pymysql.connect(
#                 host='localhost',
#                 user='root',
#                 password='yagya1234',
#                 database='class_db',
#                 port=3306,
#                 cursorclass=pymysql.cursors.DictCursor
#             )
#             print("✅ Database connected")
#         except Exception as e:
#             print(f"❌ Connection failed: {e}")
#             self.connection = None

#     def fetch_one(self, query, params=None):
#         if not self.connection:
#             return None
#         with self.connection.cursor() as cursor:
#             cursor.execute(query, params or ())
#             return cursor.fetchone()

#     def fetch_all(self, query, params=None):
#         if not self.connection:
#             return []
#         with self.connection.cursor() as cursor:
#             cursor.execute(query, params or ())
#             return cursor.fetchall()

#     def execute(self, query, params=None):
#         if not self.connection:
#             return
#         with self.connection.cursor() as cursor:
#             cursor.execute(query, params or ())
#             self.connection.commit()

#     def close(self):
#         if self.connection:
#             self.connection.close()

#     @staticmethod
#     def create_tables():
#         db = Database()
        
#         # Users table
#         db.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL,
#                 email VARCHAR(100) NOT NULL UNIQUE,
#                 password VARCHAR(255) NOT NULL,
#                 role VARCHAR(20) DEFAULT 'user',
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
        
#         # Categories table
#         db.execute("""
#             CREATE TABLE IF NOT EXISTS categories (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL UNIQUE,
#                 slug VARCHAR(255) UNIQUE,
#                 description TEXT,
#                 image VARCHAR(255),
#                 parent_id INT DEFAULT NULL,
#                 is_active BOOLEAN DEFAULT TRUE,
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
#                 FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
#             )
#         """)
        
#         # Products table
#         db.execute("""
#             CREATE TABLE IF NOT EXISTS products (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL,
#                 slug VARCHAR(255) UNIQUE,
#                 price INT NOT NULL,
#                 description TEXT,
#                 category_id INT,
#                 image VARCHAR(255),
#                 stock INT DEFAULT 0,
#                 status VARCHAR(20) DEFAULT 'active',
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
#             )
#         """)
        
#         # Admin user
#         admin = db.fetch_one("SELECT * FROM users WHERE email = %s", ("admin@admin.com",))
#         if not admin:
#             db.execute(
#                 "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
#                 ("Admin", "admin@admin.com", "admin123", "admin")
#             )
        
#         db.close()
#         print("✅ Tables created!")




import pymysql

class Database:
    def __init__(self):
        try:
            self.connection = pymysql.connect(
                host='localhost',
                user='root',
                password='yagya1234',
                database='class_db',
                port=3306,
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
        
        # Users table
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
        
        # Categories table
        db.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                slug VARCHAR(255) UNIQUE,
                description TEXT,
                image VARCHAR(255),
                parent_id INT DEFAULT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        
        # Products table
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
            db.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Admin", "admin@admin.com", "admin123", "admin")
            )
        
        db.close()
        print("✅ Tables created!")