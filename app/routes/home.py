from flask import Blueprint, render_template

bp = Blueprint("home", __name__, url_prefix="/")

@bp.route("/")
def index():
    # This will render templates/home/index.html
    return render_template("home/index.html")
