import pymysql
import config

class Database:
    def __init__(self):
        try:
            self.connection = pymysql.connect(
                host=config.MYSQL_HOST,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                database=config.MYSQL_DATABASE,
                cursorclass=pymysql.cursors.DictCursor
            )
            print("Database connected successfully")
        except Exception as e:
            print(f"Connection failed: {e}")

    def fetch_one(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def fetch_all(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def execute(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())
            self.connection.commit()

    def close(self):
        self.connection.close()