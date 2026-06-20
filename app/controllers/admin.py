import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_image(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    upload_dir = os.path.join(current_app.root_path, "static", "admin", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, unique_name))
    return unique_name


def delete_product_image(filename):
    if not filename:
        return
    path = os.path.join(current_app.root_path, "static", "admin", "uploads", filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
