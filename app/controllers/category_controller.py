import os
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads/categories'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

def save_image(file):
    if not file or not file.filename:
        return None
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    
    filename = secure_filename(file.filename)
    unique = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique)
    file.save(filepath)
    
    return f"uploads/categories/{unique}"


from flask import render_template, request, redirect, url_for, flash
from app.models.category_model import Category
import os
from datetime import datetime
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/uploads/categories'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}

def save_image(file):
    if not file or not file.filename:
        return None
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    
    filename = secure_filename(file.filename)
    unique = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique)
    file.save(filepath)
    
    return f"uploads/categories/{unique}"

def list_categories():
    categories = Category.get_all()
    return render_template('list.html', categories=categories)

def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        image = request.files.get('image')
        
        if not name:
            flash('Category name is required!', 'danger')
            return render_template('add.html')
        
        image_path = save_image(image)
        
        category = Category(name=name, description=description, image=image_path)
        category.save()
        
        flash(f'Category "{name}" added successfully!', 'success')
        return redirect(url_for('category.categories_list'))
    
    return render_template('add.html')

def edit_category(category_id):
    category = Category.get_by_id(category_id)
    if not category:
        flash('Category not found!', 'danger')
        return redirect(url_for('category.categories_list'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        image = request.files.get('image')
        delete_image = request.form.get('delete_image')
        
        if not name:
            flash('Category name is required!', 'danger')
            return render_template('edit.html', category=category)
        
        image_path = category.get('image')
        
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
            new_path = save_image(image)
            if new_path:
                image_path = new_path
        
        cat = Category(name=name, description=description, image=image_path)
        cat.update(category_id)
        
        flash(f'Category "{name}" updated successfully!', 'success')
        return redirect(url_for('category.categories_list'))
    
    return render_template('edit.html', category=category)

def delete_category(category_id):
    category = Category.get_by_id(category_id)
    if category and category.get('image'):
        old_path = os.path.join('static', category['image'])
        if os.path.exists(old_path):
            os.remove(old_path)
    
    Category.delete(category_id)
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('category.categories_list'))