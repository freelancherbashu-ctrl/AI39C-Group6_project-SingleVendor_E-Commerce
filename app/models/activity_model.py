from app.models.database import Database
from datetime import datetime

class ActivityLog:
    table = "activity_logs"
    
    def __init__(self, user_id=None, action=None, details=None):
        self.user_id = user_id
        self.action = action
        self.details = details
    
    def save(self):
        db = Database()
        db.execute("""
            INSERT INTO activity_logs (user_id, action, details, created_at)
            VALUES (%s, %s, %s, %s)
        """, (self.user_id, self.action, self.details, datetime.now()))
        db.close()
    
    @classmethod
    def get_recent(cls, limit=20):
        db = Database()
        results = db.fetch_all("""
            SELECT * FROM activity_logs 
            ORDER BY created_at DESC 
            LIMIT %s
        """, (limit,))
        db.close()
        return results
    
    @classmethod
    def get_all(cls):
        db = Database()
        results = db.fetch_all("SELECT * FROM activity_logs ORDER BY created_at DESC")
        db.close()
        return results