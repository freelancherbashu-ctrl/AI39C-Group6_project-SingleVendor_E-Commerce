import os

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

# ── MySQL ──────────────────────────────────────────────────────────────────
MYSQL_HOST     = os.environ.get('MYSQL_HOST',     'localhost')
MYSQL_USER     = os.environ.get('MYSQL_USER',     'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
MYSQL_DB       = os.environ.get('MYSQL_DB',       'meropasal')

# ── Mail ───────────────────────────────────────────────────────────────────
MAIL_SERVER         = 'smtp.gmail.com'
MAIL_PORT           = 587
MAIL_USE_TLS        = True
MAIL_USERNAME       = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD       = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = ('MeroPasal', os.environ.get('MAIL_USERNAME', ''))

# ── Google OAuth ───────────────────────────────────────────────────────────
GOOGLE_OAUTH_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID',     '')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
