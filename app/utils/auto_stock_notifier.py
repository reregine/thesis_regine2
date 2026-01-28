# app/utils/auto_stock_notifier.py
import logging
import atexit
from datetime import datetime, timedelta
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app import db
from .stock_monitor import StockMonitor
from .email_sender import EmailSender

logger = logging.getLogger(__name__)

class AutoStockNotifier:
    """Automatically send email notifications for low stock with built-in scheduler"""
    
    def __init__(self):
        self.last_check_time = None
        self.sent_notifications = {}  # product_id -> last_notified_time
        self.scheduler = None
        self.scheduler_running = False
        
    def init_scheduler(self):
        """Initialize and start the scheduler"""
        if self.scheduler_running:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Create scheduler
            self.scheduler = BackgroundScheduler(daemon=True)
            
            # Get check interval from config (default: 1 hour)
            check_interval_minutes = current_app.config.get('STOCK_CHECK_INTERVAL_MINUTES', 60)
            
            # Add job to check stock periodically
            self.scheduler.add_job(
                func=self.check_and_send_notifications,
                trigger=IntervalTrigger(minutes=check_interval_minutes),
                id='auto_stock_check',
                name='Automatic stock notification check',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.scheduler_running = True
            
            logger.info(f"✅ Stock notification scheduler started (checking every {check_interval_minutes} minutes)")
            
            # Register shutdown
            atexit.register(self.shutdown)
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler_running:
            self.scheduler.shutdown()
            self.scheduler_running = False
            logger.info("🛑 Stock notification scheduler stopped")
    
    def start_scheduler(self):
        """Start the scheduler (for manual control)"""
        if not current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
            logger.info("Auto stock notifications are disabled - not starting scheduler")
            return False
        
        if not self.scheduler_running:
            self.init_scheduler()
        return self.scheduler_running
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.shutdown()
    
    def check_and_send_notifications(self):
        """Main method to check stock and send notifications automatically"""
        try:
            # Check if auto notifications are enabled
            if not current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                logger.info("Auto stock notifications are disabled")
                return {'success': False, 'message': 'Auto notifications disabled'}
            
            logger.info("🔍 Checking for low stock products...")
            
            # Get all low stock products
            low_stock_products = StockMonitor.check_low_stock_products()
            
            if not low_stock_products:
                logger.info("✅ No low stock products found")
                return {'success': True, 'message': 'No low stock products', 'notifications_sent': 0}
            
            logger.info(f"⚠️ Found {len(low_stock_products)} low stock products")
            
            # Check cooldown period
            cooldown_hours = current_app.config.get('NOTIFICATION_COOLDOWN_HOURS', 24)
            now = datetime.utcnow()
            
            notifications_sent = 0
            failed_notifications = 0
            sent_to_incubatees = []
            
            for product in low_stock_products:
                product_id = product['product_id']
                
                # Check if we should send notification (cooldown period)
                last_notified = self.sent_notifications.get(product_id)
                if last_notified:
                    hours_since = (now - last_notified).total_seconds() / 3600
                    if hours_since < cooldown_hours:
                        logger.debug(f"Skipping notification for product {product_id} - cooldown active")
                        continue
                
                # Send notification to incubatee
                if product.get('email'):
                    logger.info(f"📧 Sending low stock notification to {product['email']}")
                    
                    success = EmailSender.send_low_stock_notification(product)
                    
                    if success:
                        notifications_sent += 1
                        self.sent_notifications[product_id] = now
                        sent_to_incubatees.append(product['incubatee_name'])
                        logger.info(f"✅ Notification sent for product {product_id}")
                    else:
                        failed_notifications += 1
                        logger.error(f"❌ Failed to send notification for product {product_id}")
                else:
                    logger.warning(f"No email found for incubatee {product['incubatee_name']}")
            
            # Send summary to admin if notifications were sent
            if notifications_sent > 0:
                self.send_admin_summary(low_stock_products, notifications_sent, sent_to_incubatees)
            
            self.last_check_time = now
            
            result = {
                'success': True,
                'message': f'Sent {notifications_sent} notifications',
                'notifications_sent': notifications_sent,
                'failed_notifications': failed_notifications,
                'total_low_stock': len(low_stock_products),
                'check_time': now.isoformat(),
                'scheduler_running': self.scheduler_running
            }
            
            logger.info(f"✅ Auto stock check completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in auto stock notifier: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_admin_summary(self, low_stock_products, notifications_sent, sent_to_incubatees):
        """Send summary email to admin"""
        try:
            admin_email = current_app.config.get('ADMIN_EMAIL')
            if not admin_email:
                logger.warning("No admin email configured for summary")
                return False
            
            from .email_templates import EmailTemplates
            
            subject = f"📊 Low Stock Report: {len(low_stock_products)} Products Need Attention"
            
            # Group by severity
            critical_products = [p for p in low_stock_products if p['current_stock'] <= 3]
            low_products = [p for p in low_stock_products if p['current_stock'] > 3 and p['current_stock'] <= 10]
            
            # Create list of notified incubatees
            notified_incubatees = ", ".join(set(sent_to_incubatees)) if sent_to_incubatees else "None"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #f0ad4e; color: white; padding: 20px; text-align: center; }}
                    .summary {{ padding: 20px; background-color: #f9f9f9; }}
                    .product-list {{ margin: 20px 0; }}
                    .product-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
                    .critical {{ background-color: #f2dede; border-left: 4px solid #d9534f; }}
                    .low {{ background-color: #fcf8e3; border-left: 4px solid #f0ad4e; }}
                    .count {{ font-size: 24px; font-weight: bold; }}
                    .success {{ color: #28a745; }}
                    .warning {{ color: #dc3545; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 ATBI Low Stock Report</h1>
                        <p>Automated Stock Monitoring System</p>
                    </div>
                    
                    <div class="summary">
                        <h2>Summary</h2>
                        <p><span class="count">{len(low_stock_products)}</span> products are low on stock</p>
                        <p><span class="count success">{notifications_sent}</span> email notifications sent to incubatees</p>
                        <p><span class="count warning">{len(critical_products)}</span> critical products (≤ 3 units)</p>
                        <p><strong>Notified Incubatees:</strong> {notified_incubatees}</p>
                        <p>Check time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    </div>
                    
                    <div class="product-list">
                        <h3>Critical Products (≤ 3 units)</h3>
                        {"".join([self._format_product_html(p, 'critical') for p in critical_products[:5]])}
                        
                        <h3>Low Products (4-10 units)</h3>
                        {"".join([self._format_product_html(p, 'low') for p in low_products[:5]])}
                        
                        {f'<p>... and {len(low_stock_products) - 10} more products</p>' if len(low_stock_products) > 10 else ''}
                    </div>
                    
                    <div style="padding: 20px; text-align: center; background-color: #f5f5f5; margin-top: 20px;">
                        <p>This is an automated report from ATBI Stock Monitoring System.</p>
                        <p><a href="{current_app.config.get('BASE_URL', 'http://localhost:5000')}/admin">View in Admin Panel</a></p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            ATBI Low Stock Report
            =====================
            
            SUMMARY:
            - Total low stock products: {len(low_stock_products)}
            - Notifications sent: {notifications_sent}
            - Critical products (≤ 3 units): {len(critical_products)}
            - Low products (4-10 units): {len(low_products)}
            - Notified incubatees: {notified_incubatees}
            
            Check time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            
            This is an automated report from ATBI Stock Monitoring System.
            """
            
            success = EmailSender.send_email(
                to_email=admin_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                logger.info("✅ Admin summary email sent successfully")
            else:
                logger.error("❌ Failed to send admin summary email")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending admin summary: {str(e)}")
            return False
    
    def _format_product_html(self, product, severity):
        """Format product HTML for admin email"""
        severity_class = 'critical' if severity == 'critical' else 'low'
        stock_status = "🔥 CRITICAL" if severity == 'critical' else "⚠️ LOW"
        
        return f"""
        <div class="product-item {severity_class}">
            <strong>{product['product_name']}</strong> ({product['stock_no']})<br>
            Incubatee: {product['incubatee_name']}<br>
            Current Stock: <strong>{product['current_stock']}</strong> units ({stock_status})<br>
            Email: {product['email'] or 'No email available'}
        </div>
        """
    
    def get_status(self):
        """Get current status of the notifier"""
        return {
            'scheduler_running': self.scheduler_running,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'sent_notifications_count': len(self.sent_notifications),
            'auto_notifications_enabled': current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True),
            'check_interval_minutes': current_app.config.get('STOCK_CHECK_INTERVAL_MINUTES', 60),
            'cooldown_hours': current_app.config.get('NOTIFICATION_COOLDOWN_HOURS', 24),
            'low_stock_threshold': current_app.config.get('LOW_STOCK_THRESHOLD', 10)
        }

# Singleton instance
_auto_notifier = None

def get_auto_notifier():
    """Get or create auto notifier instance"""
    global _auto_notifier
    if _auto_notifier is None:
        _auto_notifier = AutoStockNotifier()
    return _auto_notifier

def check_and_send_auto_notifications():
    """Convenience function to check and send notifications"""
    notifier = get_auto_notifier()
    return notifier.check_and_send_notifications()

def init_auto_notifier(app):
    """Initialize auto notifier with Flask app"""
    notifier = get_auto_notifier()
    
    # Start scheduler if auto notifications are enabled
    if app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
        with app.app_context():
            notifier.start_scheduler()
    
    return notifier