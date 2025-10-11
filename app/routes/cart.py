from flask import Blueprint, render_template, session, redirect, url_for

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")

@cart_bp.route("/")
def cart_page():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    # This will render templates/cart/cart.html
    return render_template("cart/cart.html")