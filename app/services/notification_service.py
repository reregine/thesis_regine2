 # Sending product status notifications
from datetime import datetime
from ..extension import db
from ..models import Notification

def create_notification(message: str, product_id=None, reservation_id=None):
    """Create a new notification."""
    notification = Notification(
        message=message,
        product_id=product_id,
        reservation_id=reservation_id,
        date_created=datetime.utcnow()
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def get_unread_notifications():
    """Fetch unread notifications."""
    return Notification.query.filter_by(is_read=False).order_by(Notification.date_created.desc()).all()

def mark_as_read(notification_id: int) -> bool:
    """Mark a notification as read."""
    notification = Notification.query.get(notification_id)
    if not notification:
        return False
    notification.is_read = True
    db.session.commit()
    return True
