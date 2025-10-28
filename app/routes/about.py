from flask import Blueprint, render_template
# Create a blueprint for about
about_bp = Blueprint("about", __name__, url_prefix="/about")
@about_bp.route("/", methods=["GET"])
def about_page():
    # This will render your about.html page
    return render_template("contacts/about.html")