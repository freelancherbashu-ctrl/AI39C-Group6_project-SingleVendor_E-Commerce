from flask import render_template, request, redirect, url_for, flash, session
from app.models.user_models import User
from app.models.database import Database
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import secrets

class AuthController:
    
    def register(self):
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            errors = []
            if not name:
                errors.append("Name is required")
            if not email:
                errors.append("Email is required")
            if len(password) < 6:
                errors.append("Password must be at least 6 characters")
            if password != confirm_password:
                errors.append("Passwords do not match")

            existing_user = User.find_by_email(email)
            if existing_user:
                errors.append("Email already registered")

            if errors:
                return render_template('register.html', errors=errors, name=name, email=email)

            User.create(name, email, password)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('authroutes.login'))

        return render_template('register.html')

    def login(self):
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            user = User.find_by_email(email)

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['role'] = user.get('role', 'customer')
                
                flash(f'Welcome {user["name"]}!', 'success')
                
                if session['role'] == 'admin':
                    return redirect(url_for('authroutes.admin_dashboard'))
                else:
                    return redirect(url_for('authroutes.customer_dashboard'))
            else:
                flash('Invalid email or password', 'error')
                return redirect(url_for('authroutes.login'))

        return render_template('login.html')

    def logout(self):
        session.clear()
        flash('You have been logged out.', 'success')
        return redirect(url_for('authroutes.login'))

    def forgot_password(self):
        if request.method == 'POST':
            email = request.form.get('email')
            user = User.find_by_email(email)
        
            if not user:
                flash('Email not found in our records', 'error')
                return redirect(url_for('authroutes.forgot_password'))
        
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=24)
        
            db = Database()
            db.execute(
                "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE email = %s",
                (token, expiry, email)
            )
            db.close()
        
            reset_link = url_for('authroutes.reset_password', token=token, _external=True)
        
            flash(f'Reset link: {reset_link}', 'info')
            return redirect(url_for('authroutes.login'))
    
        return render_template('forgot_password.html')

    def reset_password(self, token):
        db = Database()
        user = db.fetch_one(
            "SELECT * FROM users WHERE reset_token = %s AND reset_token_expiry > %s",
            (token, datetime.now())
        )
        db.close()
        
        if not user:
            flash('Invalid or expired reset link', 'error')
            return redirect(url_for('authroutes.forgot_password'))
        
        if request.method == 'POST':
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters', 'error')
                return render_template('reset_password.html', token=token)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('reset_password.html', token=token)
            
            from werkzeug.security import generate_password_hash
            hashed_password = generate_password_hash(password)
            
            db = Database()
            db.execute(
                "UPDATE users SET password = %s, reset_token = NULL, reset_token_expiry = NULL WHERE reset_token = %s",
                (hashed_password, token)
            )
            db.close()
            
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('authroutes.login'))
        
        return render_template('reset_password.html', token=token)

    
    
    def customer_dashboard(self):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('authroutes.login'))
        
        if session.get('role') == 'admin':
            return redirect(url_for('authroutes.admin_dashboard'))
        
        return render_template('customer_dashboard.html', name=session.get('user_name'))

    def admin_dashboard(self):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('authroutes.login'))
        
        if session.get('role') != 'admin':
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('authroutes.customer_dashboard'))
        
        return render_template('admin_dashboard.html', name=session.get('user_name'))