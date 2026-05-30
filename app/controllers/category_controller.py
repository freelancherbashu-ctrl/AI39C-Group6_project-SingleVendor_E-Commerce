from flask import render_template, request, redirect, url_for, flash
from app.controllers.base_controller import BaseController
from app.models.category_model import CategoryModel
from app.utils.image_upload import upload_image

class CategoryController(BaseController):
    def __init__(self):
        self.model = CategoryModel()
    
    def add_category(self):
        access = self.check_admin()
        if access:
            return access
        
        if request.method == 'POST':
            name, description, status = self.get_form_data('name', 'description', 'status')
            image_file = request.files.get('image')
            
            if not name:
                flash('Category name is required!', 'danger')
                return render_template('add_category.html')
            
            if self.model.name_exists(name):
                flash(f'Category "{name}" already exists!', 'danger')
                return render_template('add_category.html')
            
            slug = self.model.generate_slug(name)
            
            if self.model.slug_exists(slug):
                flash('A category with similar name exists!', 'danger')
                return render_template('add_category.html')
            
            # Image Upload
            image_filename = None
            if image_file and image_file.filename:
                filename, error = upload_image(image_file)
                if error:
                    flash(error, 'danger')
                    return render_template('add_category.html')
                image_filename = f'/static/uploads/{filename}'
            
            self.model.save(name, slug, description, image_filename, status)
            flash(f'Category "{name}" added successfully!', 'success')
            return redirect(url_for('category.categories_list'))
        
        return render_template('add_category.html')
    
    def list_categories(self):
        access = self.check_admin()
        if access:
            return access
        categories = self.model.find_all()
        return render_template('categories.html', categories=categories)
    
    def delete_category(self, id):
        access = self.check_admin()
        if access:
            return access
        category = self.model.find_by_id(id)
        if category:
            self.model.delete_by_id(id)
            flash(f'Category "{category["name"]}" deleted!', 'success')
        else:
            flash('Category not found!', 'danger')
        return redirect(url_for('category.categories_list'))