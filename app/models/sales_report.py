from ..extension import db
from datetime import datetime

class SalesReport(db.Model):
    __tablename__ = "sales_reports"
    
    sales_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.reservation_id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("incubatee_products.product_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_no"), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_date = db.Column(db.Date, nullable=False)  # Date when item was picked up/completed
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    reservation = db.relationship("Reservation", back_populates="sales_report")
    product = db.relationship("IncubateeProduct", back_populates="sales_reports")
    user = db.relationship("User", back_populates="sales_reports")
    
    def __repr__(self):
        return f"<SalesReport {self.sales_id} - {self.product_name}>"