import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from ..models.admin import db, IncubateeProduct, Incubatee
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
                return jsonify({'success': True,'message': '✅ Login successful! Welcome Admin!','redirect_url': url_for('admin.admin_dashboard')})
            else:
                return redirect(url_for('admin.admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False,'message': '❌ Invalid username or password'}), 401
            else:
                # Redirect back to login with error
                return redirect(url_for('login.login', error="Invalid credentials"))
                
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'message': '❌ Login error occurred'}), 500
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
    return jsonify({'authenticated': session.get('admin_logged_in', False),'username': session.get('admin_username', None)})
    
@admin_bp.route("/add-product", methods=["POST"])
def add_product():
    try:
        incubatee_id = request.form.get("incubatee_id")
        name = request.form.get("name")
        stock_no = request.form.get("stock_no")
        products = request.form.get("products")
        details = request.form.get("details")
        warranty = request.form.get("warranty")
        category = request.form.get("category")

        # Validate required incubatee_id
        if not incubatee_id:
            return jsonify({"success": False, "error": "Incubatee ID is required"}), 400

        # Validate numbers
        try:
            stock_amount = int(request.form.get("stock_amount", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid stock amount"}), 400

        try:
            price_per_stocks = float(request.form.get("price_per_stocks", 0))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid price per stock"}), 400

        # Handle optional expiration date
        expiration_date = None
        if request.form.get("expiration_date"):
            try:
                expiration_date = datetime.strptime(request.form.get("expiration_date"), "%Y-%m-%d").date()
            except Exception:
                return jsonify({"success": False, "error": "Invalid expiration date"}), 400

        # Added on date (default to today if empty)
        added_on_str = request.form.get("added_on")
        added_on = datetime.strptime(added_on_str, "%Y-%m-%d").date() if added_on_str else datetime.utcnow().date()

        # Handle image upload
        image = request.files.get("product_image")
        filename = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            image.save(save_path)

        # Create product entry
        product = IncubateeProduct(
            incubatee_id=incubatee_id,
            name=name,
            stock_no=stock_no,
            products=products,
            stock_amount=stock_amount,
            price_per_stocks=price_per_stocks,
            details=details,
            category=category,
            expiration_date=expiration_date,
            warranty=warranty,
            added_on=added_on,
            image_path=f"{UPLOAD_FOLDER}/{filename}" if filename else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow())

        db.session.add(product)
        db.session.commit()

        return jsonify({"success": True, "message": "✅ Product saved successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in add_product: {e}")
        return jsonify({"success": False, "error": str(e)}), 400


@admin_bp.route("/get-products", methods=["GET"])
def get_products():
    try:
        products = (db.session.query(IncubateeProduct).order_by(IncubateeProduct.created_at.desc()).all())

        products_list = []
        for product in products:
            products_list.append({
                "product_id": product.product_id,
                "incubatee_id": product.incubatee_id,
                "name": product.name,
                "stock_no": product.stock_no,
                "products": product.products,
                "stock_amount": product.stock_amount,
                "price_per_stocks": float(product.price_per_stocks),
                "details": product.details,
                "category": product.category or "Uncategorized",
                "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else "No Expiry",
                "warranty": product.warranty or "No Warranty",
                "added_on": product.added_on.strftime("%Y-%m-%d"),
                "image_path": product.image_path,
                "created_at": product.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": product.updated_at.strftime("%Y-%m-%d %H:%M:%S"),})

        return jsonify({"success": True, "products": products_list})

    except Exception as e:
        current_app.logger.error(f"Error fetching products: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/delete-product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    try:
        product = IncubateeProduct.query.get_or_404(product_id)

        # Delete image if exists
        if product.image_path:
            try:
                image_path = os.path.join(current_app.root_path, product.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                current_app.logger.warning(f"Image delete failed: {e}")

        db.session.delete(product)
        db.session.commit()

        return jsonify({"success": True, "message": "🗑️ Product deleted successfully"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/add-incubatee", methods=["POST"])
def add_incubatee():
    """Add a new incubatee (person/company)"""
    try:
        data = request.get_json()
        incubatee = Incubatee(
            last_name=data.get("last_name"),
            first_name=data.get("first_name"),
            middle_name=data.get("middle_name"),
            contact_info=data.get("contact_info"),
            batch=data.get("batch"),
            new_field=data.get("new_field"),
            company_name=data.get("company_name"),
            email=data.get("email"),
            phone_number=data.get("phone_number")
        )
        db.session.add(incubatee)
        db.session.commit()
        return jsonify({"success": True, "message": "Incubatee added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-incubatees", methods=["GET"])
def get_incubatees():
    """Return incubatees for dropdown selection"""
    try:
        incubatees = Incubatee.query.order_by(Incubatee.last_name.asc()).all()
        return jsonify({
            "success": True,
            "incubatees": [
                {
                    "incubatee_id": i.incubatee_id,
                    "first_name": i.first_name,
                    "last_name": i.last_name,
                    "company_name": i.company_name
                } for i in incubatees
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

