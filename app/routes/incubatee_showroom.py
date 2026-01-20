# incubatee_showroom.py
import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, current_app, request
from werkzeug.utils import secure_filename
from ..models.admin import db, Incubatee, IncubateeProduct
from datetime import datetime

# Create a blueprint for incubates showroom
incubatee_bp = Blueprint("incubatee_showroom", __name__, url_prefix="/incubates")
def login_required(f):
    """Decorator to check if user is logged in"""
    def decorated_function(*args, **kwargs):
        if not session.get("user_logged_in") and not session.get("admin_logged_in"):
            return jsonify({"success": False, "message": "Please login to access this page"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@incubatee_bp.route("/")
@login_required
def incubatee_showroom():
    # Get all approved incubatees grouped by batch
    incubatees_by_batch = {}
    
    # Query all approved incubatees
    incubatees = Incubatee.query.filter_by(is_approved=True).order_by(Incubatee.batch, Incubatee.company_name).all()
    
    # Group by batch
    for incubatee in incubatees:
        batch_key = f"batch{incubatee.batch}"
        if batch_key not in incubatees_by_batch:
            incubatees_by_batch[batch_key] = []
        
        # Get incubatee's products count
        product_count = IncubateeProduct.query.filter_by(incubatee_id=incubatee.incubatee_id).count()
        
        # Determine status based on batch
        status = "Active" if incubatee.batch and incubatee.batch >= 3 else "Graduated"
        
        incubatees_by_batch[batch_key].append({
            "id": incubatee.incubatee_id,
            "company_name": incubatee.company_name or incubatee.full_name,
            "full_name": incubatee.full_name,
            "description": incubatee.contact_info or f"{incubatee.company_name or incubatee.first_name} - Agri-Aqua Technology Innovator",
            "batch": incubatee.batch,
            "email": incubatee.email,
            "phone": incubatee.phone_number,
            "website": incubatee.website,
            "logo_url": incubatee.logo_url,
            "product_count": product_count,
            "status": status,
            "year_joined": incubatee.created_at.year if incubatee.created_at else "Unknown"})
    
    # Get unique batches for navigation
    unique_batches = sorted(set(incubatee.batch for incubatee in incubatees if incubatee.batch is not None))
    
    return render_template("incubates/incubates.html", 
                         incubatees_by_batch=incubatees_by_batch,
                         unique_batches=unique_batches)

@incubatee_bp.route("/get-incubatee-details/<int:incubatee_id>")
def get_incubatee_details(incubatee_id):
    """Get detailed information about a specific incubatee"""
    try:
        incubatee = Incubatee.query.get_or_404(incubatee_id)
        
        # Get incubatee's products
        products = IncubateeProduct.query.filter_by(incubatee_id=incubatee_id).all()
        products_list = []
        
        for product in products:
            # Build proper image URL for products
            product_image_url = None
            if product.image_path:
                product_image_url = f"/{product.image_path}"
            
            products_list.append({
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "description": product.details or "No description available",
                "price": float(product.price_per_stocks),
                "stock": product.stock_amount,
                "image_path": product.image_path,
                "image_url": product_image_url  # Add this for proper URL handling
            })
        
        # Build incubatee details with proper logo URL
        incubatee_details = {
            "incubatee_id": incubatee.incubatee_id,
            "company_name": incubatee.company_name or incubatee.full_name,
            "full_name": incubatee.full_name,
            "description": incubatee.contact_info or "No additional information available",
            "batch": incubatee.batch or "Not specified",
            "email": incubatee.email or "No email provided",
            "phone": incubatee.phone_number or "No phone provided",
            "website": incubatee.website or "No website provided",
            "display_website": incubatee.display_website,
            "logo_url": incubatee.logo_url,  # This will use the fixed property
            "contact_info": incubatee.contact_info or "No contact information available",
            "status": "Active" if incubatee.batch and incubatee.batch >= 3 else "Graduated",
            "year_joined": incubatee.created_at.year if incubatee.created_at else "Unknown",
            "products": products_list,
            "product_count": len(products_list)
        }
        
        return jsonify({"success": True, "incubatee": incubatee_details})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500