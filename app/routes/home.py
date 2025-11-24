from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from app.extension import db
from app.models.admin import Incubatee, IncubateeProduct, ProductPopularity
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
from app.services.popularity_service import ProductPopularityService

home_bp = Blueprint("home", __name__, url_prefix="/")

def get_featured_products():
    """Get products for the featured carousel - ROBUST VERSION"""
    try:
        print("🎯 Fetching featured products (robust version)...")
        
        # Use a single query with eager loading to avoid connection issues
        featured_query = db.session.query(
            IncubateeProduct,
            ProductPopularity,
            Incubatee
        ).join(
            ProductPopularity, 
            IncubateeProduct.product_id == ProductPopularity.product_id
        ).join(
            Incubatee,
            IncubateeProduct.incubatee_id == Incubatee.incubatee_id
        ).filter(
            Incubatee.is_approved == True
        ).options(
            db.joinedload(IncubateeProduct.incubatee),
            db.joinedload(ProductPopularity.product)
        )
        
        # Get all approved products with popularity data
        all_products = featured_query.all()
        
        print(f"📊 Found {len(all_products)} products with popularity data")
        
        featured_products = []
        
        # Process best sellers first
        best_sellers = [p for p in all_products if p[1].is_best_seller]
        print(f"🔥 Best sellers: {len(best_sellers)}")
        
        for product, popularity, incubatee in best_sellers[:5]:  # Limit to 5
            featured_products.append({
                'product_id': product.product_id,
                'name': product.name,
                'products': product.products or 'Product',
                'details': product.details or 'No description available.',
                'category': product.category or 'General',
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'weekly_sold': popularity.weekly_sold,
                'weekly_rank': popularity.weekly_rank or 1,
                'tag': 'best_seller',
                'tag_text': f'🔥 #{popularity.weekly_rank or 1} Best Seller',
                'period_text': f'{popularity.weekly_sold} sold this week',
                'period': 'weekly'
            })
        
        # Process known products (avoid duplicates)
        known_products = [p for p in all_products if p[1].is_known_product and p[0].product_id not in [fp['product_id'] for fp in featured_products]]
        print(f"⭐ Known products: {len(known_products)}")
        
        for product, popularity, incubatee in known_products[:10]:  # Limit to 10
            featured_products.append({
                'product_id': product.product_id,
                'name': product.name,
                'products': product.products or 'Product',
                'details': product.details or 'No description available.',
                'category': product.category or 'General',
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'monthly_customers': popularity.monthly_customers,
                'tag': 'known_product',
                'tag_text': f'⭐ Customer Favorite',
                'period_text': f'{popularity.monthly_customers} customers this month',
                'period': 'monthly'
            })
        
        # If still no products, use fallback - ANY approved products
        if len(featured_products) == 0:
            print("🔄 No featured products found, using fallback...")
            fallback_products = db.session.query(
                IncubateeProduct,
                Incubatee
            ).join(
                Incubatee,
                IncubateeProduct.incubatee_id == Incubatee.incubatee_id
            ).filter(
                Incubatee.is_approved == True
            ).limit(8).all()
            
            for product, incubatee in fallback_products:
                featured_products.append({
                    'product_id': product.product_id,
                    'name': product.name,
                    'products': product.products or 'Product',
                    'details': product.details or 'No description available.',
                    'category': product.category or 'General',
                    'image_path': product.image_path,
                    'price_per_stocks': float(product.price_per_stocks),
                    'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                    'incubatee_batch': incubatee.batch,
                    'tag': 'regular',
                    'tag_text': '🌟 Featured',
                    'period_text': 'Just added',
                    'period': 'all'
                })
        
        print(f"✅ Returning {len(featured_products)} featured products")
        
        # Debug output
        for product in featured_products:
            print(f"  - {product['name']} (Tag: {product['tag']}, Period: {product.get('period', 'all')})")
        
        return featured_products
        
    except Exception as e:
        print(f"❌ Error in get_featured_products: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    
@home_bp.route("/")
def index():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))
    
    # Pass login status to template
    user_logged_in = session.get("user_logged_in")
    admin_logged_in = session.get("admin_logged_in")
    username = session.get("username")
    
    # Get featured products for carousel - with error handling
    try:
        featured_products = get_featured_products()
    except Exception as e:
        print(f"❌ Error getting featured products: {str(e)}")
        featured_products = []  # Empty array on error
    
    return render_template("home/index.html", 
                         user_logged_in=user_logged_in,
                         admin_logged_in=admin_logged_in,
                         username=username,
                         featured_products=featured_products)
    
@home_bp.route("/dashboard-content")
def dashboard_content():
    if not session.get("user_logged_in"):
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    return render_template("dashboard/dashboard.html",
                         username=session.get("username"),
                         user_logged_in=session.get("user_logged_in"))

# API routes for product data
@home_bp.route("/api/featured-products")
def get_featured_products_api():
    """API endpoint to get featured products for carousel"""
    try:
        featured_products = get_featured_products()
        return jsonify({
            "success": True,
            "featured_products": featured_products
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching featured products: {str(e)}"
        }), 500

