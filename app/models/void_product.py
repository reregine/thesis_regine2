# models/void_product.py
from ..extension import db
from datetime import datetime

class VoidProduct(db.Model):
    __tablename__ = "void_products"
    
    void_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.reservation_id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id_no", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("incubatee_products.product_id", ondelete="CASCADE"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    problem_description = db.Column(db.Text)
    return_type = db.Column(db.String(50))
    image_path = db.Column(db.String(500))
    void_status = db.Column(db.String(20), default="pending")
    requested_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    processed_at = db.Column(db.DateTime(timezone=True))
    processed_by = db.Column(db.Integer, db.ForeignKey("admin_profiles.admin_id"))
    admin_notes = db.Column(db.Text)
    refund_amount = db.Column(db.Numeric(10, 2))
    refund_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    RETURN_TYPES = {
        'defective': 'Defective Product',
        'wrong_item': 'Wrong Item Received',
        'damaged': 'Damaged During Delivery',
        'not_as_described': 'Not as Described',
        'other': 'Other Reason'
    }
    
    STATUS_TYPES = {
        'pending': 'Pending Review',
        'approved': 'Approved for Refund',
        'rejected': 'Rejected',
        'refunded': 'Refund Completed'
    }
    
    REFUND_METHODS = {
        'wallet': 'Wallet Credit',
        'bank_transfer': 'Bank Transfer',
        'cash': 'Cash (On-site)'
    }
    
    def __repr__(self):
        return f"<VoidProduct {self.void_id}>"
    
    @property
    def formatted_requested_at(self):
        if self.requested_at:
            return self.requested_at.strftime("%b %d, %Y, %I:%M %p")
        return None
    
    @property
    def formatted_processed_at(self):
        if self.processed_at:
            return self.processed_at.strftime("%b %d, %Y, %I:%M %p")
        return None
    
    @property
    def display_return_type(self):
        return self.RETURN_TYPES.get(self.return_type, self.return_type)
    
    @property
    def display_status(self):
        return self.STATUS_TYPES.get(self.void_status, self.void_status)
    
    @property
    def display_refund_method(self):
        return self.REFUND_METHODS.get(self.refund_method, self.refund_method)