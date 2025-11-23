from ..extension import db
from datetime import datetime, timezone

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'reservation', 'system', 'alert'
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='unread')  # 'unread', 'read'
    related_id = db.Column(db.Integer)  # reservation_id or other related entity
    related_type = db.Column(db.String(50))  # 'reservation', 'product', etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    read_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'notification_id': self.notification_id,
            'user_id': self.user_id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'status': self.status,
            'related_id': self.related_id,
            'related_type': self.related_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'time_ago': self.get_time_ago()
        }
    
    def get_time_ago(self):
        """Calculate human-readable time difference"""
        if not self.created_at:
            return "Recently"
            
        now = datetime.now(timezone.utc)
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def mark_as_read(self):
        self.status = 'read'
        self.read_at = datetime.now(timezone.utc)