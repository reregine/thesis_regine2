import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from ..models.admin import db, IncubateeProduct
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Admin credentials (in production, use environment variables or database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin2025_atbi"

# Folder where images will be uploaded (inside /static/uploads)
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route("/")
def admin_dashboard():
    """Admin dashboard - protected route"""
    # Check if user is logged in
    if not session.get('admin_logged_in'):
        return redirect(url_for('login.login'))  # Redirect to your login route
    
    return render_template("admin/admin.html")

@admin_bp.route("/login", methods=["POST"])
def admin_login_post():
    """Handle login form submission"""
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # Validate credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': '✅ Login successful! Welcome Admin!',
                    'redirect_url': url_for('admin.admin_dashboard')
                })
            else:
                return redirect(url_for('admin.admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': '❌ Invalid username or password'
                }), 401
            else:
                # Redirect back to login with error
                return redirect(url_for('login.login', error="Invalid credentials"))
                
    except Exception as e:
        if request.is_json:
            return jsonify({
                'success': False,
                'message': '❌ Login error occurred'
            }), 500
        else:
            return redirect(url_for('login.login', error="Login error occurred"))

@admin_bp.route("/logout")
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin.admin_login'))

# Optional: API endpoint for checking login status
@admin_bp.route("/check-auth")
def check_auth():
    """Check if admin is authenticated (for AJAX calls)"""
    return jsonify({
        'authenticated': session.get('admin_logged_in', False),
        'username': session.get('admin_username', None)})
    
@admin_bp.route("/add-product", methods=["POST"])
def add_product():
    try:
        # Required text fields
        name = request.form.get("name")
        stock_no = request.form.get("stock_no")
        products = request.form.get("products")
        details = request.form.get("details")

        # Validate numbers
        try:
            stock_amount = int(request.form.get("stock_amount", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid stock amount"}), 400

        try:
            price_per_stocks = float(request.form.get("price_per_stocks", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid price per stock"}), 400

        # Validate dates
        try:
            expiration_date = datetime.strptime(request.form.get("expiration_date"), "%Y-%m-%d").date()
            added_on = datetime.strptime(request.form.get("added_on"), "%Y-%m-%d").date()
        except Exception:
            return jsonify({"success": False, "error": "Invalid date format"}), 400

        # Handle image
        image = request.files.get("product_image")
        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            image.save(save_path)

        # Create product object
        product = IncubateeProduct(
            name=name,
            stock_no=stock_no,
            products=products,
            stock_amount=stock_amount,
            price_per_stocks=price_per_stocks,
            details=details,
            expiration_date=expiration_date,
            added_on=added_on,
            image_path=f"{UPLOAD_FOLDER}/{filename}" if filename else None
        )

        db.session.add(product)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Product saved successfully!",
            "filename": filename
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in add_product: {e}")  #log actual error
        return jsonify({"success": False, "error": str(e)}), 400
