from flask import Blueprint, render_template, session, redirect, url_for

# Create a blueprint for incubates showroom
incubatee_bp = Blueprint("incubatee_showroom", __name__, url_prefix="/incubates")

@incubatee_bp.route("/")
def incubatee_showroom():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    return render_template("incubates/incubates.html")
