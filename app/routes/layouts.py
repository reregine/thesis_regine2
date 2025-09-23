from flask import Blueprint, render_template

# Create blueprint for layouts
layouts_bp = Blueprint("layouts", __name__)

@layouts_bp.route("/layout")
def show_layout():
    """Render the base layout template."""
    return render_template("layouts/base.html")
