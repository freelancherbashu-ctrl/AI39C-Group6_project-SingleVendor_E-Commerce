from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.category_model import Category

category_bp = Blueprint('category', __name__)

@category_bp.route('/')
@category_bp.route('/categories')
def categories_list():
    categories = Category.get_all()
    return render_template('list.html', categories=categories)

@category_bp.route('/add-category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        image = request.files.get('image')
        
        if not name:
            flash('Category name is required!', 'danger')
            return render_template('add.html')
        
        from app.controllers.category_controller import save_image
        image_path = save_image(image)
        
        category = Category(name=name, description=description, image=image_path)
        category.save()
        
        flash(f'Category "{name}" added successfully!', 'success')
        return redirect(url_for('category.categories_list'))
    
    return render_template('add.html')

@category_bp.route('/edit-category/<int:category_id>', methods=['GET', 'POST'])
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
        
        from app.controllers.category_controller import save_image
        import os
        
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

@category_bp.route('/delete-category/<int:category_id>')
def delete_category(category_id):
    import os
    category = Category.get_by_id(category_id)
    if category and category.get('image'):
        old_path = os.path.join('static', category['image'])
        if os.path.exists(old_path):
            os.remove(old_path)
    
    Category.delete(category_id)
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('category.categories_list'))