@home_bp.route("/api/refresh-rankings", methods=["POST"])
def refresh_rankings():
    """Manual trigger to refresh product rankings"""
    try:
        ProductPopularityService.update_product_rankings()
        return jsonify({
            "success": True,
            "message": "Product rankings updated successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating rankings: {str(e)}"
        }), 500

@home_bp.route("/api/popularity-stats")
def get_popularity_stats():
    """Get current popularity statistics"""
    try:
        total_products = ProductPopularity.query.count()
        best_sellers_count = ProductPopularity.query.filter_by(is_best_seller=True).count()
        known_products_count = ProductPopularity.query.filter_by(is_known_product=True).count()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_products_tracked": total_products,
                "best_sellers": best_sellers_count,
                "known_products": known_products_count
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching popularity stats: {str(e)}"
        }), 500

@home_bp.route("/api/debug-popularity", methods=["GET"])
def debug_popularity():
    """Debug endpoint to check popularity data"""
    try:
        from app.models.admin import ProductPopularity, SalesReport
        
        # Get all popularity data
        popularity_data = ProductPopularity.query.all()
        sales_data = SalesReport.query.all()
        
        result = {
            "popularity_records": [],
            "sales_reports": [],
            "summary": {
                "total_popularity_records": len(popularity_data),
                "total_sales_reports": len(sales_data)
            }
        }
        
        for pop in popularity_data:
            result["popularity_records"].append({
                "product_id": pop.product_id,
                "weekly_sold": pop.weekly_sold,
                "monthly_customers": pop.monthly_customers,
                "weekly_revenue": float(pop.weekly_revenue),
                "is_best_seller": pop.is_best_seller,
                "is_known_product": pop.is_known_product,
                "weekly_rank": pop.weekly_rank
            })
        
        for sale in sales_data:
            result["sales_reports"].append({
                "sales_id": sale.sales_id,
                "product_id": sale.product_id,
                "product_name": sale.product_name,
                "quantity": sale.quantity,
                "total_price": float(sale.total_price),
                "sale_date": sale.sale_date.isoformat()
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@home_bp.route("/api/force-update-flags", methods=["POST"])
def force_update_flags():
    """Force update product flags for testing"""
    try:
        from app.services.popularity_service import ProductPopularityService
        ProductPopularityService.force_update_flags()
        ProductPopularityService.update_product_rankings()
        
        return jsonify({
            "success": True,
            "message": "Product flags force updated successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@home_bp.route("/api/check-popularity-data")
def check_popularity_data():
    """Check what popularity data exists"""
    try:
        from app.models.admin import ProductPopularity, IncubateeProduct, Incubatee
        
        # Check products that should be featured
        best_sellers = ProductPopularity.query.filter_by(is_best_seller=True).all()
        known_products = ProductPopularity.query.filter_by(is_known_product=True).all()
        all_popularity = ProductPopularity.query.all()
        
        result = {
            "best_sellers_count": len(best_sellers),
            "known_products_count": len(known_products),
            "total_popularity_records": len(all_popularity),
            "best_sellers": [],
            "known_products": [],
            "all_products_with_sales": []
        }
        
        for pop in best_sellers:
            product = IncubateeProduct.query.get(pop.product_id)
            incubatee = Incubatee.query.get(pop.incubatee_id) if pop.incubatee_id else None
            result["best_sellers"].append({
                "product_id": pop.product_id,
                "product_name": product.name if product else "Unknown",
                "incubatee_name": incubatee.company_name if incubatee else "Unknown",
                "is_approved": incubatee.is_approved if incubatee else False,
                "weekly_sold": pop.weekly_sold,
                "weekly_rank": pop.weekly_rank,
                "is_best_seller": pop.is_best_seller
            })
        
        for pop in known_products:
            product = IncubateeProduct.query.get(pop.product_id)
            incubatee = Incubatee.query.get(pop.incubatee_id) if pop.incubatee_id else None
            result["known_products"].append({
                "product_id": pop.product_id,
                "product_name": product.name if product else "Unknown",
                "incubatee_name": incubatee.company_name if incubatee else "Unknown",
                "is_approved": incubatee.is_approved if incubatee else False,
                "monthly_customers": pop.monthly_customers,
                "is_known_product": pop.is_known_product
            })
        
        # Get all products with any sales activity
        products_with_activity = ProductPopularity.query.filter(
            (ProductPopularity.weekly_sold > 0) | 
            (ProductPopularity.monthly_sold > 0) |
            (ProductPopularity.monthly_customers > 0)
        ).all()
        
        for pop in products_with_activity:
            product = IncubateeProduct.query.get(pop.product_id)
            incubatee = Incubatee.query.get(pop.incubatee_id) if pop.incubatee_id else None
            result["all_products_with_sales"].append({
                "product_id": pop.product_id,
                "product_name": product.name if product else "Unknown",
                "incubatee_name": incubatee.company_name if incubatee else "Unknown",
                "is_approved": incubatee.is_approved if incubatee else False,
                "weekly_sold": pop.weekly_sold,
                "monthly_sold": pop.monthly_sold,
                "monthly_customers": pop.monthly_customers,
                "is_best_seller": pop.is_best_seller,
                "is_known_product": pop.is_known_product
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500