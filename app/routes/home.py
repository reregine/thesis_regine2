from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from app.extension import db
from app.models.admin import Incubatee, IncubateeProduct, ProductPopularity
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta
from app.services.popularity_service import ProductPopularityService

home_bp = Blueprint("home", __name__, url_prefix="/")

def get_featured_products():
    """Get products for the featured carousel - SIMPLIFIED VERSION"""
    try:
        print("🎯 Fetching featured products...")
        
        # Get products from TWO categories:
        # 1. Weekly Best Sellers (top 5)
        # 2. Monthly Known Products (top 10)
        
        # 1. Get WEEKLY best sellers (top 5)
        weekly_best_sellers = db.session.query(
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
            ProductPopularity.is_best_seller == True,
            ProductPopularity.weekly_rank < 999,  # Exclude monthly fillers
            Incubatee.is_approved == True
        ).order_by(
            ProductPopularity.weekly_rank.asc()
        ).limit(5).all()
        
        # 2. Get MONTHLY known products (top 10)
        monthly_known_products = db.session.query(
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
            ProductPopularity.is_known_product == True,
            Incubatee.is_approved == True,
            ~ProductPopularity.product_id.in_([p[0].product_id for p in weekly_best_sellers])  # Avoid duplicates
        ).order_by(
            ProductPopularity.monthly_customers.desc()
        ).limit(10).all()
        
        # Format WEEKLY best sellers
        weekly_data = []
        for product, popularity, incubatee in weekly_best_sellers:
            weekly_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'products': product.products,
                'details': product.details,
                'category': product.category,
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'weekly_sold': popularity.weekly_sold,
                'weekly_rank': popularity.weekly_rank,
                'tag': 'best_seller',
                'tag_text': f'🔥 #{popularity.weekly_rank} Best Seller',
                'period_text': f'{popularity.weekly_sold} sold this week'
            })
        
        # Format MONTHLY known products
        monthly_data = []
        for product, popularity, incubatee in monthly_known_products:
            monthly_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'products': product.products,
                'details': product.details,
                'category': product.category,
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'monthly_customers': popularity.monthly_customers,
                'tag': 'known_product',
                'tag_text': f'👥 Popular Choice',
                'period_text': f'{popularity.monthly_customers} customers this month'
            })
        
        # Combine products - WEEKLY first, then MONTHLY
        featured_products = []
        featured_products.extend(weekly_data)  # Add weekly best sellers first
        
        # Add monthly known products (avoiding duplicates)
        weekly_ids = {p['product_id'] for p in featured_products}
        for monthly_product in monthly_data:
            if monthly_product['product_id'] not in weekly_ids:
                featured_products.append(monthly_product)
        
        # If we still don't have enough products, add MONTHLY FILLERS (products marked as best_seller with rank 999)
        if len(featured_products) < 8:
            monthly_fillers = db.session.query(
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
                ProductPopularity.is_best_seller == True,
                ProductPopularity.weekly_rank == 999,  # Monthly fillers
                Incubatee.is_approved == True,
                ~ProductPopularity.product_id.in_([p['product_id'] for p in featured_products])
            ).order_by(
                ProductPopularity.monthly_sold.desc()
            ).limit(8 - len(featured_products)).all()
            
            for product, popularity, incubatee in monthly_fillers:
                featured_products.append({
                    'product_id': product.product_id,
                    'name': product.name,
                    'products': product.products,
                    'details': product.details,
                    'category': product.category,
                    'image_path': product.image_path,
                    'price_per_stocks': float(product.price_per_stocks),
                    'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                    'incubatee_batch': incubatee.batch,
                    'monthly_sold': popularity.monthly_sold,
                    'tag': 'best_seller',
                    'tag_text': f'⭐ Monthly Performer',
                    'period_text': f'{popularity.monthly_sold} sold this month'
                })
        
        print(f"✅ Found {len(featured_products)} featured products: "
              f"{len(weekly_data)} weekly best sellers, "
              f"{len(monthly_data)} monthly known products")
        
        return featured_products[:15]  # Limit to 15 products max
        
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