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

# Update these paths to be relative to your app
LOGO_UPLOAD_FOLDER = "static/incubatee_logo"  # Changed to relative path
LOGO_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_logo_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in LOGO_ALLOWED_EXTENSIONS

def get_logo_url(logo_path):
    """Get the URL path for the logo"""
    if logo_path:
        return f"/static/incubatee_logo/{logo_path}"
    return None

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
            
        # Check if unit already exists (case-insensitive)
        existing_unit = PricingUnit.query.filter(db.func.lower(PricingUnit.unit_name) == db.func.lower(unit_name)).first()
        
        if existing_unit:
            # Return success but indicate it's an existing unit
            return jsonify({"success": True, "message": "Pricing unit already exists","unit_id": existing_unit.unit_id,"existing": True})
            
        # Create new pricing unit with is_active=True by default
        pricing_unit = PricingUnit(unit_name=unit_name,unit_description=unit_description if unit_description else None,is_active=True, created_at=datetime.utcnow())
        
        db.session.add(pricing_unit)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Pricing unit added successfully!","unit_id": pricing_unit.unit_id,"existing": False})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding pricing unit: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
        
@admin_bp.route("/search-pricing-units", methods=["GET"])
def search_pricing_units():
    """Search pricing units by name or description"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        query = request.args.get('q', '').strip().lower()
        
        if not query:
            pricing_units = PricingUnit.query.filter_by(is_active=True).all()
        else:
            pricing_units = PricingUnit.query.filter(
                PricingUnit.is_active == True,
                db.or_(
                    PricingUnit.unit_name.ilike(f'%{query}%'),
                    PricingUnit.unit_description.ilike(f'%{query}%')
                )
            ).all()
        
        return jsonify({"success": True,"pricing_units": [{"unit_id": unit.unit_id,"unit_name": unit.unit_name,"unit_description": unit.unit_description} for unit in pricing_units]})
        
    except Exception as e:
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

@admin_bp.route("/get-products", methods=["GET"])
def get_products():
    """Get all products for display in admin panel"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Get all products with incubatee information
        products = IncubateeProduct.query.options(
            db.joinedload(IncubateeProduct.incubatee),
            db.joinedload(IncubateeProduct.pricing_unit)
        ).all()
        
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
                "pricing_unit": product.pricing_unit.unit_name if product.pricing_unit else "N/A",
                "pricing_unit_id": product.pricing_unit_id,
                "details": product.details,
                "category": product.category,
                "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else "N/A",
                "warranty": product.warranty,
                "added_on": product.added_on.strftime("%Y-%m-%d") if product.added_on else "N/A",
                "image_path": product.image_path,
                "incubatee_name": f"{product.incubatee.first_name} {product.incubatee.last_name}" if product.incubatee else "Unknown"
            })
        
        return jsonify({"success": True, "products": products_list})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/add-incubatee", methods=["POST"])
