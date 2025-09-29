from flask import Blueprint, render_template

# Create a blueprint for incubates showroom
incubatee_bp = Blueprint("incubatee_showroom", __name__, url_prefix="/incubates")

@incubatee_bp.route("/")
def incubatee_showroom():
    return render_template("incubates/incubates.html")
