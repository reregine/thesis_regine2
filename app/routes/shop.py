
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.shop import Shop
from ..models.admin import IncubateeProduct
from ..extension import db
import json, redis, os

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

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
                # fallback to local redis 
                redis_client = redis.Redis(host='localhost', port=6379, db=0,decode_response=True)
        except Exception as e:
            print(f"Redis connection failed: {str(e)}")
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
        print(f"Cache get error for key {key}: {str(e)}")
        return None, False

def set_cached_data(key, data, expire_seconds=3600):
    """Set data in cache with expiration"""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        redis_client.setex(key, expire_seconds, json.dumps(data, default=str))
    except Exception as e:
        print(f"Cache set error for key {key}: {str(e)}")

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
        print(f"Cache invalidation error for pattern {pattern}: {str(e)}")

def get_availability_status(stock_count):
    """Determine availability status based on stock count."""
    if stock_count == 0:
        return "Out of Stock"
    elif 1 <= stock_count <= 5:
        return "Low Stock"
    elif 6 <= stock_count <= 20:
        return "In Stock"
    else:
        return "High Stock"
    
@shop_bp.route("/")
def shop_home():
    return render_template("shop/shop.html")


@shop_bp.route("/search-products", methods=["GET"])
def search_products():
    """Search or list all incubatee products."""
    query = request.args.get("q", "").strip()
    cache_key_str = cache_key("shop_search", query)

    # Try cache first (shorter cache for searches - 5 minutes)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=300)
    if found:
        return jsonify(cached_data)
    try:
        products = Shop.search_products(query)
        result = []
        for p in products:
            result.append({
                "incubatee_id": p.incubatee_id,
                "product_id": p.product_id,
                "name": p.name,
                "products": p.products,
                "category": p.category,
                "details": p.details,
                "price_per_stocks": float(p.price_per_stocks),
                "stock_amount": p.stock_amount,
                "expiration_date": (
                    p.expiration_date.strftime("%Y-%m-%d")
                    if p.expiration_date
                    else "No Expiry"
                ),"warranty": p.warranty,"added_on": p.added_on.strftime("%Y-%m-%d"),"image_path": p.image_path})

        response_data = {"success": True, "products": result}
        set_cached_data(cache_key_str, response_data, 300)  # Cache for 5 minutes
        return jsonify({"success": True, "products": result})

    except Exception as e:
        print("❌ Error fetching products:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/product-availability", methods=["GET"])
