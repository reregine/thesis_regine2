import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from werkzeug.utils import secure_filename
from ..models.admin import ProductPopularity, ProductSalesLog, db, IncubateeProduct, Incubatee, PricingUnit, AdminProfile, SalesReport
from datetime import datetime, timedelta
from ..models.user import User
from ..models.reservation import Reservation
from sqlalchemy import func, desc
import redis, json

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
last_notification_time = {}
redis_client = None

last_notification_time = {}
email_counter = {}  # Track email counts per 5-minute window
MAX_EMAILS_PER_5_MIN = 2  # Maximum 2 emails per 5 minutes
    
def get_redis_client():
    """Get redis client with lazy inizialization"""
    global redis_client
    if redis_client is None:
        try:
            redis_url = os.environ.get('redis_url')
            if redis_url:
                redis_client = redis.from_url(redis_url)
            else:
                #Fallback to local redis if no environment variable
                redis_client = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)
        except Exception as e:
            current_app.logger.error(f"Redis Connection failed: {str(e)}")
            redis_client = None
    return redis_client

def cache_key(prefix, *args):
    """Generate cache key with prefix and arguments"""
    key_parts = [prefix] + [str(arg) for arg in args]
    return ":".join(key_parts)

def get_cached_data(key, expire_seconds=3600):
    """Get data from cache, return (data, found) tuple"""
    redis_client = get_redis_client()
    if not redis_client:
        return None, False
    
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached), True
        return None, False
    except Exception as e:
        current_app.logger.warning(f"Cache get error for key {key}: {str(e)}")
        return None, False
    
def set_cached_data(key, data, expire_seconds=3600):
    """Set data in cache with expiration"""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(key, expire_seconds, json.dumps(data, default=str))
    except Exception as e:
        current_app.logger.warning(f"Cache set error for key {key}: {str(e)}")
def invalidate_cache(pattern):
    """Invalidate cache keys matching pattern"""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        current_app.logger.warning(f"Cache invalidation error for pattern {pattern}: {str(e)}")
        
def allowed_logo_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in LOGO_ALLOWED_EXTENSIONS

def get_logo_url(logo_path):
    """Get the URL path for the logo"""
    if logo_path:
        return f"static/incubatee_logo/{logo_path}"
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
            
            #Invalidate any cached admin data on login
            invalidate_cache("admin:*")
            
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
    invalidate_cache("admin:*")
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

