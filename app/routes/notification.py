# Product status notifications
from flask import Blueprint, render_template
from ..models import Notification

bp = Blueprint("notification", __name__, url_prefix="/notifications")

@bp.route("/")
def list_notifications():
    notifications = Notification.query.order_by(Notification.date_created.desc()).all()
    return render_template("notification/list.html", notifications=notifications)
