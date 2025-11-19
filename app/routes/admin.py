import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from ..models.admin import db, IncubateeProduct, Incubatee, PricingUnit, AdminProfile, SalesReport
from datetime import datetime, timedelta
from ..models.user import User
from ..models.reservation import Reservation
from sqlalchemy import func, desc

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

@admin_bp.route("/users")
def users_management():
    """Users management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login.login'))
    return render_template("admin/users.html")

@admin_bp.route("/incubatees")
def incubatees_management():
    """Incubatees management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login.login'))
    return render_template("admin/incubatees.html")

@admin_bp.route("/reports")
def sales_reports():
    """Sales reports page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login.login'))
    
    # Calculate date for 30 days ago
    today = datetime.utcnow().date()
    today_minus_30 = today - timedelta(days=30)
    
    return render_template("admin/reports.html", today=today.isoformat(),today_minus_30=today_minus_30.isoformat())

@admin_bp.route("/get-incubatee-products/<int:incubatee_id>")
def get_incubatee_products(incubatee_id):
    """Get products for a specific incubatee"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        products = IncubateeProduct.query.filter_by(incubatee_id=incubatee_id).all()
        products_list = []
        
        for product in products:
            products_list.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "stock_amount": product.stock_amount,
                "price_per_stocks": float(product.price_per_stocks),
                "image_path": product.image_path})
        
        return jsonify({"success": True, "products": products_list})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# Optional: API endpoint for checking login status
@admin_bp.route("/check-auth")
def check_auth():
    """Check if admin is authenticated (for AJAX calls)"""
    return jsonify({'authenticated': session.get('admin_logged_in', False),'username': session.get('admin_username', None)})
    
