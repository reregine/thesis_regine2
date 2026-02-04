
import logging
import atexit
from datetime import datetime
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app import db
from .stock_monitor import StockMonitor
from .email_sender import EmailSender

logger = logging.getLogger(__name__)

class AutoStockNotifier:
    """Automatically send email notifications for low stock with built-in scheduler"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutoStockNotifier, cls).__new__(cls)
            cls._instance.scheduler = None
            cls._instance.scheduler_running = False
            cls._instance.app = None
        return cls._instance
    
    def init_scheduler(self, app):
        """Initialize and start the scheduler with dual email schedule"""
        if self.scheduler_running:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Store app reference
            self.app = app
            
            # Create scheduler
            self.scheduler = BackgroundScheduler(daemon=True)
            
            # Get interval from config (default: 5 minutes for thesis demo)
            check_interval_minutes = app.config.get('STOCK_CHECK_INTERVAL_MINUTES', 5)
            
            # Schedule both jobs using lambda functions that include app context
            self.scheduler.add_job(
                func=self._send_batch_with_context,
                trigger=IntervalTrigger(minutes=check_interval_minutes),
                args=[app, 1],  # Pass app and batch number
                id='first_notification_batch',
                name='First notification batch',
                replace_existing=True
            )
            
            self.scheduler.add_job(
                func=self._send_batch_with_context,
                trigger=IntervalTrigger(minutes=check_interval_minutes),
                args=[app, 2],  # Pass app and batch number
                id='second_notification_batch',
                name='Second notification batch',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            self.scheduler_running = True
            
            logger.info(f"✅ Dual notification scheduler started ({check_interval_minutes}-minute interval)")
            logger.info("📧 First notification at minute 1, second at minute 4 of each interval")
            
            # Register shutdown
            atexit.register(self.shutdown)
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
    
    def _send_batch_with_context(self, app, batch_number):
        """Send notification batch with proper Flask context"""
        with app.app_context():
            try:
                if batch_number == 1:
                    return self._send_notification_batch(batch_number=1)
                else:
                    return self._send_notification_batch(batch_number=2)
            except Exception as e:
                logger.error(f"❌ Error in batch {batch_number}: {str(e)}")
                return {'success': False, 'error': str(e), 'batch': batch_number}
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler and self.scheduler_running:
            self.scheduler.shutdown()
            self.scheduler_running = False
            logger.info("🛑 Stock notification scheduler stopped")
    
    def _send_notification_batch(self, batch_number=1):
        """Send a batch of notifications"""
        try:
            # Check if auto notifications are enabled
            if not current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                logger.info("Auto stock notifications are disabled")
                return {'success': False, 'message': 'Auto notifications disabled', 'batch': batch_number}
            
            logger.info(f"🔍 Batch {batch_number}: Checking for low stock products...")
            
            # Get all low stock products
            low_stock_products = StockMonitor.check_low_stock_products()
            
            if not low_stock_products:
                logger.info(f"✅ Batch {batch_number}: No low stock products found")
                return {
                    'success': True, 
                    'message': 'No low stock products', 
                    'notifications_sent': 0,
                    'batch': batch_number
                }
            
            logger.info(f"⚠️ Batch {batch_number}: Found {len(low_stock_products)} low stock products")
            
            # For demo mode, limit the number of notifications
            demo_mode = current_app.config.get('DEMO_MODE', False)
            max_notifications = current_app.config.get('DEMO_NOTIFICATIONS_PER_BATCH', 2)
            
            notifications_sent = 0
            failed_notifications = 0
            sent_to_incubatees = []
            
            for index, product in enumerate(low_stock_products):
                # Limit notifications in demo mode
                if demo_mode and notifications_sent >= max_notifications:
                    logger.info(f"📊 Demo mode: Sent {max_notifications} emails, stopping for batch {batch_number}")
                    break
                
                product_id = product['product_id']
                
                # Check if we should send based on interval (using EmailSender's logic)
                should_send = EmailSender.should_send_email(
                    product.get('incubatee_id'),
                    product_id,
                    interval_minutes=current_app.config.get('EMAIL_INTERVAL_MINUTES', 5)
                )
                
                if not should_send:
                    logger.debug(f"Batch {batch_number}: Skipping product {product_id} - within interval")
                    continue
                
                # Send notification to incubatee
                if product.get('email'):
                    logger.info(f"📧 Batch {batch_number}: Sending notification to {product['email']}")
                    
                    success = EmailSender.send_low_stock_notification(product)
                    
                    if success:
                        notifications_sent += 1
                        sent_to_incubatees.append(product['incubatee_name'])
                        logger.info(f"✅ Batch {batch_number}: Notification sent for product {product_id}")
                    else:
                        failed_notifications += 1
                        logger.error(f"❌ Batch {batch_number}: Failed to send notification for product {product_id}")
                else:
                    logger.warning(f"Batch {batch_number}: No email for {product['incubatee_name']}")
            
            # Send admin summary if notifications were sent
            admin_notified = False
            if notifications_sent > 0 and batch_number == 1:  # Only send admin summary from first batch
                admin_products = [p for p in low_stock_products if p.get('email')]
                if admin_products and admin_products[:max_notifications]:  # Limit for demo
                    admin_success = EmailSender.send_admin_notification(admin_products[:max_notifications])
                    admin_notified = admin_success
            
            result = {
                'success': True,
                'message': f'Batch {batch_number}: Sent {notifications_sent} notifications',
                'batch': batch_number,
                'notifications_sent': notifications_sent,
                'failed_notifications': failed_notifications,
                'total_low_stock': len(low_stock_products),
                'admin_notified': admin_notified,
                'check_time': datetime.utcnow().isoformat(),
                'scheduler_running': self.scheduler_running,
                'demo_mode': demo_mode
            }
            
            logger.info(f"✅ Batch {batch_number} completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in notification batch {batch_number}: {str(e)}")
            return {'success': False, 'error': str(e), 'batch': batch_number}
    
    def get_status(self):
        """Get current status of the notifier"""
        if not self.app:
            return {'scheduler_running': False, 'error': 'No app context'}
        
        with self.app.app_context():
            jobs = []
            if self.scheduler and self.scheduler_running:
                jobs = self.scheduler.get_jobs()
            
            return {
                'scheduler_running': self.scheduler_running,
                'jobs': [job.id for job in jobs],
                'next_run_times': [str(job.next_run_time) for job in jobs] if jobs else [],
                'auto_notifications_enabled': current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True),
                'check_interval_minutes': current_app.config.get('STOCK_CHECK_INTERVAL_MINUTES', 5),
                'email_interval_minutes': current_app.config.get('EMAIL_INTERVAL_MINUTES', 5),
                'low_stock_threshold': current_app.config.get('LOW_STOCK_THRESHOLD', 10),
                'demo_mode': current_app.config.get('DEMO_MODE', False)
            }

def get_auto_notifier():
    """Get or create auto notifier instance"""
    return AutoStockNotifier()

def init_auto_notifier(app):
    """Initialize auto notifier with Flask app"""
    notifier = get_auto_notifier()
    
    # Start scheduler if auto notifications are enabled
    if app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
        notifier.init_scheduler(app)
        print(f"✅ Auto stock notifier initialized")
        print(f"📧 Email interval: {app.config.get('EMAIL_INTERVAL_MINUTES', 5)} minutes")
        print(f"🔥 Demo mode: {'ON' if app.config.get('DEMO_MODE', False) else 'OFF'}")
        return True
    else:
        print("⏸️ Auto stock notifications disabled in config")
        return False