# Inventory management
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extension import db
from ..models import Product

bp = Blueprint("inventory", __name__, url_prefix="/inventory")

@bp.route("/")
def dashboard():
    products = Product.query.all()
    return render_template("inventory/dashboard.html", products=products)

@bp.route("/update/<int:product_id>", methods=["POST"])
def update_stock(product_id):
    product = Product.query.get_or_404(product_id)
    new_stock = int(request.form.get("stock", product.stock_quantity))
    product.stock_quantity = new_stock
    product.available = new_stock > 0
    db.session.commit()
    flash("Stock updated successfully!", "success")
    return redirect(url_for("inventory.dashboard"))