def add_incubatee():
    """Add a new incubatee (person/company)"""
    try:
        # Check if it's form data (with file) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Handle form data with file upload
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            middle_name = request.form.get("middle_name", "").strip()
            company_name = request.form.get("company_name", "").strip()
            website = request.form.get("website", "").strip()
            email = request.form.get("email", "").strip()
            phone_number = request.form.get("phone_number", "").strip()
            contact_info = request.form.get("contact_info", "").strip()
            batch = request.form.get("batch", "").strip()
            
            # Handle logo file upload
            logo_path = None
            logo_file = request.files.get("company_logo")
            if logo_file and logo_file.filename != '':
                if allowed_logo_file(logo_file.filename):
                    # Generate secure filename
                    file_extension = logo_file.filename.rsplit('.', 1)[1].lower()
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    filename = f"logo_{timestamp}.{file_extension}"
                    filename = secure_filename(filename)
                    
                    # Save file
                    save_path = os.path.join(current_app.root_path, 'static', 'incubatee_logo', filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    logo_file.save(save_path)
                    logo_path = filename
                else:
                    return jsonify({
                        "success": False, 
                        "error": f"Invalid file type. Allowed types: {', '.join(LOGO_ALLOWED_EXTENSIONS)}"
                    }), 400
        else:
            # Handle JSON data (backward compatibility)
            data = request.get_json()
            first_name = data.get("first_name", "").strip()
            last_name = data.get("last_name", "").strip()
            middle_name = data.get("middle_name", "").strip()
            company_name = data.get("company_name", "").strip()
            website = data.get("website", "").strip()
            email = data.get("email", "").strip()
            phone_number = data.get("phone_number", "").strip()
            contact_info = data.get("contact_info", "").strip()
            batch = data.get("batch", "").strip()
            logo_path = None

        # Validate required fields
        if not first_name or not last_name:
            return jsonify({"success": False, "error": "First name and last name are required"}), 400

        # Convert batch to integer if provided
        batch_int = None
        if batch:
            try:
                batch_int = int(batch)
            except ValueError:
                return jsonify({"success": False, "error": "Batch must be a valid number"}), 400

        # Create incubatee - Set empty strings to None for database
        incubatee = Incubatee(
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name if middle_name else None,
            contact_info=contact_info if contact_info else None,
            batch=batch_int,
            company_name=company_name if company_name else None,
            website=website if website else None,
            email=email if email else None,
            phone_number=phone_number if phone_number else None,
            logo_path=logo_path  # This can be None if no logo uploaded
        )
        
        db.session.add(incubatee)
        db.session.commit()

        return jsonify({"success": True, "message": "Incubatee added successfully!","incubatee_id": incubatee.incubatee_id})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding incubatee: {str(e)}")
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
                    "first_name": i.first_name or "",
                    "last_name": i.last_name or "",
                    "middle_name": i.middle_name or "",
                    "company_name": i.company_name or "",
                    "website": i.website or "",
                    "logo_url": i.logo_url or "",  # Include logo URL
                    "email": i.email or "",
                    "phone_number": i.phone_number or "",
                    "batch": i.batch or "",
                    "full_name": i.full_name  # Include full name for display
                } for i in incubatees
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching incubatees: {str(e)}")
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
            
            users_list.append({"user_id": user.id_no,"username": user.username,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M"),
                "total_reservations": pending_reservations + approved_reservations + completed_reservations,
                "pending_reservations": pending_reservations,
                "approved_reservations": approved_reservations,"completed_reservations": completed_reservations})
        
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
            # Count products for this incubatee
            product_count = IncubateeProduct.query.filter_by(incubatee_id=incubatee.incubatee_id).count()
            
            # Calculate total sales from sales reports
            total_sales_result = db.session.query(func.coalesce(func.sum(SalesReport.total_price), 0)).filter(SalesReport.incubatee_id == incubatee.incubatee_id).scalar()
            total_sales = float(total_sales_result) if total_sales_result else 0.0
            
            incubatees_list.append({
                "incubatee_id": incubatee.incubatee_id,
                "full_name": f"{incubatee.first_name} {incubatee.last_name}",
                "company_name": incubatee.company_name or "No Company",
                "website": incubatee.website,
                "logo_url": incubatee.logo_url,  # Add logo URL
                "email": incubatee.email or "No email",
                "phone": incubatee.phone_number or "No phone",
                "batch": incubatee.batch,
                "product_count": product_count,
                "total_sales": total_sales,
                "is_approved": incubatee.is_approved if hasattr(incubatee, 'is_approved') else False,
                "created_at": incubatee.created_at.strftime("%Y-%m-%d") if incubatee.created_at else "Unknown"
            })
        
        return jsonify({"success": True, "incubatees": incubatees_list})
        
    except Exception as e:
        current_app.logger.error(f"Error in get_incubatees_list: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to load incubatees: {str(e)}"}), 500

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
        # Sales by incubatee - FIXED: Use sales_id instead of report_id
        sales_by_incubatee = db.session.query(
            Incubatee.incubatee_id,
            Incubatee.first_name,
            Incubatee.last_name,
            Incubatee.company_name,
            func.count(SalesReport.sales_id).label('total_sales_count'),  # FIXED
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
                } for sale in monthly_sales]}
        
        return jsonify({"success": True, "summary": summary})
        
    except Exception as e:
        current_app.logger.error(f"Error in sales_summary: {e}")
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
    

