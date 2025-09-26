from flask import Blueprint, render_template

login_bp = Blueprint("login", __name__, url_prefix="/")

@login_bp.route("/")
def login():
    #this will render template of /login/login.html
    return render_template("login/login.html")