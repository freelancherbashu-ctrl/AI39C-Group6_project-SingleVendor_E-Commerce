from flask import render_template, request, redirect, url_for, flash
from app.models.category_model import CategoryModel

class CategoryController:
    def __init__(self):
        self.model = CategoryModel()
    
    def add_category(self):
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            image = request.form.get('image', '').strip()
            
            if not name:
                flash('Category name is required!', 'danger')
                return redirect(url_for('category.add_category'))
            
            self.model.save(name, description, image if image else None)
            flash(f'Category "{name}" added successfully!', 'success')
            return redirect(url_for('category.categories_list'))
        
        return render_template('add_category.html')
    
    def list_categories(self):
        categories = self.model.find_all()
        return render_template('categories.html', categories=categories)