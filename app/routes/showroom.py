# Virtual showroom & product browsing
from flask import Blueprint, render_template, session, redirect, url_for
from ..models import IncubateeProduct

showroom_bp = Blueprint("showroom", __name__, url_prefix="/showroom")

@showroom_bp.route("/")
def index():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    products = IncubateeProduct.query.all()
    return render_template("showroom/index.html", products=products)

@showroom_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = IncubateeProduct.query.get_or_404(product_id)
    return render_template("showroom/product_detail.html", product=product)
