# Sales record model
from datetime import datetime
from ..extension import db

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    available = db.Column(db.Boolean, default=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key to Incubate
    incubate_id = db.Column(db.Integer, db.ForeignKey("incubates.id"), nullable=False)

    # Relationships
    reservations = db.relationship("Reservation", backref="product", lazy=True)
    sales = db.relationship("Sales", backref="product", lazy=True)

    def __repr__(self):
        return f"<Product {self.name}>"
