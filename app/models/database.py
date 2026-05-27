import pymysql
import pymysql.cursors
from config import Config

class Database:
    def __init__(self):
        self.connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            cursorclass=pymysql.cursors.DictCursor
        )

    def execute(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount

    def fetch_one(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def close(self):
        self.connection.close()