from ..models import Sales

def generate_sales_report():
    """Generate sales totals."""
    sales = Sales.query.all()
    total_revenue = sum(s.total_amount for s in sales)
    total_items_sold = sum(s.quantity_sold for s in sales)
    return {
        "sales": sales,
        "total_revenue": total_revenue,
        "total_items_sold": total_items_sold
    }
