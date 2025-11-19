# app/models/shop.py
from ..models.admin import IncubateeProduct, PricingUnit, Incubatee
from sqlalchemy import or_
from ..extension import db

class Shop:
    """Handles shop-related queries using the incubatee_products table."""
    
    @staticmethod
    def get_all_products():
        """Return all products with pricing details and incubatee info."""
        return (
            IncubateeProduct.query
            .join(PricingUnit, IncubateeProduct.pricing_unit_id == PricingUnit.unit_id)
            .join(Incubatee, IncubateeProduct.incubatee_id == Incubatee.incubatee_id)
            .options(db.joinedload(IncubateeProduct.pricing_unit))
            .options(db.joinedload(IncubateeProduct.incubatee))
            .order_by(IncubateeProduct.added_on.desc())
            .all()
        )

    @staticmethod
    def get_products_by_incubatee(incubatee_id):
        """Get products for a specific incubatee with pricing details."""
        return (
            IncubateeProduct.query
            .join(PricingUnit)
            .join(Incubatee)
            .filter(IncubateeProduct.incubatee_id == incubatee_id)
            .options(db.joinedload(IncubateeProduct.pricing_unit))
            .options(db.joinedload(IncubateeProduct.incubatee))
            .order_by(IncubateeProduct.added_on.desc())
            .all()
        )

    @staticmethod
    def search_products(keyword):
        """Search by name, products, category, or details."""
        if not keyword:
            return Shop.get_all_products()

        search = f"%{keyword.lower()}%"
        return (
            IncubateeProduct.query
            .join(PricingUnit)
            .join(Incubatee)
            .filter(
                or_(
                    db.func.lower(IncubateeProduct.name).like(search),
                    db.func.lower(IncubateeProduct.products).like(search),
                    db.func.lower(IncubateeProduct.category).like(search),
                    db.func.lower(IncubateeProduct.details).like(search),
                    db.func.lower(Incubatee.company_name).like(search)
                )
            )
            .options(db.joinedload(IncubateeProduct.pricing_unit))
            .options(db.joinedload(IncubateeProduct.incubatee))
            .order_by(IncubateeProduct.added_on.desc())
            .all()
        )
        
    @staticmethod
    def get_product_by_id(product_id):
        """Get a specific product by ID with pricing details."""
        return (
            IncubateeProduct.query
            .join(PricingUnit)
            .join(Incubatee)
            .options(db.joinedload(IncubateeProduct.pricing_unit))
            .options(db.joinedload(IncubateeProduct.incubatee))
            .filter_by(product_id=product_id)
            .first()
        )

    @staticmethod
    def get_all_pricing_units():
        """Get all available pricing units."""
        return PricingUnit.query.filter_by(is_active=True).all()
    