# app/utils/stock_notification_manager.py
import logging
from datetime import datetime
from typing import Dict, Any
from .stock_monitor import StockMonitor
from .email_sender import EmailSender

logger = logging.getLogger(__name__)

class StockNotificationManager:
    """Manage stock notifications and prevent duplicate alerts"""
    
    NOTIFICATION_COOLDOWN_MINUTES = 5  # Changed to 5 minutes for thesis demo
    
    def __init__(self):
        self.sent_notifications = {}  # In production, store in database or Redis
    
    def should_send_notification(self, product_key: str) -> bool:
        """Check if we should send notification based on cooldown - relaxed for demo"""
        last_notified = self.sent_notifications.get(product_key)
        
        if not last_notified:
            return True
        
        minutes_since = (datetime.utcnow() - last_notified).total_seconds() / 60
        
        # For thesis demo, allow sending every 5 minutes
        return minutes_since >= self.NOTIFICATION_COOLDOWN_MINUTES
    
    def mark_notification_sent(self, product_key: str):
        """Record that a notification was sent"""
        self.sent_notifications[product_key] = datetime.utcnow()
    
    def check_and_notify_low_stock(self) -> Dict[str, Any]:
        """
        Main method to check low stock and send notifications
        Returns summary of actions taken
        """
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_products_checked': 0,
            'low_stock_products': 0,
            'notifications_sent': 0,
            'failed_notifications': 0,
            'details': []
        }
        
        try:
            # Get all low stock products
            low_stock_products = StockMonitor.check_low_stock_products()
            summary['total_products_checked'] = len(low_stock_products)
            summary['low_stock_products'] = len(low_stock_products)
            
            if not low_stock_products:
                summary['message'] = 'No products with low stock found'
                logger.info("✅ No low stock products found")
                return summary
            
            logger.info(f"📊 Found {len(low_stock_products)} low stock products")
            
            # Send notifications
            sent_to_incubatees = set()
            
            for product in low_stock_products:
                product_key = f"{product['product_id']}_{product['incubatee_id']}"
                
                # Always send for demo (bypass cooldown check)
                # Comment out the next 3 lines if you want to re-enable cooldown
                # if not self.should_send_notification(product_key):
                #     logger.info(f"⏸️ Skipping notification for product {product['product_id']} - cooldown active")
                #     continue
                
                # Send notification to incubatee
                if product.get('email'):
                    try:
                        logger.info(f"📧 Attempting to send email to {product['email']} for product {product['product_name']}")
                        
                        success = EmailSender.send_low_stock_notification(product)
                        
                        if success:
                            summary['notifications_sent'] += 1
                            sent_to_incubatees.add(product['incubatee_id'])
                            self.mark_notification_sent(product_key)
                            summary['details'].append({
                                'product_id': product['product_id'],
                                'product_name': product['product_name'],
                                'incubatee_email': product['email'],
                                'status': 'sent',
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            logger.info(f"✅ Low stock notification sent for {product['product_name']} to {product['email']}")
                        else:
                            summary['failed_notifications'] += 1
                            summary['details'].append({
                                'product_id': product['product_id'],
                                'product_name': product['product_name'],
                                'incubatee_email': product['email'],
                                'status': 'failed',
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            logger.error(f"❌ Failed to send notification for {product['product_name']}")
                    except Exception as e:
                        logger.error(f"Error sending notification for product {product['product_id']}: {str(e)}")
                        summary['failed_notifications'] += 1
                        summary['details'].append({
                            'product_id': product['product_id'],
                            'product_name': product['product_name'],
                            'status': 'error',
                            'error': str(e)
                        })
                else:
                    logger.warning(f"No email found for incubatee of product {product['product_name']}")
                    summary['details'].append({
                        'product_id': product['product_id'],
                        'product_name': product['product_name'],
                        'status': 'skipped_no_email',
                        'reason': 'No incubatee email found'
                    })
            
            # Log summary
            logger.info(f"📊 Notification Summary: Sent {summary['notifications_sent']}, Failed {summary['failed_notifications']}")
            
            if summary['notifications_sent'] > 0:
                summary['message'] = f"Successfully sent {summary['notifications_sent']} notifications"
            else:
                summary['message'] = "No notifications were sent"
                
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error in stock notification process: {str(e)}")
            summary['error'] = str(e)
            summary['message'] = f'Error processing notifications: {str(e)}'
            return summary
    
    def auto_check_low_stock(self):
        """
        Auto-check method to be called by scheduler
        This will automatically send notifications without manual intervention
        """
        logger.info("🔄 Auto-checking for low stock products...")
        return self.check_and_notify_low_stock()
        
    @staticmethod
    def trigger_stock_notification_on_update(product_id=None):
        """Trigger stock notification check when stock is updated"""
        from flask import current_app
        
        try:
            if current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                notification_manager = StockNotificationManager()
                
                # If specific product ID is provided, check only if it's low stock
                if product_id:
                    from .stock_monitor import StockMonitor
                    product_status = StockMonitor.get_product_stock_status(product_id)
                    
                    if product_status and not product_status.get('error'):
                        # Check if product is low stock
                        if product_status.get('is_low_stock', False):
                            # Get all low stock products and send notifications
                            notification_manager.check_and_notify_low_stock()
                            current_app.logger.info(f"✅ Triggered stock notification for low stock product {product_id}")
                        else:
                            current_app.logger.info(f"✅ Product {product_id} not low stock, no notification needed")
                else:
                    # Check all products
                    notification_manager.auto_check_low_stock()
                    current_app.logger.info("✅ Triggered stock notification check for all products")
                    
                return True
        except Exception as e:
            current_app.logger.error(f"Error triggering stock notification: {str(e)}")
            return False