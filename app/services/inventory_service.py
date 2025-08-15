# Stock monitoring & updates
from ..extension import db
from ..models import Product

def update_stock(product_id: int, new_stock: int) -> bool:
    """Update product stock and availability status."""
    product = Product.query.get(product_id)
    if not product:
        return False
    product.stock_quantity = new_stock
    product.available = new_stock > 0
    db.session.commit()
    return True

def get_all_products():
    """Fetch all products."""
    return Product.query.all()
