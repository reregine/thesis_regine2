from flask import Blueprint, render_template, session, redirect, url_for

# Create blueprint for layouts
layouts_bp = Blueprint("layouts", __name__, url_prefix="/layout")

@layouts_bp.route("/")
def show_layout():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    """Render the base layout template."""
    return render_template("layouts/base.html")
