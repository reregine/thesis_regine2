
import logging
from datetime import datetime
from typing import List, Dict, Any
from flask import current_app
from app import db
from ..models.admin import IncubateeProduct, Incubatee

logger = logging.getLogger(__name__)

class StockMonitor:
    """Monitor and handle low stock notifications"""
    
    LOW_STOCK_THRESHOLD = 10  # Stock level threshold for notifications
    
    @classmethod
    def check_low_stock_products(cls) -> List[Dict[str, Any]]:
        """
        Find all products with stock below threshold
        Returns list of products with incubatee info
        """
        try:
            # Query products with low stock and related incubatee info
            low_stock_products = db.session.query(
                IncubateeProduct, Incubatee
            ).join(
                Incubatee, IncubateeProduct.incubatee_id == Incubatee.incubatee_id
            ).filter(
                IncubateeProduct.stock_amount <= cls.LOW_STOCK_THRESHOLD,
                Incubatee.is_approved == True
            ).all()
            
            products_list = []
            for product, incubatee in low_stock_products:
                products_list.append({
                    'product_id': product.product_id,  # Ensure product_id is included
                    'product_name': product.name,
                    'stock_no': product.stock_no,
                    'current_stock': product.stock_amount,
                    'threshold': cls.LOW_STOCK_THRESHOLD,
                    'incubatee_id': incubatee.incubatee_id,
                    'incubatee_name': f"{incubatee.first_name} {incubatee.last_name}",
                    'company_name': incubatee.company_name,
                    'email': incubatee.email,
                    'phone': incubatee.phone_number,
                    'last_checked': datetime.utcnow()
                })
            
            logger.info(f"Found {len(products_list)} products with low stock")
            return products_list
            
        except Exception as e:
            logger.error(f"Error checking low stock products: {str(e)}")
            return []
    
    @classmethod
    def get_product_stock_status(cls, product_id: int) -> Dict[str, Any]:
        """Get stock status for a specific product"""
        try:
            product = IncubateeProduct.query.get(product_id)
            if not product:
                return {'error': 'Product not found'}
            
            incubatee = Incubatee.query.get(product.incubatee_id)
            
            return {
                'product_id': product.product_id,
                'product_name': product.name,
                'current_stock': product.stock_amount,
                'is_low_stock': product.stock_amount <= cls.LOW_STOCK_THRESHOLD,
                'threshold': cls.LOW_STOCK_THRESHOLD,
                'incubatee_id': product.incubatee_id,
                'incubatee_email': incubatee.email if incubatee else None,
                'last_updated': product.updated_at
            }
        except Exception as e:
            logger.error(f"Error getting product stock status: {str(e)}")
            return {'error': str(e)}