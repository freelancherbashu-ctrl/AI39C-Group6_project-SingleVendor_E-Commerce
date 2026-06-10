from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import mysql
from app.models.admin import Admin

app = create_app()

with app.app_context():
    # Ensure table exists first
    Admin.init_table(mysql)
    
    if Admin.exists(mysql):
        print("Admin user already exists. Skipping.")
    else:
        username = input("Admin username: ").strip()
        email    = input("Admin email: ").strip()
        password = input("Admin password: ").strip()
        if Admin.create(mysql, username, email, password):
            print(f"\n✓ Admin '{username}' created! Visit http://localhost:5000/admin/login")
        else:
            print("✗ Failed — username or email may already be taken.")