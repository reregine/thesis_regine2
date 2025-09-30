# Inventory management
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..extension import db
from ..models import Product

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

@inventory_bp.route("/")
def dashboard():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    products = Product.query.all()
    return render_template("inventory/dashboard.html", products=products)

@inventory_bp.route("/update/<int:product_id>", methods=["POST"])
def update_stock(product_id):
    product = Product.query.get_or_404(product_id)
    new_stock = int(request.form.get("stock", product.stock_quantity))
    product.stock_quantity = new_stock
    product.available = new_stock > 0
    db.session.commit()
    flash("Stock updated successfully!", "success")
    return redirect(url_for("inventory.dashboard"))