def product_availability():
    """Get product stock availability for all products."""
    cache_key_str = "shop_availability:all"
    
    # Try cache first (15 minutes cache for availability data)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=900)
    if found:
        return jsonify(cached_data)
    try:
        products = Shop.get_all_products()
        availability_data = []
        
        for product in products:
            availability_data.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "current_stock": product.stock_amount,
                "availability_status": get_availability_status(product.stock_amount),
                "price_per_stocks": float(product.price_per_stocks),
                "updated_at": product.added_on.strftime("%Y-%m-%d %H:%M:%S")})
        
        response_data = {
                    "success": True, 
                    "products": availability_data,
                    "total_products": len(availability_data),
                    "in_stock_count": len([p for p in availability_data if p['current_stock'] > 0]),
                    "low_stock_count": len([p for p in availability_data if 1 <= p['current_stock'] <= 5]),
                    "out_of_stock_count": len([p for p in availability_data if p['current_stock'] == 0])}
                
        set_cached_data(cache_key_str, response_data, 900)  # Cache for 15 minutes
        return jsonify(response_data)
    
    except Exception as e:
        print("❌ Error fetching product availability:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@shop_bp.route("/product/<int:product_id>/stock", methods=["GET"])
def get_product_stock(product_id):
    """Get stock information for a specific product."""
    cache_key_str = cache_key("shop_product_stock", product_id)
    
    # Try cache first (10 minutes cache for individual product stock)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=600)
    if found:
        return jsonify(cached_data)
    try:
        # Direct query to avoid issues with Shop class methods
        product = db.session.query(IncubateeProduct).filter(IncubateeProduct.product_id == product_id).first()
        
        if not product:
            response_data = {"success": False, "error": "Product not found"}
            set_cached_data(cache_key_str, response_data, 300)  # Cache negative result for 5 minutes
            return jsonify(response_data), 404
        stock_info = {
            "product_id": product.product_id,
            "name": product.name,
            "current_stock": product.stock_amount,
            "availability_status": get_availability_status(product.stock_amount),
            "price": float(product.price_per_stocks),
            "last_updated": product.added_on.strftime("%Y-%m-%d %H:%M:%S")}
        
        response_data = {"success": True, "product": stock_info}
        set_cached_data(cache_key_str, response_data, 600)  # Cache for 10 minutes
        return jsonify(response_data)
    except Exception as e:
        print(f"❌ Error fetching stock for product {product_id}:", e)
        return jsonify({"success": False, "error": str(e)}), 500

@shop_bp.route('/get-products')
def get_products():
    """Get all products with pricing details."""
    cache_key_str = "shop_products:in_stock"
    
    # Try cache first (15 minutes cache for in-stock products)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=900)
    if found:
        return jsonify(cached_data)
    try:
        # Use direct query to ensure consistency
        products = db.session.query(IncubateeProduct).join(IncubateeProduct.incubatee).filter(IncubateeProduct.stock_amount > 0 ).all()
        
        products_data = []
        for product in products:
            product_data = {'product_id': product.product_id,
                'name': product.name,'products': product.products,
                'stock_amount': product.stock_amount,
                'price_per_stocks': float(product.price_per_stocks),
                'pricing_unit': product.pricing_unit.unit_name if product.pricing_unit else 'Item',
                'pricing_description': product.pricing_unit.unit_description if product.pricing_unit else 'Per Item',
                'details': product.details,'category': product.category,
                'expiration_date': product.expiration_date.strftime('%Y-%m-%d') if product.expiration_date else None,
                'warranty': product.warranty,'image_path': product.image_path,
                'added_on': product.added_on.strftime('%Y-%m-%d'),
                'incubatee': {
                    'incubatee_id': product.incubatee.incubatee_id,
                    'company_name': product.incubatee.company_name,
                    'contact_info': product.incubatee.contact_info,
                    'email': product.incubatee.email,
                    'phone_number': product.incubatee.phone_number
                } if product.incubatee else None}
            products_data.append(product_data)
        
        response_data = {'success': True,'products': products_data}
        set_cached_data(cache_key_str, response_data, 900)  # Cache for 15 minutes
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ Error in get_products: {e}")
        return jsonify({'success': False,'message': f'Error fetching products: {str(e)}'}), 500

@shop_bp.route('/get-all-products')
def get_all_products():
    """Get all products including out-of-stock items."""
    cache_key_str = "shop_products:all"
    
    # Try cache first (30 minutes cache for all products)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)
    if found:
        return jsonify(cached_data)
    try:
        products = db.session.query(IncubateeProduct).join(IncubateeProduct.incubatee).all()
        
        products_data = []
        for product in products:
            product_data = {
                'product_id': product.product_id,'name': product.name,
                'products': product.products,'stock_amount': product.stock_amount,
                'price_per_stocks': float(product.price_per_stocks),
                'pricing_unit': product.pricing_unit.unit_name if product.pricing_unit else 'Item',
                'pricing_description': product.pricing_unit.unit_description if product.pricing_unit else 'Per Item',
                'details': product.details,'category': product.category,
                'expiration_date': product.expiration_date.strftime('%Y-%m-%d') if product.expiration_date else None,
                'warranty': product.warranty,'image_path': product.image_path,
                'added_on': product.added_on.strftime('%Y-%m-%d'),
                'incubatee': {
                    'incubatee_id': product.incubatee.incubatee_id,
                    'company_name': product.incubatee.company_name,
                    'contact_info': product.incubatee.contact_info,
                    'email': product.incubatee.email,
                    'phone_number': product.incubatee.phone_number
                } if product.incubatee else None}
            products_data.append(product_data)
        
        response_data = {'success': True,'products': products_data}
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
    
    except Exception as e:
        print(f"❌ Error in get_all_products: {e}")
        return jsonify({'success': False,'message': f'Error fetching products: {str(e)}'}), 500

@shop_bp.route('/debug-pricing')
def debug_pricing():
    """Debug route to check pricing unit data."""
    
    cache_key_str = "shop_debug:pricing"
    
    # Try cache first (1 hour cache for debug data)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=3600)
    if found:
        return jsonify(cached_data)
    try:
        # Get a few products with their pricing units
        products = IncubateeProduct.query.limit(3).all()
        
        debug_data = []
        for product in products:
            debug_data.append({
                'product_id': product.product_id,'name': product.name,
                'pricing_unit_id': product.pricing_unit_id,
                'has_pricing_unit_relationship': bool(product.pricing_unit),
                'pricing_unit_object': {
                    'unit_id': product.pricing_unit.unit_id if product.pricing_unit else None,
                    'unit_name': product.pricing_unit.unit_name if product.pricing_unit else None,
                    'unit_description': product.pricing_unit.unit_description if product.pricing_unit else None
                } if product.pricing_unit else None})
        
        response_data = {'success': True,'debug_data': debug_data}
        set_cached_data(cache_key_str, response_data, 3600)  # Cache for 1 hour
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'success': False,'message': f'Debug error: {str(e)}'}), 500


@shop_bp.route('/debug-product/<int:product_id>')
def debug_product(product_id):
    """Debug route to check specific product data."""
    cache_key_str = cache_key("shop_debug_product", product_id)
    
    # Try cache first (30 minutes cache for debug data)
    cached_data, found = get_cached_data(cache_key_str, expire_seconds=1800)
    if found:
        return jsonify(cached_data)
    
    try:
        product = db.session.query(IncubateeProduct).filter(IncubateeProduct.product_id == product_id).first()
        
        if not product:
            response_data = {'success': False,'message': f'Product {product_id} not found'}
            set_cached_data(cache_key_str, response_data, 600)  # Cache negative result for 10 minutes
            return jsonify(response_data), 404
        debug_info = {
            'product_id': product.product_id,'name': product.name,'stock_amount': product.stock_amount,
            'price_per_stocks': float(product.price_per_stocks),
            'incubatee_id': product.incubatee_id,'has_incubatee': bool(product.incubatee),
            'incubatee_name': product.incubatee.company_name if product.incubatee else None,
            'table_name': IncubateeProduct.__tablename__}
        
        response_data = {'success': True,'debug_info': debug_info}
        set_cached_data(cache_key_str, response_data, 1800)  # Cache for 30 minutes
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'success': False,'message': f'Debug error: {str(e)}'}), 500
    
# Cache invalidation functions for shop data
def invalidate_shop_cache():
    """Invalidate all shop-related cache"""
    invalidate_cache("shop:*")

def invalidate_product_cache(product_id=None):
    """Invalidate product-specific cache"""
    if product_id:
        invalidate_cache(f"shop_product_stock:{product_id}")
        invalidate_cache(f"shop_debug_product:{product_id}")
    invalidate_cache("shop_products:*")
    invalidate_cache("shop_availability:*")
    invalidate_cache("shop_search:*")