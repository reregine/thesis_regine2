# Reservation model
from datetime import datetime
from ..extension import db

class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="pending")  # pending, confirmed, cancelled
    date_reserved = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key to Product
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    def __repr__(self):
        return f"<Reservation {self.customer_name} - {self.status}>"
