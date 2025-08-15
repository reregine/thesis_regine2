# Incubate model
from datetime import datetime
from ..extension import db

class Incubate(db.Model):
    __tablename__ = "incubates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    products = db.relationship("Product", backref="incubate", lazy=True)

    def __repr__(self):
        return f"<Incubate {self.name}>"
