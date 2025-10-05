# models/admin.py
from app.extension import db
from datetime import date


class IncubateeProduct(db.Model):
    __tablename__ = "incubatee_products"

    incubatee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    stock_no = db.Column(db.String(50), nullable=False)
    products = db.Column(db.String(150), nullable=False)
    stock_amount = db.Column(db.Integer, nullable=False)
    price_per_stocks = db.Column(db.Numeric(8, 2), nullable=False)
    details = db.Column(db.Text, nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    added_on = db.Column(db.Date, nullable=False, default=date.today)
    image_path = db.Column(db.String(255), nullable=True) 

    def __repr__(self):
        return f"<IncubateeProduct {self.name}>"

