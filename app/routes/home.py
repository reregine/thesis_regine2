from flask import Blueprint, render_template, session, redirect, url_for

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/")
def index():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    # This will render templates/home/index.html
    return render_template("home/index.html")
