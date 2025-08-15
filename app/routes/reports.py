# Sales reports generation
from flask import Blueprint, render_template
from ..models import Sales

bp = Blueprint("reports", __name__, url_prefix="/reports")

@bp.route("/sales")
def sales_report():
    sales = Sales.query.all()
    total_revenue = sum(s.total_amount for s in sales)
    total_items = sum(s.quantity_sold for s in sales)
    return render_template(
        "reports/sales_report.html",
        sales=sales,
        total_revenue=total_revenue,
        total_items=total_items
    )
