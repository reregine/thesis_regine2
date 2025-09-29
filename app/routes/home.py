from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__, url_prefix="/")

@home_bp.route("/")
def index():
    # This will render templates/home/index.html
    return render_template("home/index.html")
