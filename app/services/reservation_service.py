 # Reservation handling logic
from ..extension import db
from ..models import Reservation, Product
from .notification_service import create_notification

def create_reservation(customer_name, customer_email, quantity, product_id):
    """Create a new reservation if stock is available."""
    product = Product.query.get(product_id)
    if not product or product.stock_quantity < quantity:
        return None  # Not enough stock

    # Reduce stock
    product.stock_quantity -= quantity
    product.available = product.stock_quantity > 0

    reservation = Reservation(
        customer_name=customer_name,
        customer_email=customer_email,
        quantity=quantity,
        product_id=product_id
    )

    db.session.add(reservation)
    db.session.commit()

    # Create notification
    create_notification(
        message=f"New reservation for {product.name} by {customer_name}.",
        product_id=product_id,
        reservation_id=reservation.id
    )

    return reservation

def get_reservations_by_product(product_id):
    """Fetch reservations for a given product."""
    return Reservation.query.filter_by(product_id=product_id).all()
