# app/models/shop.py
from ..models.admin import IncubateeProduct
from sqlalchemy import or_
from ..extension import db


class Shop:
    """Handles shop-related queries using the incubatee_products table."""
    @staticmethod
    def get_all_products():
        """Return all products sorted by newest first."""
        return (
            IncubateeProduct.query
            .order_by(IncubateeProduct.added_on.desc())
            .all())

    @staticmethod
    def search_products(keyword):
        """Search by name, products, category, or details."""
        if not keyword:
            return Shop.get_all_products()

        search = f"%{keyword.lower()}%"
        return (
            IncubateeProduct.query.filter(
                or_(db.func.lower(IncubateeProduct.name).like(search),db.func.lower(IncubateeProduct.products).like(search),db.func.lower(IncubateeProduct.category).like(search),db.func.lower(IncubateeProduct.details).like(search),)).order_by(IncubateeProduct.added_on.desc()).all())