@admin_bp.route("/get-pricing-units", methods=["GET"])
def get_pricing_units():
    """Get all available pricing units"""
    try:
        pricing_units = PricingUnit.query.filter_by(is_active=True).all()
        return jsonify({
            "success": True,
            "pricing_units": [{"unit_id": unit.unit_id,"unit_name": unit.unit_name,"unit_description": unit.unit_description
                } for unit in pricing_units]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/add-pricing-unit", methods=["POST"])
def add_pricing_unit():
    """Add a new pricing unit"""
    try:
        data = request.get_json()
        unit_name = data.get("unit_name", "").strip()
        unit_description = data.get("unit_description", "").strip()
        
        if not unit_name:
            return jsonify({"success": False, "error": "Unit name is required"}), 400
            
        # Check if unit already exists
        existing_unit = PricingUnit.query.filter_by(unit_name=unit_name).first()
        if existing_unit:
            return jsonify({"success": False, "error": "Pricing unit already exists"}), 400
            
        pricing_unit = PricingUnit(unit_name=unit_name,unit_description=unit_description)
        
        db.session.add(pricing_unit)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Pricing unit added successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# Update the add_product route to include pricing_unit_id
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
        pricing_unit_id = request.form.get("pricing_unit_id", 1)  # Default to 1 if not provided

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
        product = IncubateeProduct(incubatee_id=incubatee_id,name=name,stock_no=stock_no,products=products,
            stock_amount=stock_amount,price_per_stocks=price_per_stocks,pricing_unit_id=pricing_unit_id, 
            details=details,category=category,expiration_date=expiration_date,warranty=warranty,added_on=added_on,
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

# Update the get_products route to include pricing unit info
@admin_bp.route("/get-products", methods=["GET"])
def get_products():
    try:
        products = (db.session.query(IncubateeProduct).join(PricingUnit).order_by(IncubateeProduct.created_at.desc()).all())

        products_list = []
        for product in products:
            products_list.append({"product_id": product.product_id,"incubatee_id": product.incubatee_id,
                "name": product.name,"stock_no": product.stock_no,"products": product.products,
                "stock_amount": product.stock_amount,"price_per_stocks": float(product.price_per_stocks),
                "pricing_unit": product.pricing_unit.unit_name if product.pricing_unit else "Per Item",
                "pricing_unit_id": product.pricing_unit_id,"details": product.details,"category": product.category or "Uncategorized",
                "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else "No Expiry",
                "warranty": product.warranty or "No Warranty",
                "added_on": product.added_on.strftime("%Y-%m-%d"),"image_path": product.image_path,
                "created_at": product.created_at.strftime("%Y-%m-%d %H:%M:%S"),"updated_at": product.updated_at.strftime("%Y-%m-%d %H:%M:%S"),})

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

@admin_bp.route("/profile")
def admin_profile():
    """Admin profile page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login.login'))
    
    # Get admin profile from database or use session data
    admin_profile = AdminProfile.query.filter_by(username=session.get('admin_username')).first()
    
    return render_template("admin/profile.html", admin_profile=admin_profile)

@admin_bp.route("/update-profile", methods=["POST"])
def update_admin_profile():
    """Update admin profile"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        username = session.get('admin_username')
        
        admin_profile = AdminProfile.query.filter_by(username=username).first()
        if not admin_profile:
            # Create new profile if doesn't exist
            admin_profile = AdminProfile(
                username=username,
                full_name=data.get('full_name'),
                email=data.get('email'),
                phone=data.get('phone')
            )
            db.session.add(admin_profile)
        else:
            admin_profile.full_name = data.get('full_name')
            admin_profile.email = data.get('email')
            admin_profile.phone = data.get('phone')
        
        db.session.commit()
        return jsonify({"success": True, "message": "Profile updated successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/get-users")
def get_users():
    """Get all users with their status"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        users = User.query.all()
        users_list = []
        
        for user in users:
            # Count user's reservations by status
            pending_reservations = Reservation.query.filter_by(user_id=user.id_no, status='pending').count()
            approved_reservations = Reservation.query.filter_by(user_id=user.id_no, status='approved').count()
            completed_reservations = Reservation.query.filter_by(user_id=user.id_no, status='completed').count()
            
            users_list.append({
                "user_id": user.id_no,
                "username": user.username,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
                "total_reservations": pending_reservations + approved_reservations + completed_reservations,
                "pending_reservations": pending_reservations,
                "approved_reservations": approved_reservations,
                "completed_reservations": completed_reservations
            })
        
        return jsonify({"success": True, "users": users_list})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/get-incubatees-list")
def get_incubatees_list():
    """Get all incubatees for management"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        incubatees = Incubatee.query.all()
        incubatees_list = []
        
        for incubatee in incubatees:
            # Count products and calculate total sales
            product_count = IncubateeProduct.query.filter_by(incubatee_id=incubatee.incubatee_id).count()
            
            # Calculate total sales from sales reports
            total_sales = db.session.query(func.coalesce(func.sum(SalesReport.total_price), 0)).filter_by(incubatee_id=incubatee.incubatee_id).scalar()
            
            incubatees_list.append({
                "incubatee_id": incubatee.incubatee_id,
                "full_name": f"{incubatee.first_name} {incubatee.last_name}",
                "company_name": incubatee.company_name,
                "email": incubatee.email,
                "phone": incubatee.phone_number,
                "batch": incubatee.batch,
                "product_count": product_count,
                "total_sales": float(total_sales),
                "is_approved": incubatee.is_approved,
                "created_at": incubatee.created_at.strftime("%Y-%m-%d")
            })
        
        return jsonify({"success": True, "incubatees": incubatees_list})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/toggle-incubatee-approval/<int:incubatee_id>", methods=["POST"])
def toggle_incubatee_approval(incubatee_id):
    """Approve or disapprove an incubatee"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        incubatee = Incubatee.query.get_or_404(incubatee_id)
        incubatee.is_approved = not incubatee.is_approved
        db.session.commit()
        
        action = "approved" if incubatee.is_approved else "disapproved"
        return jsonify({"success": True, "message": f"Incubatee {action} successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/sales-summary")
def sales_summary():
    """Get sales summary per incubatee"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Sales by incubatee
        sales_by_incubatee = db.session.query(
            Incubatee.incubatee_id,
            Incubatee.first_name,
            Incubatee.last_name,
            Incubatee.company_name,
            func.count(SalesReport.report_id).label('total_sales_count'),
            func.coalesce(func.sum(SalesReport.total_price), 0).label('total_revenue')
        ).outerjoin(SalesReport, Incubatee.incubatee_id == SalesReport.incubatee_id
        ).group_by(Incubatee.incubatee_id).all()
        
        # Total statistics
        total_revenue = db.session.query(func.coalesce(func.sum(SalesReport.total_price), 0)).scalar()
        total_orders = db.session.query(func.count(Reservation.reservation_id)).scalar()
        completed_orders = db.session.query(func.count(Reservation.reservation_id)).filter_by(status='completed').scalar()
        
        # Monthly sales trend (last 6 months)
        monthly_sales = db.session.query(
            func.date_trunc('month', SalesReport.sale_date).label('month'),
            func.sum(SalesReport.total_price).label('monthly_revenue')
        ).filter(SalesReport.sale_date >= func.date('now', '-6 months')
        ).group_by(func.date_trunc('month', SalesReport.sale_date)
        ).order_by(func.date_trunc('month', SalesReport.sale_date)).all()
        
        summary = {
            "total_revenue": float(total_revenue),
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "completion_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            "sales_by_incubatee": [
                {
                    "incubatee_id": sale.incubatee_id,
                    "name": f"{sale.first_name} {sale.last_name}",
                    "company": sale.company_name,
                    "sales_count": sale.total_sales_count,
                    "revenue": float(sale.total_revenue)
                } for sale in sales_by_incubatee
            ],
            "monthly_trend": [
                {
                    "month": sale.month.strftime("%Y-%m"),
                    "revenue": float(sale.monthly_revenue) if sale.monthly_revenue else 0
                } for sale in monthly_sales
            ]
        }
        
        return jsonify({"success": True, "summary": summary})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/reports")
def admin_reports():
    """Generate various reports"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Popular products report
        popular_products = db.session.query(
            IncubateeProduct.product_id,
            IncubateeProduct.name,
            Incubatee.company_name,
            func.count(Reservation.reservation_id).label('reservation_count'),
            func.sum(Reservation.quantity).label('total_quantity')
        ).join(Incubatee, IncubateeProduct.incubatee_id == Incubatee.incubatee_id
        ).join(Reservation, IncubateeProduct.product_id == Reservation.product_id
        ).group_by(IncubateeProduct.product_id, Incubatee.company_name
        ).order_by(desc('reservation_count')).limit(10).all()
        
        # Sales performance by category
        category_sales = db.session.query(
            IncubateeProduct.category,
            func.count(Reservation.reservation_id).label('order_count'),
            func.sum(Reservation.quantity * Reservation.price_per_stocks).label('total_revenue')
        ).join(Reservation, IncubateeProduct.product_id == Reservation.product_id
        ).filter(Reservation.status == 'completed'
        ).group_by(IncubateeProduct.category).all()
        
        reports = {
            "popular_products": [
                {
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "company": product.company_name,
                    "reservation_count": product.reservation_count,
                    "total_quantity": product.total_quantity
                } for product in popular_products
            ],
            "category_sales": [
                {
                    "category": sale.category or "Uncategorized",
                    "order_count": sale.order_count,
                    "revenue": float(sale.total_revenue) if sale.total_revenue else 0
                } for sale in category_sales
            ]
        }
        
        return jsonify({"success": True, "reports": reports})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500