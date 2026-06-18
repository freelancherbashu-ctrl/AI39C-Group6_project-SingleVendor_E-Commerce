"""Key/value settings table for runtime-configurable admin options.

Used by the dashboard (low_stock_threshold), the settings page (site_name,
currency, etc.), and anywhere else that needs admin-tweakable values
without code changes.
"""
from app.models.database import db


class Setting(db.Model):
    __tablename__ = "settings"
    key   = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(255), nullable=False, default="")

    # ---- helpers ----
    @classmethod
    def get(cls, key, default=None):
        row = cls.query.get(key)
        return row.value if row else default

    @classmethod
    def get_int(cls, key, default=0):
        try:
            return int(cls.get(key, default))
        except (TypeError, ValueError):
            return default

    @classmethod
    def set(cls, key, value):
        row = cls.query.get(key)
        if row:
            row.value = str(value)
        else:
            db.session.add(cls(key=key, value=str(value)))
