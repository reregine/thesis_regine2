
from datetime import datetime, timedelta
from app import db
from app.models.reservation import Reservation
from app.models.admin import IncubateeProduct

class ReservationHelpers:
    """Helper functions for reservation-related calculations"""
    
    @staticmethod
    def get_product_sales_stats(product_id: int, days_back: int = 7) -> dict:
        """
        Get comprehensive sales statistics for a product
        """
        try:
            # Get date threshold
            since_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get product info
            product = IncubateeProduct.query.get(product_id)
            if not product:
                return {}
            
            # Query for different reservation statuses
            stats = {
                'product_name': product.name,
                'stock_no': product.stock_no,
                'current_stock': product.stock_amount,
                
                # Completed reservations (sold and picked up)
                'sold_last_7_days': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status == 'completed',
                    Reservation.completed_at >= since_date
                ).scalar() or 0,
                
                # Currently pending approval
                'pending_approval': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status == 'pending'
                ).scalar() or 0,
                
                # Approved but not yet picked up
                'approved_not_picked': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status == 'approved',
                    Reservation.completed_at.is_(None)
                ).scalar() or 0,
                
                # Total pending sales (pending + approved)
                'total_pending_sales': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status.in_(['pending', 'approved'])
                ).scalar() or 0,
                
                # All-time completed sales
                'total_sold': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status == 'completed'
                ).scalar() or 0,
                
                # Recently rejected (last 7 days)
                'rejected_last_7_days': db.session.query(
                    db.func.sum(Reservation.quantity)
                ).filter(
                    Reservation.product_id == product_id,
                    Reservation.status == 'rejected',
                    Reservation.rejected_at >= since_date
                ).scalar() or 0,
            }
            
            # Calculate effective available stock
            stats['effective_available'] = max(0, stats['current_stock'] - stats['total_pending_sales'])
            
            # Calculate stock depletion rate (units per week)
            stats['depletion_rate'] = stats['sold_last_7_days'] / 7 if stats['sold_last_7_days'] > 0 else 0
            
            # Calculate days of stock remaining
            if stats['depletion_rate'] > 0:
                stats['days_remaining'] = stats['effective_available'] / stats['depletion_rate']
            else:
                stats['days_remaining'] = 999  # Infinite if no sales
            
            # Determine urgency level
            if stats['effective_available'] <= 3:
                stats['urgency'] = 'critical'
            elif stats['effective_available'] <= 10:
                stats['urgency'] = 'low'
            else:
                stats['urgency'] = 'normal'
            
            # Calculate conversion rate (approved vs total reservations)
            total_reservations = stats['total_pending_sales'] + stats['total_sold'] + stats['rejected_last_7_days']
            if total_reservations > 0:
                stats['conversion_rate'] = (stats['total_sold'] / total_reservations) * 100
            else:
                stats['conversion_rate'] = 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting product sales stats: {str(e)}")
            return {}