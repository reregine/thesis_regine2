from ..extension import db
from datetime import datetime

class Reservation(db.Model):
    __tablename__ = "reservations"

    reservation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_no", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("incubatee_products.product_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reserved_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    approved_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    rejected_at = db.Column(db.DateTime(timezone=True))
    rejected_reason = db.Column(db.Text)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User",back_populates="reservations",foreign_keys=[user_id])
    product = db.relationship("IncubateeProduct",back_populates="reservations",foreign_keys=[product_id])

    def __repr__(self):
        return f"<Reservation {self.reservation_id}>"
