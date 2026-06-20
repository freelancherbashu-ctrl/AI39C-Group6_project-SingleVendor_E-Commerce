from flask import render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_required, current_user
from app.models.database import Database
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def view_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = Database()
    user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    db.close()
    return render_template('profile.html', user=user)

def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = Database()
    user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        existing = db.fetch_one("SELECT * FROM users WHERE email = %s AND id != %s", (email, session['user_id']))
        if existing:
            flash('Email already exists!', 'danger')
            return redirect(url_for('auth.edit_profile'))
        db.execute("UPDATE users SET name = %s, email = %s WHERE id = %s", (name, email, session['user_id']))
        db.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.view_profile'))
    db.close()
    return render_template('edit_profile.html', user=user)

def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = Database()
    user = db.fetch_one("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not check_password_hash(user['password'], old_password):
            flash('Old password is incorrect!', 'danger')
            return redirect(url_for('auth.change_password'))
        if new_password != confirm_password:
            flash('New passwords do not match!', 'danger')
            return redirect(url_for('auth.change_password'))
        if len(new_password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return redirect(url_for('auth.change_password'))
        hashed = generate_password_hash(new_password)
        db.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, session['user_id']))
        db.close()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('auth.view_profile'))
    db.close()
    return render_template('change_password.html', user=user)

def upload_photo():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    if 'photo' not in request.files:
        flash('No file selected!', 'danger')
        return redirect(url_for('auth.view_profile'))
    file = request.files['photo']
    if file.filename == '':
        flash('No file selected!', 'danger')
        return redirect(url_for('auth.view_profile'))
    if not allowed_file(file.filename):
        flash('Only JPG, PNG and GIF files allowed!', 'danger')
        return redirect(url_for('auth.view_profile'))
    if file:
        filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
        upload_folder = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        db = Database()
        db.execute("UPDATE users SET profile_picture = %s WHERE id = %s", (filename, session['user_id']))
        db.close()
        flash('Profile picture updated!', 'success')
    return redirect(url_for('auth.view_profile'))