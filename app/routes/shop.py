from flask import Blueprint, render_template

# Create Blueprint for shop
shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

@shop_bp.route("/")
def shop_home():
    """Render the Shop page."""
    return render_template("shop/shop.html")
