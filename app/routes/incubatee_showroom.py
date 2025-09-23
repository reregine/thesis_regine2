from flask import Blueprint, render_template

# Create a blueprint for incubates showroom
incubatee_bp = Blueprint("incubatee_showroom", __name__)

@incubatee_bp.route("/incubates")
def incubatee_showroom():
    return render_template("incubates.html")
