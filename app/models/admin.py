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
    is_approved = db.Column(db.Boolean, default=False)  # New field for approval status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship: One incubatee → Many products
    products = db.relationship("IncubateeProduct", back_populates="incubatee", cascade="all, delete-orphan")
    sales_reports = db.relationship("SalesReport", back_populates="incubatee", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Incubatee {self.first_name} {self.last_name}>"

class IncubateeProduct(db.Model):
    __tablename__ = "incubatee_products"
    
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incubatee_id = db.Column(db.Integer, db.ForeignKey("incubatees.incubatee_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    stock_no = db.Column(db.String(50), nullable=False)
    products = db.Column(db.String(150), nullable=False)
    stock_amount = db.Column(db.Integer, nullable=False)
    price_per_stocks = db.Column(db.Numeric(8, 2), nullable=False)
    pricing_unit_id = db.Column(db.Integer, db.ForeignKey("pricing_units.unit_id"), nullable=False, default=1)
    details = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    warranty = db.Column(db.String(100), nullable=True)
    added_on = db.Column(db.Date, nullable=False, default=date.today)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incubatee = db.relationship("Incubatee", back_populates="products")
    pricing_unit = db.relationship("PricingUnit")
    reservations = db.relationship("Reservation", back_populates="product", cascade="all, delete-orphan")
    sales_reports = db.relationship("SalesReport", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<IncubateeProduct {self.name}>"

class PricingUnit(db.Model):
    """Represents different pricing units (per item, per kilo, per package, etc.)"""
    __tablename__ = "pricing_units"
    
    unit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unit_name = db.Column(db.String(50), nullable=False, unique=True)
    unit_description = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PricingUnit {self.unit_name}>"

class AdminProfile(db.Model):
    """Admin profile information"""
    __tablename__ = "admin_profiles"
    
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AdminProfile {self.full_name}>"

class SalesReport(db.Model):
    """Sales reports for incubatees"""
    __tablename__ = "sales_reports"
    __table_args__ = {'extend_existing': True}
    
    # Match your exact database columns
    sales_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.reservation_id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("incubatee_products.product_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_no"), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)  # This exists in your database
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(8, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add the new column we need (make it nullable initially since it's being added)
    incubatee_id = db.Column(db.Integer, db.ForeignKey("incubatees.incubatee_id"), nullable=True)
    
    incubatee = db.relationship("Incubatee", back_populates="sales_reports")
    product = db.relationship("IncubateeProduct", back_populates="sales_reports")
    user = db.relationship("User", back_populates="sales_reports")
    reservation = db.relationship("Reservation", back_populates="sales_report")
    
    def __repr__(self):
        return f"<SalesReport {self.sales_id}>"