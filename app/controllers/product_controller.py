from flask import render_template, request, redirect, url_for, flash
from app.controllers.base_controller import BaseController
from app.models.product_model import ProductModel
from app.models.category_model import CategoryModel
from app.utils.image_upload import upload_image

class ProductController(BaseController):
    def __init__(self):
        self.model = ProductModel()
        self.cat_model = CategoryModel()
    
    def add_product(self, category_id):
        access = self.check_admin()
        if access:
            return access
        
        category = self.cat_model.find_by_id(category_id)
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            price = request.form.get('price', '').strip()
            stock = request.form.get('stock', '').strip()
            status = request.form.get('status', 'active')
            image_file = request.files.get('image')
            
            if not name or not price:
                flash('Name and price are required!', 'danger')
                return render_template('add_product.html', category=category)
            
            slug = self.model.generate_slug(name)
            
            image_filename = None
            if image_file and image_file.filename:
                filename, error = upload_image(image_file)
                if error:
                    flash(error, 'danger')
                    return render_template('add_product.html', category=category)
                image_filename = f'/static/uploads/{filename}'
            
            self.model.save(category_id, name, slug, description, float(price), int(stock or 0), image_filename, status)
            flash(f'Product "{name}" added!', 'success')
            return redirect(url_for('product.products_list'))
        
        return render_template('add_product.html', category=category)
    
    def products_list(self):
        access = self.check_admin()
        if access:
            return access
        products = self.model.find_all()
        return render_template('products.html', products=products)