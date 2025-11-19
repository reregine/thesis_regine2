from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from app.models.shop import Shop
from ..models.admin import IncubateeProduct
from ..extension import db

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")


@shop_bp.route("/")
def shop_home():
    return render_template("shop/shop.html")


@shop_bp.route("/search-products", methods=["GET"])
def search_products():
    """Search or list all incubatee products."""
    query = request.args.get("q", "").strip()

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
                "stocks": p.stock_amount,  # ✅ Changed from 'stocks' to 'stock_amount'
                "expiration_date": (
                    p.expiration_date.strftime("%Y-%m-%d")
                    if p.expiration_date
                    else "No Expiry"
                ),"warranty": p.warranty,"added_on": p.added_on.strftime("%Y-%m-%d"),"image_path": p.image_path})

        return jsonify({"success": True, "products": result})

    except Exception as e:
        print("❌ Error fetching products:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/product-availability", methods=["GET"])
def product_availability():
    """Get product stock availability for all products."""
    try:
        products = Shop.get_all_products()
        availability_data = []
        
        for product in products:
            availability_data.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "current_stock": product.stock_amount,  # ✅ Changed to stock_amount
                "availability_status": get_availability_status(product.stock_amount),  # ✅ Changed to stock_amount
                "price_per_stocks": float(product.price_per_stocks),
                "updated_at": product.added_on.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return jsonify({"success": True, "products": availability_data,"total_products": len(availability_data),
            "in_stock_count": len([p for p in availability_data if p['current_stock'] > 0]),
            "low_stock_count": len([p for p in availability_data if 1 <= p['current_stock'] <= 5]),
            "out_of_stock_count": len([p for p in availability_data if p['current_stock'] == 0])})
        
    except Exception as e:
        print("❌ Error fetching product availability:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@shop_bp.route("/product/<int:product_id>/stock", methods=["GET"])
def get_product_stock(product_id):
    """Get stock information for a specific product."""
    try:
        product = Shop.get_product_by_id(product_id)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404
        
        stock_info = {"product_id": product.product_id,
            "name": product.name,
            "current_stock": product.stock_amount,  # ✅ Changed to stock_amount
            "availability_status": get_availability_status(product.stock_amount),  # ✅ Changed to stock_amount
            "price": float(product.price_per_stocks),
            "last_updated": product.added_on.strftime("%Y-%m-%d %H:%M:%S")}
        
        return jsonify({"success": True, "product": stock_info})
        
    except Exception as e:
        print(f"❌ Error fetching stock for product {product_id}:", e)
        return jsonify({"success": False, "error": str(e)}), 500


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
    
@shop_bp.route('/get-products')
def get_products():
    """Get all products with pricing details."""
    try:
        products = Shop.get_all_products()
        
        products_data = []
        for product in products:
            product_data = {
                'product_id': product.product_id,
                'name': product.name,
                'products': product.products,
                'stock_amount': product.stock_amount,
                'price_per_stocks': float(product.price_per_stocks),
                'pricing_unit': product.pricing_unit.unit_name if product.pricing_unit else 'Item',
                'pricing_description': product.pricing_unit.unit_description if product.pricing_unit else 'Per Item',
                'details': product.details,
                'category': product.category,
                'expiration_date': product.expiration_date.strftime('%Y-%m-%d') if product.expiration_date else None,
                'warranty': product.warranty,
                'image_path': product.image_path,
                'added_on': product.added_on.strftime('%Y-%m-%d'),
                'incubatee': {
                    'incubatee_id': product.incubatee.incubatee_id,
                    'company_name': product.incubatee.company_name,
                    'contact_info': product.incubatee.contact_info,
                    'email': product.incubatee.email,
                    'phone_number': product.incubatee.phone_number
                } if product.incubatee else None
            }
            products_data.append(product_data)
        
        return jsonify({'success': True,'products': products_data})
        
    except Exception as e:
        return jsonify({'success': False,'message': f'Error fetching products: {str(e)}'}), 500
    
@shop_bp.route('/debug-pricing')
def debug_pricing():
    """Debug route to check pricing unit data."""
    try:
        # Get a few products with their pricing units
        products = IncubateeProduct.query.limit(3).all()
        
        debug_data = []
        for product in products:
            debug_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'pricing_unit_id': product.pricing_unit_id,
                'has_pricing_unit_relationship': bool(product.pricing_unit),
                'pricing_unit_object': {
                    'unit_id': product.pricing_unit.unit_id if product.pricing_unit else None,
                    'unit_name': product.pricing_unit.unit_name if product.pricing_unit else None,
                    'unit_description': product.pricing_unit.unit_description if product.pricing_unit else None
                } if product.pricing_unit else None
            })
        
        return jsonify({
            'success': True,
            'debug_data': debug_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Debug error: {str(e)}'
        }), 500