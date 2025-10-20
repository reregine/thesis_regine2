# models/admin.py
from app.extension import db
from datetime import date, datetime

class Incubatee(db.Model):
    """Represents the incubatee (owner/vendor of products)."""
    __tablename__ = "incubatees"

    incubatee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    last_name = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    contact_info = db.Column(db.Text, nullable=True)
    batch = db.Column(db.Integer, nullable=True)
    company_name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)

    # Relationship: One incubatee → Many products
    products = db.relationship("IncubateeProduct", back_populates="incubatee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Incubatee {self.first_name} {self.last_name}>"

class IncubateeProduct(db.Model):
    """Represents a product posted by an incubatee."""
    __tablename__ = "incubatee_products"

    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incubatee_id = db.Column(db.Integer, db.ForeignKey("incubatees.incubatee_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock_no = db.Column(db.String(50), nullable=False)
    products = db.Column(db.String(150), nullable=False)
    stock_amount = db.Column(db.Integer, nullable=False)
    price_per_stocks = db.Column(db.Numeric(8, 2), nullable=False)
    details = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    warranty = db.Column(db.String(100), nullable=True)
    added_on = db.Column(db.Date, nullable=False, default=date.today)
    image_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to Incubatee
    incubatee = db.relationship("Incubatee", back_populates="products")

    def __repr__(self):
        return f"<IncubateeProduct {self.name}>"
