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

redis_client = None
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
            stock_amount=stock_amount,price_per_stocks=price_per_stocks,pricing_unit_id=pricing_unit_id, 
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
        ).get(product_id)  # Use get() instead of get_or_404() for better error handling
        
        if not product:
            return jsonify({"success": False, "error": f"Product with ID {product_id} not found"}), 404
        
        # Handle multiple image paths
        image_paths = []
        if product.image_path:
            image_paths = [path.strip() for path in product.image_path.split(',')]
        
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
            "image_paths": image_paths,  # New: array of image paths
            "incubatee_name": f"{product.incubatee.first_name} {product.incubatee.last_name}" if product.incubatee else "Unknown"
        }
        
        set_cached_data(cache_key_str, product_data, 1800)  # Cache for 30 minutes
        return jsonify({"success": True, "product": product_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching product {product_id}: {str(e)}")
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
    
@admin_bp.route("/sales-summary")
def sales_summary():
    """Get sales summary for reports - FIXED for User model without names"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'overview')
        
        # Create cache key based on parameters
        cache_key_str = cache_key("sales_summary", start_date, end_date, report_type)
        
        # Try cache first (shorter cache for reports - 5 minutes)
        cached_data, found = get_cached_data(cache_key_str, expire_seconds=300)
        if found:
            return jsonify(cached_data)
        
        # Base query for sales data
        sales_query = SalesReport.query
        
        # Apply date filter if provided
        start_date_obj = None
        end_date_obj = None
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                sales_query = sales_query.filter(SalesReport.sale_date >= start_date_obj,SalesReport.sale_date <= end_date_obj)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format"}), 400
        
        # Get sales data with related information
        sales_data = sales_query.options(db.joinedload(SalesReport.incubatee),
            db.joinedload(SalesReport.product),db.joinedload(SalesReport.user)).all()
        
        # Process sales data
        sales_list = []
        for sale in sales_data:
            # Get customer name from username (since User model only has username)
            customer_name = "Unknown"
            if sale.user:
                customer_name = sale.user.username
            
            # Get incubatee name
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            sales_list.append({
                "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
                "reservation_id": sale.reservation_id,
                "incubatee_name": incubatee_name,"product_name": sale.product_name,"customer_name": customer_name,
                "quantity": sale.quantity,
                "unit_price": float(sale.unit_price) if sale.unit_price else 0,
                "total_price": float(sale.total_price) if sale.total_price else 0,
                "status": "completed"  # Sales reports are typically for completed sales
            })
        
        # Calculate summary statistics
        total_revenue = sum(float(sale.total_price) for sale in sales_data if sale.total_price)
        total_orders = len(sales_data)
        completed_orders = len(sales_data)  # All sales reports are completed orders
        completion_rate = 100.0 if total_orders > 0 else 0
        
        # Get unique incubatees
        incubatee_ids = set()
        for sale in sales_data:
            if sale.incubatee_id:
                incubatee_ids.add(sale.incubatee_id)
            elif sale.product and sale.product.incubatee_id:
                incubatee_ids.add(sale.product.incubatee_id)
        
        active_incubatees = len(incubatee_ids)
        
        # Incubatee performance data
        incubatee_performance = []
        incubatee_sales = {}
        
        # Group sales by incubatee
        for sale in sales_data:
            incubatee_id = None
            incubatee_name = "Unknown"
            
            if sale.incubatee:
                incubatee_id = sale.incubatee_id
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_id = sale.product.incubatee_id
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            if incubatee_id not in incubatee_sales:
                incubatee_sales[incubatee_id] = {
                    'name': incubatee_name,
                    'revenue': 0,
                    'order_count': 0,'product_count': 0,'completed_orders': 0,'products': set()}
            
            incubatee_sales[incubatee_id]['revenue'] += float(sale.total_price) if sale.total_price else 0
            incubatee_sales[incubatee_id]['order_count'] += 1
            incubatee_sales[incubatee_id]['products'].add(sale.product_name)
            incubatee_sales[incubatee_id]['completed_orders'] += 1
        
        # Format incubatee performance data
        for incubatee_id, data in incubatee_sales.items():
            incubatee_performance.append({
                'name': data['name'],
                'revenue': data['revenue'],
                'order_count': data['order_count'],
                'product_count': len(data['products']),
                'completion_rate': (data['completed_orders'] / data['order_count'] * 100) if data['order_count'] > 0 else 0,
                'top_product': next(iter(data['products'])) if data['products'] else 'N/A'
            })
        
        # Sort incubatees by revenue
        incubatee_performance.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Chart data - Revenue trend by date
        revenue_trend_labels = []
        revenue_trend_data = []
        
        if start_date and end_date and sales_data:
            try:
                # Group sales by date
                date_sales = {}
                for sale in sales_data:
                    sale_date = sale.sale_date.isoformat() if sale.sale_date else datetime.utcnow().date().isoformat()
                    if sale_date not in date_sales:
                        date_sales[sale_date] = 0
                    date_sales[sale_date] += float(sale.total_price) if sale.total_price else 0
                
                # Convert to sorted lists
                sorted_dates = sorted(date_sales.keys())
                revenue_trend_labels = [date[5:] for date in sorted_dates]  # Show MM-DD format
                revenue_trend_data = [date_sales[date] for date in sorted_dates]
                
            except Exception as e:
                current_app.logger.error(f"Error processing revenue trend: {str(e)}")
                revenue_trend_labels = ['Total']
                revenue_trend_data = [total_revenue]
        else:
            revenue_trend_labels = ['Total']
            revenue_trend_data = [total_revenue]
        
        # Category sales - get from products
        category_sales = {}
        for sale in sales_data:
            category = "Uncategorized"
            if sale.product and sale.product.category:
                category = sale.product.category
            elif sale.product_name:
                # Try to infer category from product name
                product_lower = sale.product_name.lower()
                if any(keyword in product_lower for keyword in ['agriculture', 'aqua', 'crop', 'farm', 'fish', 'seed']):
                    category = "Agri-Aqua Business"
                elif any(keyword in product_lower for keyword in ['food', 'processing', 'recipe', 'cook', 'bake']):
                    category = "Food Processing Technology"
            
            if category not in category_sales:
                category_sales[category] = 0
            category_sales[category] += float(sale.total_price) if sale.total_price else 0
        
        category_sales_labels = list(category_sales.keys())
        category_sales_data = list(category_sales.values())
        
        # Top incubatees for chart (limit to 5)
        top_incubatees_labels = [inc['name'] for inc in incubatee_performance[:5]]
        top_incubatees_data = [inc['revenue'] for inc in incubatee_performance[:5]]
        
        # Status distribution (all completed for sales reports)
        status_labels = ['Completed']
        status_data = [total_orders]
        
        response_data = {
            "success": True,
            "summary": {
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "completion_rate": completion_rate,
                "active_incubatees": active_incubatees
            },
            "sales_data": sales_list,
            "incubatee_performance": incubatee_performance,
            "charts": {
                "revenue_trend": {
                    "labels": revenue_trend_labels,
                    "data": revenue_trend_data
                },
                "category_sales": {
                    "labels": category_sales_labels,
                    "data": category_sales_data
                },
                "top_incubatees": {
                    "labels": top_incubatees_labels,
                    "data": top_incubatees_data
                },
                "status_distribution": {
                    "labels": status_labels,
                    "data": status_data
                }
            }
        }
        #set cache for the response
        set_cached_data(cache_key_str, response_data, 300) # cache for 5 minutes
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in sales_summary: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@admin_bp.route("/export-report")
def export_report():
    """Export sales report to CSV - FIXED variable name"""
    if not session.get('admin_logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        report_type = request.args.get('type', 'overview')
        
        # Get sales data (similar to sales_summary)
        sales_query = SalesReport.query.options(
            db.joinedload(SalesReport.incubatee),
            db.joinedload(SalesReport.product),
            db.joinedload(SalesReport.user)
        )
        
        if start_date and end_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            sales_query = sales_query.filter(
                SalesReport.sale_date >= start_date_obj,
                SalesReport.sale_date <= end_date_obj
            )
        
        sales_data = sales_query.all()
        
        import csv
        from io import StringIO
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Order ID', 'Incubatee', 'Product', 'Customer', 'Quantity', 'Unit Price', 'Total', 'Status'])
        
        for sale in sales_data:
            # Get customer name from username
            customer_name = "Unknown"
            if sale.user:
                customer_name = sale.user.username
            
            # Get incubatee name
            incubatee_name = "Unknown"
            if sale.incubatee:
                incubatee_name = f"{sale.incubatee.first_name} {sale.incubatee.last_name}"
            elif sale.product and sale.product.incubatee:
                incubatee_name = f"{sale.product.incubatee.first_name} {sale.product.incubatee.last_name}"
            
            writer.writerow([
                sale.sale_date.isoformat() if sale.sale_date else '',
                sale.reservation_id,
                incubatee_name,
                sale.product_name,
                customer_name,
                sale.quantity,
                float(sale.unit_price) if sale.unit_price else 0,
                float(sale.total_price) if sale.total_price else 0,
                'completed'
            ])
        
        # Return CSV file - FIXED: Changed endDate to end_date
        from flask import Response
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=incubatee-report-{start_date}-to-{end_date}.csv"}
        )
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting report: {str(e)}")
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
            
            # Invalidate relevant caches
            invalidate_cache(f"product:{product_id}")
            invalidate_cache(f"incubatee_products:{product.incubatee_id}")
            invalidate_cache("products:all")
            invalidate_cache(f"incubatee_details:{product.incubatee_id}")
            
            return jsonify({"success": True,"message": f"Product updated successfully! Updated fields: {', '.join(updated_fields)}","updated_fields": updated_fields})
        else:
            return jsonify({"success": True,"message": "No changes detected - product information is up to date","updated_fields": []})
        
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