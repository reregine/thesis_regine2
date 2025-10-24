from ..extension import db
from datetime import datetime

class Favorite(db.Model):
    __tablename__ = 'favorites'
    
    favorite_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id_no'), nullable=False)  # Changed to id_no
    product_id = db.Column(db.Integer, db.ForeignKey('incubatee_products.product_id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('favorites', lazy=True))
    product = db.relationship('IncubateeProduct', backref=db.backref('favorites', lazy=True))
    
    def to_dict(self):
        return {'favorite_id': self.favorite_id,'user_id': self.user_id,'product_id': self.product_id,'added_at': self.added_at.isoformat() if self.added_at else None,'updated_at': self.updated_at.isoformat() if self.updated_at else None}