@admin_bp.route("/get-incubatee-logo/<int:incubatee_id>")
def get_incubatee_logo(incubatee_id):
    """Get incubatee logo via API- with caching"""
    cache_key_str = cache_key("incubatee_logo", incubatee_id)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=86400)  # 24 hours cache
    if found:
        return jsonify(cached_data)
    try:
        incubatee = Incubatee.query.get_or_404(incubatee_id)
        
        if not incubatee.logo_path:
            response_data = {"success": False, "error": "No logo available"}
            set_cached_data(cache_key_str, response_data, 3600) #cache negative result for 1 hour
            return jsonify(response_data), 404
            
        # Return the logo URL using the model's property
        response_data = {"success": True, "logo_url": incubatee.logo_url,"company_name": incubatee.company_name}
        set_cached_data(cache_key_str, response_data, 86400)  # Cache for 24 hours
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-incubatee-details/<int:incubatee_id>")
def get_incubatee_details(incubatee_id):
    """Get complete incubatee details including logo URL - WITH CACHING"""
    cache_key_str = cache_key("incubatee_details", incubatee_id)
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        incubatee = Incubatee.query.get_or_404(incubatee_id)
        
        # Get incubatee products
        products = IncubateeProduct.query.filter_by(incubatee_id=incubatee_id).all()
        products_list = []
        
        for product in products:
            product_data = {"product_id": product.product_id,"name": product.name,
                "category": product.category,"description": product.details,"price": float(product.price_per_stocks),
                "stock": product.stock_amount,"image_path": product.image_path}
            # Add image URL if exists
            if product.image_path:
                product_data["image_url"] = url_for('static', filename=product.image_path)
            products_list.append(product_data)
        
        # Build response with proper URLs
        response_data = {
            "success": True,
            "incubatee": {"id": incubatee.incubatee_id,"company_name": incubatee.company_name,
                "full_name": f"{incubatee.first_name} {incubatee.last_name}",
                "email": incubatee.email,"phone": incubatee.phone_number,"website": incubatee.website,
                "contact_info": incubatee.contact_info,"batch": incubatee.batch,
                "year_joined": incubatee.created_at.year if incubatee.created_at else None,
                "description": incubatee.contact_info or "No description available",
                "logo_url": url_for('static', filename=f'incubatee_logo/{incubatee.logo_path}') if incubatee.logo_path else None,
                "logo_path": incubatee.logo_path,  # Keep for reference
                "products": products_list,
                "product_count": len(products_list)}}
        
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-incubatee-products/<int:incubatee_id>")
def get_incubatee_products(incubatee_id):
    """Get products for a specific incubatee - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = cache_key("incubatee_products", incubatee_id)
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
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
        
        response_data = {"success": True, "products": products_list}
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Optional: API endpoint for checking login status
@admin_bp.route("/check-auth")
def check_auth():
    """Check if admin is authenticated (for AJAX calls)"""
    return jsonify({'authenticated': session.get('admin_logged_in', False),'username': session.get('admin_username', None)})
    
@admin_bp.route("/add-pricing-unit", methods=["POST"])
def add_pricing_unit():
    """Add a new pricing unit - INVALIDATES CACHE"""
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
        
        # Invalidate pricing units cache
        invalidate_cache("pricing_units:*")
        
        return jsonify({"success": True, "message": "Pricing unit added successfully!","unit_id": pricing_unit.unit_id,"existing": False})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding pricing unit: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
        
@admin_bp.route("/search-pricing-units", methods=["GET"])
def search_pricing_units():
    """Search pricing units by name or description - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    query = request.args.get('q', '').strip().lower()
    cache_key_str = cache_key("pricing_units:search", query)
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        if not query:
            pricing_units = PricingUnit.query.filter_by(is_active=True).all()
        else:
            pricing_units = PricingUnit.query.filter(
                PricingUnit.is_active == True,
                db.or_(PricingUnit.unit_name.ilike(f'%{query}%'),PricingUnit.unit_description.ilike(f'%{query}%'))).all()
        
        response_data = {"success": True,"pricing_units": [{"unit_id": unit.unit_id,"unit_name": unit.unit_name,"unit_description": unit.unit_description} for unit in pricing_units]}
        
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Update the add_product route to include pricing_unit_id
@admin_bp.route("/add-product", methods=["POST"])
def add_product():
    """Add product - INVALIDATES CACHE"""
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

        # Handle multiple image uploads
        image_paths = []
        image_files = request.files.getlist("product_images")
        for idx, image in enumerate(image_files):
            if image and allowed_file(image.filename):
                # Generate unique filename
                file_extension = image.filename.rsplit('.', 1)[1].lower()
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"product_{timestamp}_{idx}.{file_extension}"
                filename = secure_filename(filename)
                
                save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                image.save(save_path)
                image_paths.append(f"{UPLOAD_FOLDER}/{filename}")

        # Create product entry
        product = IncubateeProduct(incubatee_id=incubatee_id,name=name,stock_no=stock_no,products=products,
            stock_amount=stock_amount,price_per_stocks=price_per_stocks,new_price_per_stocks=price_per_stocks,pricing_unit_id=pricing_unit_id, 
            details=details,category=category,expiration_date=expiration_date,warranty=warranty,added_on=added_on,
            image_path=','.join(image_paths) if image_paths else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow())

        db.session.add(product)
        db.session.commit()

        # Invalidate relevant caches
        invalidate_cache(f"incubatee_products:{incubatee_id}")
        invalidate_cache("products:all")
        invalidate_cache(f"incubatee_details:{incubatee_id}")

        return jsonify({"success": True, "message": "✅ Product saved successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in add_product: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/delete-product/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    """Delete product - INVALIDATES CACHE"""
    try:
        product = IncubateeProduct.query.get_or_404(product_id)
        incubatee_id = product.incubatee_id
        
        # Delete related records first
        # 1. Delete from product_popularity
        popularity_records = ProductPopularity.query.filter_by(product_id=product_id).all()
        for record in popularity_records:
            db.session.delete(record)
        
        # 2. Delete from product_sales_log
        sales_logs = ProductSalesLog.query.filter_by(product_id=product_id).all()
        for log in sales_logs:
            db.session.delete(log)
        
        # 3. Delete from sales_reports
        sales_reports = SalesReport.query.filter_by(product_id=product_id).all()
        for report in sales_reports:
            db.session.delete(report)
        
        # 4. Delete image if exists
        if product.image_path:
            try:
                image_path = os.path.join(current_app.root_path, product.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                current_app.logger.warning(f"Image delete failed: {e}")
        
        # 5. Delete the product itself
        db.session.delete(product)
        db.session.commit()
        
        # Invalidate relevant caches
        invalidate_cache(f"incubatee_products:{incubatee_id}")
        invalidate_cache("products:all")
        invalidate_cache(f"incubatee_details:{incubatee_id}")
        invalidate_cache(f"product:{product_id}")
        
        return jsonify({"success": True, "message": "🗑️ Product deleted successfully"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting product: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-products", methods=["GET"])
def get_products():
    """Get all products for display in admin panel - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = "products:all"
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        # Get all products with incubatee information
        products = IncubateeProduct.query.options(
            db.joinedload(IncubateeProduct.incubatee),
            db.joinedload(IncubateeProduct.pricing_unit)
        ).all()
        
        products_list = []
        for product in products:
            # Use new_price_per_stocks if available, otherwise use price_per_stocks
            display_price = float(product.new_price_per_stocks) if product.new_price_per_stocks else float(product.price_per_stocks)
            
            products_list.append({
                "product_id": product.product_id,
                "incubatee_id": product.incubatee_id,
                "name": product.name,
                "stock_no": product.stock_no,
                "products": product.products,
                "stock_amount": product.stock_amount,
                "price_per_stocks": float(product.price_per_stocks),  # Original price
                "new_price_per_stocks": float(product.new_price_per_stocks) if product.new_price_per_stocks else None,  # New price
                "display_price": display_price,  # Price to display (uses new price if available)
                "pricing_unit": product.pricing_unit.unit_name if product.pricing_unit else "N/A",
                "pricing_unit_id": product.pricing_unit_id,
                "details": product.details,
                "category": product.category,
                "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else "N/A",
                "warranty": product.warranty,
                "added_on": product.added_on.strftime("%Y-%m-%d") if product.added_on else "N/A",
                "image_path": product.image_path,
                "image_paths": product.image_path.split(',') if product.image_path else [],
                "incubatee_name": f"{product.incubatee.first_name} {product.incubatee.last_name}" if product.incubatee else "Unknown"
            })
        
        response_data = {"success": True, "products": products_list}
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching products: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-pricing-units", methods=["GET"])
def get_pricing_units():
    """Get all pricing units - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = "pricing_units:all"
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        pricing_units = PricingUnit.query.filter_by(is_active=True).all()
        
        response_data = {
            "success": True,
            "pricing_units": [
                {
                    "unit_id": unit.unit_id,
                    "unit_name": unit.unit_name,
                    "unit_description": unit.unit_description
                } for unit in pricing_units
            ]
        }
        
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/add-incubatee", methods=["POST"])
def add_incubatee():
    """Add a new incubatee (person/company) - INVALIDATES CACHE"""
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
                    return jsonify({"success": False, "error": f"Invalid file type. Allowed types: {', '.join(LOGO_ALLOWED_EXTENSIONS)}"}), 400
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
        incubatee = Incubatee(last_name=last_name,first_name=first_name,
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

        # Invalidate incubatees cache
        invalidate_cache("incubatees:*")
        invalidate_cache("incubatees_list:all")

        return jsonify({"success": True, "message": "Incubatee added successfully!","incubatee_id": incubatee.incubatee_id})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding incubatee: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-incubatees", methods=["GET"])
def get_incubatees():
    """Return incubatees for dropdown selection - WITH CACHING"""
    cache_key_str = "incubatees:all"
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=3600)  # 1 hour cache
    if found:
        return jsonify(cached_data)
    
    try:
        incubatees = Incubatee.query.order_by(Incubatee.last_name.asc()).all()
        response_data = {
            "success": True,
            "incubatees": [{
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
                } for i in incubatees]}
        
        set_cached_data(cache_key_str, response_data, 3600)  # Cache for 1 hour
        return jsonify(response_data)
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
    """Update admin profile - INVALIDATES CACHE"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        username = session.get('admin_username')
        
        admin_profile = AdminProfile.query.filter_by(username=username).first()
        if not admin_profile:
            # Create new profile if doesn't exist
            admin_profile = AdminProfile(username=username,full_name=data.get('full_name'),email=data.get('email'),phone=data.get('phone'))
            db.session.add(admin_profile)
        else:
            admin_profile.full_name = data.get('full_name')
            admin_profile.email = data.get('email')
            admin_profile.phone = data.get('phone')
        
        db.session.commit()
        
        # Invalidate admin profile cache if you cache it
        invalidate_cache(f"admin_profile:{username}")
        
        return jsonify({"success": True, "message": "Profile updated successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/get-users")
def get_users():
    """Get all users with their status - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = "users:all"
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=900)  # 15 minutes cache
    if found:
        return jsonify(cached_data)
    
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
        
        response_data = {"success": True, "users": users_list}
        set_cached_data(cache_key_str, response_data, 900)  # Cache for 15 minutes
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/get-incubatees-list")
def get_incubatees_list():
    """Get all incubatees for management - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = "incubatees_list:all"
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        incubatees = Incubatee.query.all()
        incubatees_list = []
        
        for incubatee in incubatees:
            # Count products for this incubatee
            product_count = IncubateeProduct.query.filter_by(incubatee_id=incubatee.incubatee_id).count()
            
            # Calculate total sales from sales reports
            total_sales_result = db.session.query(func.coalesce(func.sum(SalesReport.total_price), 0)).filter(SalesReport.incubatee_id == incubatee.incubatee_id).scalar()
            total_sales = float(total_sales_result) if total_sales_result else 0.0
            
            incubatees_list.append({"incubatee_id": incubatee.incubatee_id,
                "full_name": f"{incubatee.first_name} {incubatee.last_name}",
                "company_name": incubatee.company_name or "No Company",
                "website": incubatee.website,"logo_url": incubatee.logo_url,"email": incubatee.email or "No email","phone": incubatee.phone_number or "No phone",
                "batch": incubatee.batch,"product_count": product_count,"total_sales": total_sales,
                "is_approved": incubatee.is_approved if hasattr(incubatee, 'is_approved') else False,
                "created_at": incubatee.created_at.strftime("%Y-%m-%d") if incubatee.created_at else "Unknown"})
        
        response_data = {"success": True, "incubatees": incubatees_list}
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in get_incubatees_list: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to load incubatees: {str(e)}"}), 500
    
@admin_bp.route("/toggle-incubatee-approval/<int:incubatee_id>", methods=["POST"])
def toggle_incubatee_approval(incubatee_id):
    """Approve or disapprove an incubatee - INVALIDATES CACHE"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        incubatee = Incubatee.query.get_or_404(incubatee_id)
        incubatee.is_approved = not incubatee.is_approved
        db.session.commit()
        
        # Invalidate incubatee caches
        invalidate_cache(f"incubatee_details:{incubatee_id}")
        invalidate_cache("incubatees_list:all")
        invalidate_cache("incubatees:all")
        
        action = "approved" if incubatee.is_approved else "disapproved"
        return jsonify({"success": True, "message": f"Incubatee {action} successfully!"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    

@admin_bp.route("/get-product/<int:product_id>")
def get_product(product_id):
    """Get product data for editing - WITH CACHING"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    cache_key_str = cache_key("product", product_id)
    
    # Try cache first
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)  # 30 minutes cache
    if found:
        return jsonify(cached_data)
    
    try:
        product = IncubateeProduct.query.options(
            db.joinedload(IncubateeProduct.incubatee),
            db.joinedload(IncubateeProduct.pricing_unit)
        ).get(product_id)
        
        if not product:
            return jsonify({"success": False, "error": f"Product with ID {product_id} not found"}), 404
        
        # Handle multiple image paths
        image_paths = []
        if product.image_path:
            image_paths = [path.strip() for path in product.image_path.split(',')]
        
        # Use new_price_per_stocks for display in edit form if it exists
        display_price = float(product.new_price_per_stocks) if product.new_price_per_stocks else float(product.price_per_stocks)
        
        product_data = {
            "product_id": product.product_id,
            "name": product.name,
            "stock_no": product.stock_no,
            "products": product.products,
            "stock_amount": product.stock_amount,
            "price_per_stocks": float(product.price_per_stocks),  # Original price
            "new_price_per_stocks": float(product.new_price_per_stocks) if product.new_price_per_stocks else None,  # New price
            "display_price": display_price,  # Price to show in edit form
            "pricing_unit_id": product.pricing_unit_id,
            "details": product.details,
            "category": product.category,
            "expiration_date": product.expiration_date.strftime("%Y-%m-%d") if product.expiration_date else None,
            "warranty": product.warranty,
            "image_path": product.image_path,
            "image_paths": image_paths,
            "incubatee_name": f"{product.incubatee.first_name} {product.incubatee.last_name}" if product.incubatee else "Unknown"
        }
        
        set_cached_data(cache_key_str, product_data, 1800)  # Cache for 30 minutes
        return jsonify({"success": True, "product": product_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching product {product_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route("/update-product/<int:product_id>", methods=["POST"])
def update_product(product_id):
    """Update product information - Invalidates cache"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # First, get the product
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
                current_display_price = float(product.new_price_per_stocks) if product.new_price_per_stocks else float(product.price_per_stocks)
                
                if new_price != current_display_price:
                    # ONLY update new_price_per_stocks (NOT price_per_stocks)
                    product.new_price_per_stocks = new_price
                    updated_fields.append('new_price_per_stocks')
                    
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
                        # Handle multiple images
                        old_image_paths = product.image_path.split(',')
                        for old_path in old_image_paths:
                            old_path = old_path.strip()
                            if old_path:
                                old_full_path = os.path.join(current_app.root_path, old_path)
                                if os.path.exists(old_full_path):
                                    os.remove(old_full_path)
                    except Exception as e:
                        current_app.logger.warning(f"Failed to delete old product image: {str(e)}")
                
                product.image_path = f"{UPLOAD_FOLDER}/{filename}"
                updated_fields.append('image_path')
        
        # Handle multiple image uploads
        if 'product_images' in request.files:
            image_files = request.files.getlist('product_images')
            new_image_paths = []
            
            for idx, image_file in enumerate(image_files):
                if image_file and image_file.filename and allowed_file(image_file.filename):
                    # Generate secure filename
                    file_extension = image_file.filename.rsplit('.', 1)[1].lower()
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    filename = f"product_{product_id}_{timestamp}_{idx}.{file_extension}"
                    filename = secure_filename(filename)
                    
                    # Save the new image
                    save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    image_file.save(save_path)
                    new_image_paths.append(f"{UPLOAD_FOLDER}/{filename}")
            
            if new_image_paths:
                # Delete old images if exist
                if product.image_path:
                    try:
                        old_image_paths = product.image_path.split(',')
                        for old_path in old_image_paths:
                            old_path = old_path.strip()
                            if old_path:
                                old_full_path = os.path.join(current_app.root_path, old_path)
                                if os.path.exists(old_full_path):
                                    os.remove(old_full_path)
                    except Exception as e:
                        current_app.logger.warning(f"Failed to delete old product images: {str(e)}")
                
                product.image_path = ','.join(new_image_paths)
                updated_fields.append('image_path')
        
        # Only update timestamp and commit if there are actual changes
        if updated_fields:
            product.updated_at = datetime.utcnow()
            db.session.commit()
            try:
                popularity_record = ProductPopularity.query.filter_by(product_id=product_id).first()
                if popularity_record:
                    # Update the popularity record with new product data if needed
                    popularity_record.product_name = product.name  # Add this field if it doesn't exist
                    popularity_record.incubatee_id = product.incubatee_id
                    popularity_record.last_updated = datetime.utcnow()
            except Exception as e:
                current_app.logger.warning(f"Could not update product_popularity: {str(e)}")
            
            # Invalidate relevant caches
            invalidate_cache(f"product:{product_id}")
            invalidate_cache(f"incubatee_products:{product.incubatee_id}")
            invalidate_cache("products:all")
            invalidate_cache(f"incubatee_details:{product.incubatee_id}")
            
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
    
@admin_bp.route("/debug-env")
def debug_env():
    """Debug environment variables"""
    import os
    
    redis_url = os.environ.get('redis_url')
    all_env_vars = dict(os.environ)
    
    # Hide sensitive values in output
    safe_vars = {}
    for key, value in all_env_vars.items():
        if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower() or 'url' in key.lower():
            safe_vars[key] = '***HIDDEN***'
        else:
            safe_vars[key] = value
    
    return jsonify({
        "redis_url_exists": bool(redis_url),
        "redis_url_length": len(redis_url) if redis_url else 0,
        "redis_url_preview": redis_url[:20] + "..." if redis_url and len(redis_url) > 20 else redis_url if redis_url else None,
        "all_env_vars": safe_vars
    })
@admin_bp.route("/test-redis")
def test_redis():
    """Test Redis connection"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.ping()
            return jsonify({"success": True, "message": "✅ Redis is connected and working!"})
        else:
            # Check if environment variable exists
            redis_url = os.environ.get('redis_url')
            if not redis_url:
                return jsonify({"success": False, "message": "❌ redis_url environment variable not found"})
            else:
                return jsonify({"success": False, "message": "❌ Redis connection failed - check your redis_url value"})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Redis error: {str(e)}"})
    
def should_send_notification(product_id):
    """Check if we should send notification (cooldown period)"""
    global last_notification_time
    
    cooldown_hours = current_app.config.get('NOTIFICATION_COOLDOWN_HOURS', 24)
    
    if product_id in last_notification_time:
        last_time = last_notification_time[product_id]
        hours_passed = (datetime.utcnow() - last_time).total_seconds() / 3600
        
        if hours_passed < cooldown_hours:
            return False
    
    return True

def record_notification_sent(product_id):
    """Record that a notification was sent - with cleanup"""
    global last_notification_time
    
    # Clean up old entries (older than 24 hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    keys_to_delete = []
    for pid, timestamp in last_notification_time.items():
        if timestamp < cutoff_time:
            keys_to_delete.append(pid)
    
    for pid in keys_to_delete:
        del last_notification_time[pid]
    
    # Record new notification
    last_notification_time[product_id] = datetime.utcnow()
    
@admin_bp.route("/check-low-stock", methods=["GET"])
def check_low_stock():
    """Simple low stock check - OPTIMIZED for speed"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Use simple SELECT with LIMIT for faster response
        low_stock_threshold = current_app.config.get('LOW_STOCK_THRESHOLD', 10)
        
        # OPTIMIZED QUERY: Only fetch essential fields
        low_stock_products = db.session.query(
            IncubateeProduct.product_id,
            IncubateeProduct.name,
            IncubateeProduct.stock_no,
            IncubateeProduct.stock_amount,
            Incubatee.email,
            Incubatee.first_name,
            Incubatee.last_name
        ).join(
            Incubatee, IncubateeProduct.incubatee_id == Incubatee.incubatee_id
        ).filter(
            IncubateeProduct.stock_amount <= low_stock_threshold
        ).limit(50).all()  # LIMIT to prevent huge queries
        
        products_list = []
        for product in low_stock_products:
            products_list.append({
                "product_id": product.product_id,
                "product_name": product.name,
                "stock_no": product.stock_no,
                "current_stock": product.stock_amount,
                "threshold": low_stock_threshold,
                "incubatee_name": f"{product.first_name} {product.last_name}" if product.first_name and product.last_name else "Unknown",
                "incubatee_email": product.email,
                "status": "Critical" if product.stock_amount <= 3 else "Low"
            })
        
        return jsonify({
            "success": True,
            "low_stock_threshold": low_stock_threshold,
            "total_low_stock": len(products_list),
            "products": products_list,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error checking low stock: {str(e)}")
        # Return minimal error response
        return jsonify({
            "success": False, 
            "error": "Server error",
            "message": "Unable to check low stock at this time"
        }), 500

@admin_bp.route("/check-overdue", methods=["POST"])
def check_overdue():
    """Check for overdue reservations - OPTIMIZED"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = request.get_json() or {}
        timeout_ms = data.get('timeout_ms', 3 * 24 * 60 * 60 * 1000)  # Default 3 days
        
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(milliseconds=timeout_ms)
        
        # OPTIMIZED QUERY: Only get IDs that need processing
        overdue_reservations = Reservation.query.with_entities(
            Reservation.reservation_id
        ).filter(
            Reservation.status == 'approved',
            Reservation.reserved_at <= cutoff_time
        ).limit(100).all()  # Process max 100 at a time
        
        reservation_ids = [r.reservation_id for r in overdue_reservations]
        rejected_count = 0
        
        if reservation_ids:
            # Update in batches for better performance
            batch_size = 50
            for i in range(0, len(reservation_ids), batch_size):
                batch = reservation_ids[i:i + batch_size]
                updated = Reservation.query.filter(
                    Reservation.reservation_id.in_(batch)
                ).update({
                    'status': 'rejected',
                    'rejected_reason': 'Not picked up on time (auto-rejected)',
                    'updated_at': datetime.utcnow()
                }, synchronize_session=False)
                
                db.session.commit()
                rejected_count += updated
        
        return jsonify({
            "success": True,
            "rejected_count": rejected_count,
            "message": f"Auto-rejected {rejected_count} overdue reservations"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error checking overdue: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Server error",
            "message": "Unable to process overdue reservations"
        }), 500

@admin_bp.route("/send-low-stock-notifications", methods=["POST"])
def send_low_stock_notifications():
    """Send email notifications to incubatees for low stock - ALL LOGIC HERE"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # 1. Get low stock threshold
        low_stock_threshold = current_app.config.get('LOW_STOCK_THRESHOLD', 10)
        
        # 2. QUERY: Get products with low stock AND their incubatee emails
        low_stock_products = IncubateeProduct.query.filter(
            IncubateeProduct.stock_amount <= low_stock_threshold
        ).options(
            db.joinedload(IncubateeProduct.incubatee)
        ).all()
        
        # 3. Send emails to incubatees
        notifications_sent = 0
        failed_notifications = 0
        sent_emails = []
        
        for product in low_stock_products:
            # Check if incubatee has email
            if product.incubatee and product.incubatee.email:
                # Send email (all email logic is here)
                email_sent = send_low_stock_email_to_incubatee({
                    'product_id': product.product_id,
                    'product_name': product.name,
                    'stock_no': product.stock_no,
                    'current_stock': product.stock_amount,
                    'threshold': low_stock_threshold,
                    'incubatee_name': f"{product.incubatee.first_name} {product.incubatee.last_name}",
                    'incubatee_email': product.incubatee.email,
                    'status': "Critical" if product.stock_amount <= 3 else "Low"
                })
                
                if email_sent:
                    notifications_sent += 1
                    sent_emails.append({
                        "incubatee": f"{product.incubatee.first_name} {product.incubatee.last_name}",
                        "email": product.incubatee.email,
                        "product": product.name
                    })
                else:
                    failed_notifications += 1
        
        return jsonify({
            "success": True,
            "message": f"Sent {notifications_sent} email notifications",
            "notifications_sent": notifications_sent,
            "failed_notifications": failed_notifications,
            "total_low_stock": len(low_stock_products),
            "sent_emails": sent_emails
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending low stock notifications: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
def send_low_stock_email_to_incubatee(product_data):
    """Send email to incubatee about low stock"""
    try:
        # Check if email is configured
        if not current_app.config.get('SMTP_USERNAME') or not current_app.config.get('SMTP_PASSWORD'):
            current_app.logger.warning("Email not configured - skipping email send")
            return False
        
        # Create email content
        subject = f"⚠️ Low Stock Alert: {product_data['product_name']}"
        
        # Determine severity
        severity = "CRITICAL" if product_data['current_stock'] <= 3 else "LOW"
        severity_color = "#dc3545" if product_data['current_stock'] <= 3 else "#f0ad4e"
        action_required = "RESTOCK IMMEDIATELY" if product_data['current_stock'] <= 3 else "Consider restocking soon"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: {severity_color};
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    padding: 30px;
                }}
                .product-info {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid {severity_color};
                    margin: 20px 0;
                }}
                .alert-box {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                    border-top: 1px solid #eee;
                    margin-top: 30px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 5px 10px;
                    background-color: {severity_color};
                    color: white;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    background-color: {severity_color};
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ ATBI Low Stock Alert</h1>
                    <p>Automated Stock Monitoring System</p>
                </div>
                
                <div class="content">
                    <h2>Hello {product_data['incubatee_name']},</h2>
                    
                    <p>Your product is running low on stock and requires your attention.</p>
                    
                    <div class="product-info">
                        <h3>Product Details</h3>
                        <table>
                            <tr>
                                <th>Product Name:</th>
                                <td><strong>{product_data['product_name']}</strong></td>
                            </tr>
                            <tr>
                                <th>Stock Number:</th>
                                <td>{product_data['stock_no']}</td>
                            </tr>
                            <tr>
                                <th>Current Stock Level:</th>
                                <td><span class="status-badge">{product_data['current_stock']} units</span></td>
                            </tr>
                            <tr>
                                <th>Low Stock Threshold:</th>
                                <td>{product_data['threshold']} units</td>
                            </tr>
                            <tr>
                                <th>Stock Status:</th>
                                <td><span class="status-badge">{severity} STOCK</span></td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="alert-box">
                        <h3>⚠️ Action Required</h3>
                        <p><strong>{action_required}</strong></p>
                        <p>To avoid running out of stock, please plan to restock this product as soon as possible.</p>
                    </div>
                    
                    <p>You can log in to your account to update your stock levels or contact ATBI administration for assistance.</p>
                    
                    <p>Thank you for being part of the ATBI incubator program!</p>
                    
                    <p>Best regards,<br>
                    <strong>ATBI Administration Team</strong></p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from the ATBI Stock Monitoring System.</p>
                    <p>Please do not reply to this email. For assistance, contact ATBI administration.</p>
                    <p>© {datetime.utcnow().year} ATBI Incubator Program</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_content = f"""
        ATBI LOW STOCK ALERT
        ====================
        
        Hello {product_data['incubatee_name']},
        
        Your product is running low on stock and requires your attention.
        
        PRODUCT DETAILS:
        - Product Name: {product_data['product_name']}
        - Stock Number: {product_data['stock_no']}
        - Current Stock: {product_data['current_stock']} units
        - Low Stock Threshold: {product_data['threshold']} units
        - Status: {severity} STOCK
        
        ⚠️ ACTION REQUIRED: {action_required}
        
        To avoid running out of stock, please plan to restock this product as soon as possible.
        
        You can log in to your account to update your stock levels or contact ATBI administration for assistance.
        
        Thank you for being part of the ATBI incubator program!
        
        Best regards,
        ATBI Administration Team
        
        ---
        This is an automated message from the ATBI Stock Monitoring System.
        Please do not reply to this email.
        """
        
        # Send email using Flask-Mail or your email sending method
        from app.utils.email_sender import EmailSender
        
        email_data = {
            'to_email': product_data['incubatee_email'],
            'subject': subject,
            'html_content': html_content,
            'text_content': text_content,
            'product_name': product_data['product_name'],
            'current_stock': product_data['current_stock'],
            'threshold': product_data['threshold'],
            'incubatee_name': product_data['incubatee_name']
        }
        
        # Try to send email
        success = EmailSender.send_email(
            to_email=email_data['to_email'],
            subject=email_data['subject'],
            html_content=email_data['html_content'],
            text_content=email_data['text_content']
        )
        
        if success:
            current_app.logger.info(f"✅ Low stock email sent to {product_data['incubatee_email']} for product {product_data['product_name']}")
        else:
            current_app.logger.error(f"❌ Failed to send email to {product_data['incubatee_email']}")
        
        return success
        
    except Exception as e:
        current_app.logger.error(f"Error sending email to incubatee: {str(e)}")
        return False

def send_admin_summary_email(sent_emails, total_low_stock):
    """Send summary email to admin"""
    try:
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if not admin_email:
            return False
        
        from app.utils.email_sender import EmailSender
        
        subject = f"📊 Low Stock Notification Summary - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        # Group by incubatee
        incubatee_summary = {}
        for email in sent_emails:
            incubatee_name = email['incubatee']
            if incubatee_name not in incubatee_summary:
                incubatee_summary[incubatee_name] = {
                    'email': email['email'],
                    'products': []
                }
            incubatee_summary[incubatee_name]['products'].append(email['product'])
        
        # Create HTML content
        summary_html = ""
        for incubatee, data in incubatee_summary.items():
            products_list = "<br>".join([f"• {p}" for p in data['products']])
            summary_html += f"""
            <tr>
                <td>{incubatee}</td>
                <td>{data['email']}</td>
                <td>{len(data['products'])}</td>
                <td>{products_list}</td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 700px; margin: 0 auto; }}
                .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                .summary {{ padding: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #f8f9fa; padding: 10px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #eee; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Low Stock Notification Summary</h1>
                    <p>{datetime.utcnow().strftime('%B %d, %Y %H:%M')}</p>
                </div>
                
                <div class="summary">
                    <p><strong>Total Low Stock Products:</strong> {total_low_stock}</p>
                    <p><strong>Notifications Sent:</strong> {len(sent_emails)}</p>
                    <p><strong>Incubatees Notified:</strong> {len(incubatee_summary)}</p>
                    
                    <h3>Notification Details:</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Incubatee</th>
                                <th>Email</th>
                                <th>Products</th>
                                <th>Product Names</th>
                            </tr>
                        </thead>
                        <tbody>
                            {summary_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email
        success = EmailSender.send_email(
            to_email=admin_email,
            subject=subject,
            html_content=html_content,
            text_content=f"Low stock notifications sent to {len(sent_emails)} incubatees."
        )
        
        return success
        
    except Exception as e:
        current_app.logger.error(f"Error sending admin summary: {str(e)}")
        return False