# app/utils/stock_scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from flask import current_app
from .stock_notification_manager import StockNotificationManager

logger = logging.getLogger(__name__)

class StockNotificationScheduler:
    """Scheduler for automatic stock notifications"""
    
    def __init__(self):
        self.scheduler = None
        self.notification_manager = StockNotificationManager()
        self.first_run_done = False
    
    def start(self, app):
        """Start the scheduler with 5-minute interval, sending 2 emails"""
        try:
            if self.scheduler and self.scheduler.running:
                logger.info("Scheduler already running")
                return
            
            self.scheduler = BackgroundScheduler()
            
            # Schedule the FIRST email notification at 0 minutes (immediate start)
            self.scheduler.add_job(
                id='first_stock_check',
                func=self.send_first_notification_job,
                trigger='interval',
                minutes=5,  # 5-minute interval
                args=[app],
                replace_existing=True,
                next_run_time=datetime.now()  # Start immediately
            )
            
            # Schedule the SECOND email notification at 4 minutes (1 minute before next cycle)
            self.scheduler.add_job(
                id='second_stock_check',
                func=self.send_second_notification_job,
                trigger='interval',
                minutes=5,  # 5-minute interval
                args=[app],
                replace_existing=True,
                next_run_time=datetime.now()  # Start immediately
            )
            
            self.scheduler.start()
            logger.info("✅ Stock notification scheduler started")
            logger.info("📧 Email notifications will send 2 times within each 5-minute interval")
            logger.info("   - First email at 0 minute mark")
            logger.info("   - Second email at 4 minute mark")
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
    
    def send_first_notification_job(self, app):
        """First notification job - runs at minute 0 of each 5-minute cycle"""
        with app.app_context():
            logger.info(f"📧 FIRST NOTIFICATION - Running at {datetime.now().strftime('%H:%M:%S')}")
            
            if current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                try:
                    result = self.notification_manager.auto_check_low_stock()
                    logger.info(f"✅ First notification sent: {result.get('message', 'No result')}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Error in first notification: {str(e)}")
                    return {'error': str(e)}
            else:
                logger.info("⏸️ Auto notifications disabled")
                return {'auto_check': False, 'message': 'Auto notifications disabled'}
    
    def send_second_notification_job(self, app):
        """Second notification job - runs at minute 4 of each 5-minute cycle"""
        with app.app_context():
            # Wait 4 minutes before sending second notification
            # This is handled by the job starting immediately and then running every 5 minutes
            # The first job runs at minute 0, this runs at minute 4
            
            import time
            # We'll wait 4 minutes after the first run
            if not self.first_run_done:
                time.sleep(240)  # Wait 4 minutes (240 seconds)
                self.first_run_done = True
            
            logger.info(f"📧 SECOND NOTIFICATION - Running at {datetime.now().strftime('%H:%M:%S')}")
            
            if current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True):
                try:
                    # Add a small delay to ensure it's 4 minutes after the first
                    result = self.notification_manager.auto_check_low_stock()
                    logger.info(f"✅ Second notification sent: {result.get('message', 'No result')}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Error in second notification: {str(e)}")
                    return {'error': str(e)}
            else:
                logger.info("⏸️ Auto notifications disabled")
                return {'auto_check': False, 'message': 'Auto notifications disabled'}
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️ Stock notification scheduler stopped")
    
    def manual_trigger(self, app):
        """Manually trigger a check (for testing or immediate needs)"""
        with app.app_context():
            logger.info("🔧 Manually triggering stock check")
            return self.send_first_notification_job(app)

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