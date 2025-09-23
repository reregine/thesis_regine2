# models/notification.py
from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)          # Notification title
    message = db.Column(db.Text, nullable=False)               # Detailed message
    type = db.Column(db.String(50), default="info")            # info, success, warning, error
    is_read = db.Column(db.Boolean, default=False)             # Track if seen
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Timestamp
    incubate_id = db.Column(db.Integer, db.ForeignKey("incubates.id"), nullable=True) 
    # optional: link notification to specific incubate

    def __repr__(self):
        return f"<Notification {self.title} - {self.type}>"
