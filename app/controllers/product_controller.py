# from flask import render_template, request, redirect, url_for, flash
# from app.controllers.base_controller import BaseController
# from app.models.product_model import ProductModel
# from app.models.category_model import CategoryModel
# from app.utils.image_upload import upload_image

# class ProductController(BaseController):
#     def __init__(self):
#         self.model = ProductModel()
#         self.cat_model = CategoryModel()
    
#     def add_product(self, category_id):
#         access = self.check_admin()
#         if access:
#             return access
        
#         category = self.cat_model.find_by_id(category_id)
        
#         if request.method == 'POST':
#             name = request.form.get('name', '').strip()
#             description = request.form.get('description', '').strip()
#             price = request.form.get('price', '').strip()
#             stock = request.form.get('stock', '').strip()
#             status = request.form.get('status', 'active')
#             image_file = request.files.get('image')
            
#             if not name or not price:
#                 flash('Name and price are required!', 'danger')
#                 return render_template('add_product.html', category=category)
            
#             slug = self.model.generate_slug(name)
            
#             image_filename = None
#             if image_file and image_file.filename:
#                 filename, error = upload_image(image_file)
#                 if error:
#                     flash(error, 'danger')
#                     return render_template('add_product.html', category=category)
#                 image_filename = f'/static/uploads/{filename}'
            
#             self.model.save(category_id, name, slug, description, float(price), int(stock or 0), image_filename, status)
#             flash(f'Product "{name}" added!', 'success')
#             return redirect(url_for('product.products_list'))
        
#         return render_template('add_product.html', category=category)
    
#     def products_list(self):
#         access = self.check_admin()
#         if access:
#             return access
#         products = self.model.find_all()
#         return render_template('products.html', products=products)



from flask import render_template, request, redirect, url_for, session, flash
from app.models.product_model import Product
from app.models.category_model import Category  # CategoryModel → Category
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

def is_admin():
    return session.get('role') == 'admin'

def generate_slug(name):
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug

def save_product_image(image):
    if not image or not image.filename:
        return None
    
    os.makedirs('static/uploads/products', exist_ok=True)
    
    filename = secure_filename(image.filename)
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    filepath = os.path.join('static/uploads/products', unique_filename)
    image.save(filepath)
    
    return f"uploads/products/{unique_filename}"

def list_products():
    if not is_admin():
        flash('Please login as admin', 'danger')
        return redirect(url_for('auth.login'))
    
    products = Product.get_all()
    return render_template('products/list.html', products=products)

def add_product():
    if not is_admin():
        flash('Please login as admin', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', 0)
        stock = request.form.get('stock', 0)
        category_id = request.form.get('category_id')
        image = request.files.get('image')
        
        if not name:
            flash('Product name is required', 'danger')
            categories = Category.get_all()
            return render_template('products/add.html', categories=categories)
        
        slug = generate_slug(name)
        if Product.slug_exists(slug):
            slug = f"{slug}-{int(datetime.now().timestamp())}"
        
        image_path = save_product_image(image)
        
        product = Product(
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id if category_id and category_id != '' else None,
            image=image_path
        )
        product.save()
        
        flash(f'Product "{name}" added successfully!', 'success')
        return redirect(url_for('product.list_products'))
    
    categories = Category.get_all()
    return render_template('products/add.html', categories=categories)

def edit_product(product_id):
    if not is_admin():
        flash('Please login as admin', 'danger')
        return redirect(url_for('auth.login'))
    
    product = Product.get_by_id(product_id)
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('product.list_products'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price', 0)
        stock = request.form.get('stock', 0)
        category_id = request.form.get('category_id')
        image = request.files.get('image')
        delete_image = request.form.get('delete_image')
        
        if not name:
            flash('Product name is required', 'danger')
            categories = Category.get_all()
            return render_template('products/edit.html', product=product, categories=categories)
        
        slug = generate_slug(name)
        if Product.slug_exists(slug, exclude_id=product_id):
            slug = f"{slug}-{int(datetime.now().timestamp())}"
        
        image_path = product.get('image')
        
        if delete_image == 'yes':
            if image_path:
                old_path = os.path.join('static', image_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            image_path = None
        
        if image and image.filename:
            if image_path:
                old_path = os.path.join('static', image_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            image_path = save_product_image(image)
        
        prod = Product(
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id if category_id and category_id != '' else None,
            image=image_path
        )
        prod.update(product_id)
        
        flash(f'Product "{name}" updated!', 'success')
        return redirect(url_for('product.list_products'))
    
    categories = Category.get_all()
    return render_template('products/edit.html', product=product, categories=categories)

def delete_product(product_id):
    if not is_admin():
        flash('Please login as admin', 'danger')
        return redirect(url_for('auth.login'))
    
    product = Product.get_by_id(product_id)
    if product and product.get('image'):
        old_path = os.path.join('static', product['image'])
        if os.path.exists(old_path):
            os.remove(old_path)
    
    Product.delete(product_id)
    flash('Product deleted!', 'success')
    return redirect(url_for('product.list_products'))