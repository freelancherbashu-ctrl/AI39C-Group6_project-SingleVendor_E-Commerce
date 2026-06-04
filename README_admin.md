# meropasal — Admin Panel Module

Modular admin panel for the meropasal e-commerce site. **One HTML + one CSS + one JS per feature**, so anyone on the team can modify a single section without touching the rest.

---

## ✨ What you get

| Feature | Template | CSS | JS |
|---|---|---|---|
| Admin home / Dashboard | `admin_index.html` | `dashboard.css` | `dashboard.js` |
| Products list | `products.html` | `products.css` | `products.js` |
| Add / Edit product | `product_form.html` | `products.css` | `products.js` |
| Categories | `categories.html` | `categories.css` | `categories.js` |
| Orders list | `orders.html` | `orders.css` | `orders.js` |
| Order detail | `order_detail.html` | `orders.css` | `orders.js` |
| Shared shell | `admin_layout.html` | `admin_base.css` | `admin_base.js` |

✅ `admin_index.html` is **standalone** — extends only `admin_layout.html`, NOT the customer site's `base.html`. Admin and customer UIs are fully separated.
✅ All admin CSS classes are prefixed (`.admin-`, `.prod-`, `.cat-`, `.ord-`, `.dash-`) so they cannot collide with `style.css` from the storefront.
✅ Admin static files live under `static/admin/` — separate folder from customer assets.

---

## 📁 Folder structure (drops into your existing repo)

```
app/
├── controllers/
│   └── admin.py                          ← NEW (image upload helper)
├── models/
│   ├── database.py                       ← keep yours if it exists
│   └── product_models.py                 ← NEW (Product/Category/Order)
├── routes/
│   └── admin_routes.py                   ← NEW (blueprint)
├── static/
│   └── admin/                            ← NEW (all admin assets here)
│       ├── css/
│       │   ├── admin_base.css            (shared shell)
│       │   ├── dashboard.css             (admin_index page only)
│       │   ├── products.css
│       │   ├── categories.css
│       │   └── orders.css
│       ├── js/
│       │   ├── admin_base.js
│       │   ├── dashboard.js
│       │   ├── products.js
│       │   ├── categories.js
│       │   └── orders.js
│       ├── img/
│       │   └── meropasal-logo.png
│       └── uploads/                      (product images go here)
│           └── .gitkeep
├── templates/
│   └── admin/                            ← NEW
│       ├── admin_layout.html             (shell — extended by all admin pages)
│       ├── admin_index.html              (admin homepage / dashboard)
│       ├── products.html
│       ├── product_form.html
│       ├── categories.html
│       ├── orders.html
│       └── order_detail.html
└── __init__.py                           ← EDIT (see step 2)

seed_admin.py                             ← optional, project root
```

---

## 🖥 How to add the code in VS Code

1. **Open your project folder** in VS Code (`File → Open Folder…` → pick `AI39C-Group6_project-SingleVendor_E-Commerce`).

2. **Unzip** the bundle (`meropasal_admin.zip`) somewhere outside the project.

3. **Drag the files into VS Code** OR copy folders manually:
   - Drag `app/controllers/admin.py` into the VS Code Explorer panel under `app/controllers/`.
   - Same for `app/models/product_models.py` and `app/routes/admin_routes.py`.
   - Drag the **whole** `static/admin/` folder into `app/static/`.
   - Drag the **whole** `templates/admin/` folder into `app/templates/`. (If `templates/admin/` already has files from before, replace them.)
   - Drop `seed_admin.py` into the project root (same place as `run.py`).

4. **Open `app/__init__.py`** in VS Code and merge in the two new lines (shown in step below).

5. **Open the integrated terminal** (`Ctrl + ~`) — make sure your venv is activated. The prompt should show `(venv)`. If not:
   ```bash
   .\venv\Scripts\activate        # Windows
   # source venv/bin/activate     # macOS/Linux
   ```

6. **Install dependencies** (if not already):
   ```bash
   pip install flask flask-sqlalchemy
   ```

7. **Run**:
   ```bash
   python run.py
   ```
   Open **http://127.0.0.1:5000/admin/**

---

## 🔧 Update `app/__init__.py`

Inside `create_app()`, add the two highlighted lines:

```python
from app.models import product_models                # ← ADD
from app.routes.admin_routes import admin_bp         # ← ADD
app.register_blueprint(admin_bp)                     # ← ADD
```

Make sure these configs exist:
```python
app.config["SECRET_KEY"] = "change-this-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meropasal.db"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
```

A full reference file is bundled — compare side-by-side in VS Code.

---

## 🌱 (Optional) Load sample data

```bash
python seed_admin.py
```
Adds 3 categories, 4 products, 2 orders so the dashboard isn't blank.

---

## 🚀 Push to GitHub

From the project root in VS Code terminal:

```bash
# Always sync first so you don't conflict with teammates
git pull origin main

# Create a feature branch (recommended for group projects)
git checkout -b feature/admin-panel

# Stage everything new
git add app/controllers/admin.py
git add app/models/product_models.py
git add app/routes/admin_routes.py
git add app/static/admin/
git add app/templates/admin/
git add app/__init__.py
git add seed_admin.py
git add README_admin.md

# Or stage everything at once:
git add .

# Commit
git commit -m "Add modular admin panel (dashboard, products, categories, orders)"

# Push the branch
git push -u origin feature/admin-panel
```

Then on GitHub:
1. Open the repo → you'll see a yellow banner "Compare & pull request" → click it.
2. Write a short description → "Create pull request".
3. Teammates review → click **Merge pull request** → done.

### If your group works directly on `main`:
```bash
git add .
git commit -m "Add admin panel"
git push origin main
```

### Using VS Code's built-in Git instead of terminal
1. Click the **Source Control** icon in the left sidebar (`Ctrl+Shift+G`).
2. You'll see all changed/new files under "Changes". Hover any file and click `+` to stage it (or click `+` next to "Changes" to stage all).
3. Type your commit message at the top → click the ✔ checkmark to commit.
4. Click the **…** menu → **Push** → done.

### Recommended `.gitignore` additions
```
venv/
__pycache__/
*.pyc
instance/
*.db
app/static/admin/uploads/*
!app/static/admin/uploads/.gitkeep
```

The `.gitkeep` file keeps the uploads folder tracked while ignoring everything users upload.

---

## 🗺 Route map

| URL | Page |
|---|---|
| `/admin/` | Dashboard (admin_index.html) |
| `/admin/products` | Product list |
| `/admin/products/add` | New product form |
| `/admin/products/edit/<id>` | Edit product |
| `/admin/categories` | Categories list + add |
| `/admin/orders` | Orders list (filter via tabs) |
| `/admin/orders/<id>` | Order detail + change status |

---

## 🛠 How to modify ONE feature without touching others

Want to change how **products** look? Only touch:
- `app/templates/admin/products.html` or `product_form.html`
- `app/static/admin/css/products.css`
- `app/static/admin/js/products.js`

The dashboard, categories, and orders stay exactly as they were.

Same logic for every other feature — its three files are isolated.

---

## 🔐 Auth note

The blueprint currently doesn't enforce login. Once `auth.py` from your teammate exposes a `login_required` / `admin_required` decorator, wrap the routes at the top of `admin_routes.py`:

```python
from app.controllers.auth import admin_required

@admin_bp.before_request
@admin_required
def gate(): pass
```
