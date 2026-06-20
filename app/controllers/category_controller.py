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