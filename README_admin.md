# meropasal - Admin Panel

Admin panel module for the meropasal e-commerce project. Built with Flask, SQLAlchemy, and MySQL.

## Features

### Dashboard
- Total products, categories, orders counters
- Revenue from completed orders
- Order status overview (pending / processing / completed / cancelled)
- 7-day sales chart (Chart.js)
- Recent orders list
- Low stock alerts

### Products
- Add / Edit / Delete products with image upload
- Search by name
- Filter by category
- Pagination (10 per page)
- Bulk actions: activate / deactivate / delete
- Quick stock adjust (+/- buttons)
- Active / Inactive status

### Categories
- Add / Edit / Delete categories

### Orders
- List all orders with pagination
- Filter by status (pending / processing / completed / cancelled)
- Search by customer name / email / phone
- Order detail page with status update
- CSV export of filtered orders

### Settings
- Site name
- Currency symbol
- Low stock threshold (used in dashboard alerts)

### Error Pages
- Custom 404 (not found) page
- Custom 500 (server error) page

### Auth
- admin_required decorator stub in app/controllers/auth.py
- All admin routes are gated; switching the decorator to a real check enables auth for the whole panel without touching any other file

## Tech Stack

- Python 3.14
- Flask 3.x
- Flask-SQLAlchemy
- MySQL (via PyMySQL)
- Jinja2 templates
- Chart.js (CDN)

## Setup

1. Create the database in MySQL Workbench:

CREATE DATABASE meropasal_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

2. Install dependencies:

pip install -r requirements.txt

3. Update config.py with your MySQL password.

4. Seed sample data (optional):

python seed_admin.py

5. Run:

python run.py

6. Open http://127.0.0.1:5000/admin/

## Routes

| URL | Page |
|---|---|
| /admin/ | Dashboard |
| /admin/products | Products list |
| /admin/products/add | Add product |
| /admin/products/edit/<id> | Edit product |
| /admin/products/bulk | Bulk action (POST) |
| /admin/products/<id>/stock | Quick stock adjust (POST) |
| /admin/categories | Categories |
| /admin/orders | Orders list |
| /admin/orders/<id> | Order detail |
| /admin/orders/export.csv | Download CSV |
| /admin/settings | Settings |
| /admin/api/sales-chart | Sales chart JSON API |

## Notes for Team

- Admin code only touches: app/controllers/admin.py, app/controllers/auth.py, app/routes/admin_routes.py, app/models/settings_model.py, and app/templates/admin/ + app/static/admin/
- auth.py has a no-op admin_required decorator. When the auth teammate is ready, replace the body of admin_required with a real session check - no other file needs to change.
- app/__init__.py is shared. Admin only added: from app.models import settings_model and 2 error handlers.
- config.py was updated to use MySQL via PyMySQL.