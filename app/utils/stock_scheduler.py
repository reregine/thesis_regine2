import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from flask import current_app
from .stock_notification_manager import StockNotificationManager

logger = logging.getLogger(__name__)

class StockNotificationScheduler:
    """Scheduler for automatic stock notifications"""
    
    def __init__(self):
        self.scheduler = None
        self.notification_manager = StockNotificationManager()
    
    def start(self, app):
        """Start the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                logger.info("Scheduler already running")
                return
            
            self.scheduler = BackgroundScheduler()
            
            # Schedule to run every day at 9 AM and 5 PM
            # You can adjust this schedule as needed
            self.scheduler.add_job(
                id='auto_stock_check',
                func=self.auto_check_job,
                trigger=CronTrigger(hour='9,17', minute='0'),
                args=[app],
                replace_existing=True
            )
            
            # Also run every hour for testing/demo
            self.scheduler.add_job(
                id='hourly_stock_check',
                func=self.auto_check_job,
                trigger='interval',
                hours=1,
                args=[app],
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("✅ Stock notification scheduler started")
            logger.info("📧 Auto-notifications will run every hour and at 9AM/5PM daily")
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️ Stock notification scheduler stopped")
    
    def auto_check_job(self, app):
        """Job function to be called by scheduler"""
        with app.app_context():
            logger.info(f"🔄 Running scheduled stock check at {datetime.now()}")
            
            if current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                result = self.notification_manager.auto_check_low_stock()
                logger.info(f"✅ Scheduled check completed: {result.get('message', 'No result')}")
                return result
            else:
                logger.info("⏸️ Auto notifications disabled, skipping scheduled check")
                return {'auto_check': False, 'message': 'Auto notifications disabled'}
    
    def manual_trigger(self, app):
        """Manually trigger a check (for testing or immediate needs)"""
        with app.app_context():
            logger.info("🔧 Manually triggering stock check")
            return self.auto_check_job(app)

# Global scheduler instance
stock_scheduler = StockNotificationScheduler()

def init_stock_scheduler(app):
    """Initialize the stock notification scheduler"""
    # Only start if auto notifications are enabled
    if app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
        stock_scheduler.start(app)
        return True
    else:
        logger.info("⏸️ Auto stock notifications disabled in config")
        return False