@admin_bp.route("/get-product/<int:product_id>")
def get_product(product_id):
    """Get product data for editing"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        product = IncubateeProduct.query.options(
            db.joinedload(IncubateeProduct.incubatee),
            db.joinedload(IncubateeProduct.pricing_unit)
        ).get_or_404(product_id)
        
        product_data = {
            "product_id": product.product_id,
            "name": product.name,
            "stock_no": product.stock_no,
            "products": product.products,
            "stock_amount": product.stock_amount,
            "price_per_stocks": float(product.price_per_stocks),
            "pricing_unit_id": product.pricing_unit_id,
            "details": product.details,
            "category": product.category,
            "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else None,
            "warranty": product.warranty,
            "image_path": product.image_path,
            "incubatee_name": f"{product.incubatee.first_name} {product.incubatee.last_name}" if product.incubatee else "Unknown"
        }
        
        return jsonify({"success": True, "product": product_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching product {product_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/update-product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    """Update product information"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        product = IncubateeProduct.query.get_or_404(product_id)
        updated_fields = []
        
        # Handle form data
        form_data = request.form
        
        # Update basic fields
        if 'name' in form_data and form_data['name'] != product.name:
            product.name = form_data['name']
            updated_fields.append('name')
            
        if 'stock_no' in form_data and form_data['stock_no'] != product.stock_no:
            product.stock_no = form_data['stock_no']
            updated_fields.append('stock_no')
            
        if 'products' in form_data and form_data['products'] != product.products:
            product.products = form_data['products']
            updated_fields.append('products')
            
        if 'stock_amount' in form_data:
            try:
                new_stock = int(form_data['stock_amount'])
                if new_stock != product.stock_amount:
                    product.stock_amount = new_stock
                    updated_fields.append('stock_amount')
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid stock amount"}), 400
                
        if 'price_per_stocks' in form_data:
            try:
                new_price = float(form_data['price_per_stocks'])
                if new_price != product.price_per_stocks:
                    product.price_per_stocks = new_price
                    updated_fields.append('price_per_stocks')
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid price per stock"}), 400
                
        if 'pricing_unit_id' in form_data:
            try:
                new_unit_id = int(form_data['pricing_unit_id'])
                if new_unit_id != product.pricing_unit_id:
                    product.pricing_unit_id = new_unit_id
                    updated_fields.append('pricing_unit_id')
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid pricing unit ID"}), 400
                
        if 'details' in form_data and form_data['details'] != product.details:
            product.details = form_data['details']
            updated_fields.append('details')
            
        if 'category' in form_data and form_data['category'] != product.category:
            product.category = form_data['category']
            updated_fields.append('category')
            
        if 'warranty' in form_data and form_data['warranty'] != product.warranty:
            product.warranty = form_data['warranty'] if form_data['warranty'] else None
            updated_fields.append('warranty')
            
        # Handle expiration date
        if 'expiration_date' in form_data:
            new_expiration = None
            if form_data['expiration_date']:
                try:
                    new_expiration = datetime.strptime(form_data['expiration_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({"success": False, "error": "Invalid expiration date format"}), 400
            
            current_expiration = product.expiration_date
            if new_expiration != current_expiration:
                product.expiration_date = new_expiration
                updated_fields.append('expiration_date')
        
        # Handle image upload
        if 'product_image' in request.files:
            image_file = request.files['product_image']
            if image_file and image_file.filename and allowed_file(image_file.filename):
                # Generate secure filename
                file_extension = image_file.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"product_{product_id}_{timestamp}.{file_extension}"
                filename = secure_filename(filename)
                
                # Save the new image
                save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                image_file.save(save_path)
                
                # Delete old image if exists
                if product.image_path:
                    try:
                        old_image_path = os.path.join(current_app.root_path, product.image_path)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        current_app.logger.warning(f"Failed to delete old product image: {str(e)}")
                
                product.image_path = f"{UPLOAD_FOLDER}/{filename}"
                updated_fields.append('image_path')
        
        # Only update timestamp and commit if there are actual changes
        if updated_fields:
            product.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({
                "success": True,
                "message": f"Product updated successfully! Updated fields: {', '.join(updated_fields)}",
                "updated_fields": updated_fields
            })
        else:
            return jsonify({
                "success": True,
                "message": "No changes detected - product information is up to date",
                "updated_fields": []
            })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating product {product_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500