from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__, url_prefix="/")

@admin_bp.route("/")
def admin():
    #this is to access the route /admin/admin.html
    return render_template("admin/admin.html")