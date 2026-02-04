from datetime import datetime
from app import db

class EmailLog(db.Model):
    """Model to log all email notifications sent"""
    __tablename__ = 'email_logs'
    
    log_id = db.Column(db.Integer, primary_key=True)
    email_type = db.Column(db.String(50), nullable=False)  # 'low_stock', 'admin_notification', etc.
    recipient_email = db.Column(db.String(255), nullable=False)
    recipient_name = db.Column(db.String(255))
    subject = db.Column(db.String(255), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('incubatee_products.product_id'), nullable=True)
    incubatee_id = db.Column(db.Integer, db.ForeignKey('incubatees.incubatee_id'), nullable=True)
    stock_amount = db.Column(db.Integer, nullable=True)
    threshold = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # 'sent', 'failed', 'skipped'
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    next_scheduled = db.Column(db.DateTime, nullable=True)
    interval_minutes = db.Column(db.Integer, default=5)  # Default 5 min interval
    
    # Relationships
    product = db.relationship('IncubateeProduct', backref='email_logs', lazy=True)
    incubatee = db.relationship('Incubatee', backref='email_logs', lazy=True)
    
    def __repr__(self):
        return f'<EmailLog {self.log_id}: {self.email_type} to {self.recipient_email}>'
    
    def to_dict(self):
        return {
            'log_id': self.log_id,
            'email_type': self.email_type,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'product_id': self.product_id,
            'incubatee_id': self.incubatee_id,
            'stock_amount': self.stock_amount,
            'threshold': self.threshold,
            'status': self.status,
            'error_message': self.error_message,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'next_scheduled': self.next_scheduled.isoformat() if self.next_scheduled else None,
            'interval_minutes': self.interval_minutes
        }