from app.extension import db
from datetime import datetime

class Cart(db.Model):
    """Represents items a user adds to their cart before reservation or checkout."""
    __tablename__ = "cart"

    cart_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_no", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("incubatee_products.product_id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    added_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships — note: only string references here (no direct imports)
    user = db.relationship("User", backref=db.backref("cart_items", cascade="all, delete-orphan"))
    product = db.relationship("IncubateeProduct", backref=db.backref("cart_entries", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Cart user={self.user_id} product={self.product_id} qty={self.quantity}>"
