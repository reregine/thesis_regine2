from flask import Blueprint, render_template, session, redirect, url_for

# Create Blueprint for shop
shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

@shop_bp.route("/")
def shop_home():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    """Render the Shop page."""
    return render_template("shop/shop.html")
