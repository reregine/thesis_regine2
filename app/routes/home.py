from flask import Blueprint, jsonify, render_template, session, redirect, url_for
from app.extension import db
from app.models.admin import Incubatee, IncubateeProduct, ProductPopularity
from sqlalchemy import desc, func, and_, or_
from datetime import datetime, timedelta

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/")
def index():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    # Pass login status to template
    user_logged_in = session.get("user_logged_in")
    admin_logged_in = session.get("admin_logged_in")
    username = session.get("username")
    
    # Get featured products for carousel
    featured_products = get_featured_products()
    
    # This will render templates/home/index.html
    return render_template(
        "home/index.html", 
        user_logged_in=user_logged_in,
        admin_logged_in=admin_logged_in,
        username=username,
        featured_products=featured_products
    )

@home_bp.route("/dashboard-content")
def dashboard_content():
    if not session.get("user_logged_in"):
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    return render_template("dashboard/dashboard.html",username=session.get("username"),user_logged_in=session.get("user_logged_in"))

# New routes for product data
@home_bp.route("/api/featured-products")
def get_featured_products_api():
    """API endpoint to get featured products for carousel"""
    try:
        featured_products = get_featured_products()
        return jsonify({"success": True,"featured_products": featured_products})
    except Exception as e:
        return jsonify({"success": False,"message": f"Error fetching featured products: {str(e)}"}), 500

@home_bp.route("/api/refresh-rankings", methods=["POST"])
def refresh_rankings():
    """Manual trigger to refresh product rankings"""
    try:
        update_product_rankings()
        return jsonify({
            "success": True,
            "message": "Product rankings updated successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating rankings: {str(e)}"
        }), 500

def get_featured_products():
    """Get products for the featured carousel with tags"""
    try:
        # Update rankings first to ensure data is current
        update_product_rankings()
        
        # Get best sellers (top 5 weekly)
        best_sellers = db.session.query(
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
            Incubatee.is_approved == True
        ).order_by(
            desc(ProductPopularity.weekly_rank)
        ).limit(5).all()
        
        # Get known products (top 10 by monthly customers)
        known_products = db.session.query(
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
            Incubatee.is_approved == True
        ).order_by(
            desc(ProductPopularity.monthly_customers)
        ).limit(10).all()
        
        # Format best sellers
        best_sellers_data = []
        for product, popularity, incubatee in best_sellers:
            best_sellers_data.append({
                'product_id': product.product_id,
                'name': product.name,
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
        
        # Format known products
        known_products_data = []
        for product, popularity, incubatee in known_products:
            known_products_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'monthly_customers': popularity.monthly_customers,
                'tag': 'known_product',
                'tag_text': f'👥 Popular Choice',
                'period_text': f'{popularity.monthly_customers} customers this month'
            })
        
        # Combine and shuffle for carousel (alternate between best sellers and known products)
        featured_products = []
        max_length = max(len(best_sellers_data), len(known_products_data))
        
        for i in range(max_length):
            if i < len(best_sellers_data):
                featured_products.append(best_sellers_data[i])
            if i < len(known_products_data):
                featured_products.append(known_products_data[i])
        
        return featured_products[:15]  # Limit to 15 products max
        
    except Exception as e:
        print(f"Error in get_featured_products: {str(e)}")
        return []

def update_product_rankings():
    """Update product rankings - Simple and reliable approach"""
    try:
        # Get current period dates
        current_week_start = datetime.now().date() - timedelta(days=datetime.now().weekday())
        current_month_start = datetime.now().replace(day=1).date()
        
        # Reset all flags
        for product in ProductPopularity.query.all():
            product.is_best_seller = False
            product.is_known_product = False
            product.weekly_rank = 0
        
        # Update best sellers (top 5 weekly per incubatee)
        incubatee_ids = db.session.query(ProductPopularity.incubatee_id).distinct()
        
        for incubatee_id in [inc_id[0] for inc_id in incubatee_ids]:
            # Weekly best sellers
            best_sellers = ProductPopularity.query.filter(
                ProductPopularity.incubatee_id == incubatee_id,
                ProductPopularity.weekly_sold > 0,
                ProductPopularity.week_start_date >= current_week_start
            ).order_by(
                ProductPopularity.weekly_sold.desc()
            ).limit(5).all()
            
            for rank, product in enumerate(best_sellers, 1):
                product.is_best_seller = True
                product.weekly_rank = rank
            
            # Monthly known products
            known_products = ProductPopularity.query.filter(
                ProductPopularity.incubatee_id == incubatee_id,
                ProductPopularity.monthly_customers > 0,
                ProductPopularity.month_start_date >= current_month_start
            ).order_by(
                ProductPopularity.monthly_customers.desc()
            ).limit(10).all()
            
            for product in known_products:
                product.is_known_product = True
        
        db.session.commit()
        print("✅ Product rankings updated successfully")
        
    except Exception as e:
        print(f"❌ Error in update_product_rankings: {str(e)}")
        db.session.rollback()

def get_featured_products():
    """Get products for the featured carousel with tags"""
    try:
        # Update rankings first to ensure data is current
        update_product_rankings()
        
        # Get best sellers (top 5 weekly)
        best_sellers = db.session.query(
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
            Incubatee.is_approved == True,
            ProductPopularity.weekly_sold > 0
        ).order_by(
            ProductPopularity.weekly_rank.asc()
        ).limit(5).all()
        
        # Get known products (top 10 by monthly customers)
        known_products = db.session.query(
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
            ProductPopularity.monthly_customers > 0
        ).order_by(
            ProductPopularity.monthly_customers.desc()
        ).limit(10).all()
        
        # Format best sellers
        best_sellers_data = []
        for product, popularity, incubatee in best_sellers:
            best_sellers_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'weekly_sold': popularity.weekly_sold,
                'weekly_rank': popularity.weekly_rank or 1,
                'tag': 'best_seller',
                'tag_text': f'🔥 #{popularity.weekly_rank or 1} Best Seller',
                'period_text': f'{popularity.weekly_sold} sold this week'
            })
        
        # Format known products
        known_products_data = []
        for product, popularity, incubatee in known_products:
            known_products_data.append({
                'product_id': product.product_id,
                'name': product.name,
                'image_path': product.image_path,
                'price_per_stocks': float(product.price_per_stocks),
                'incubatee_name': incubatee.company_name or f"{incubatee.first_name} {incubatee.last_name}",
                'incubatee_batch': incubatee.batch,
                'monthly_customers': popularity.monthly_customers,
                'tag': 'known_product',
                'tag_text': f'👥 Popular Choice',
                'period_text': f'{popularity.monthly_customers} customers this month'
            })
        
        # Combine and shuffle for carousel (alternate between best sellers and known products)
        featured_products = []
        max_length = max(len(best_sellers_data), len(known_products_data))
        
        for i in range(max_length):
            if i < len(best_sellers_data):
                featured_products.append(best_sellers_data[i])
            if i < len(known_products_data):
                featured_products.append(known_products_data[i])
        
        return featured_products[:15]  # Limit to 15 products max
        
    except Exception as e:
        print(f"Error in get_featured_products: {str(e)}")
        return []