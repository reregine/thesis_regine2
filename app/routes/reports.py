# Sales reports generation
from flask import Blueprint, render_template, session, redirect, url_for
from ..models import Sales

report_bp = Blueprint("reports", __name__, url_prefix="/reports")

@report_bp.route("/sales")
def sales_report():
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    sales = Sales.query.all()
    total_revenue = sum(s.total_amount for s in sales)
    total_items = sum(s.quantity_sold for s in sales)
    return render_template(
        "reports/sales_report.html",
        sales=sales,
        total_revenue=total_revenue,
        total_items=total_items)
