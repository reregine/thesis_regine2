# Virtual showroom & product browsing
from flask import Blueprint, render_template
from ..models import Product

showroom_bp = Blueprint("showroom", __name__, url_prefix="/showroom")

@showroom_bp.route("/")
def index():
    products = Product.query.all()
    return render_template("showroom/index.html", products=products)

@showroom_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("showroom/product_detail.html", product=product)
