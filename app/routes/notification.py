# Product status notifications
from flask import Blueprint, render_template, session, redirect, url_for
from ..models import Notification

notif_bp = Blueprint("notification", __name__, url_prefix="/notifications")

@notif_bp.route("/")
def list_notifications():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    notifications = Notification.query.order_by(Notification.date_created.desc()).all()
    return render_template("notification/list.html", notifications=notifications)
