
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app
from ..utils.stock_monitor import StockMonitor
from ..utils.stock_notification_manager import StockNotificationManager
from ..utils.email_sender import EmailSender
from app.models.email_log import EmailLog

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')

@stock_bp.route('/low-stock-check', methods=['GET'])
def check_low_stock():
    """Check for low stock products"""
    try:
        # Get low stock products
        low_stock_products = StockMonitor.check_low_stock_products()
        
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "low_stock_threshold": StockMonitor.LOW_STOCK_THRESHOLD,
            "total_low_stock": len(low_stock_products),
            "products": low_stock_products,
            "auto_notifications_enabled": current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True)
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error in low stock check: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/send-notifications', methods=['POST'])
def send_low_stock_notifications():
    """Trigger low stock notifications"""
    try:
        notification_manager = StockNotificationManager()
        result = notification_manager.check_and_notify_low_stock()
        
        return jsonify({
            "success": True,
            "message": "Low stock notification process completed",
            "result": result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error sending notifications: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/email-logs', methods=['GET'])
def get_email_logs():
    """Get email logs with filters"""
    try:
        # Get query parameters
        days = request.args.get('days', default=1, type=int)
        email_type = request.args.get('type')
        status = request.args.get('status')
        
        # Build query
        query = EmailLog.query
        query = query.filter(EmailLog.sent_at >= datetime.utcnow() - timedelta(days=days))
        
        if email_type:
            query = query.filter_by(email_type=email_type)
        
        if status:
            query = query.filter_by(status=status)
        
        # Order by most recent
        logs = query.order_by(EmailLog.sent_at.desc()).limit(100).all()
        
        return jsonify({
            "success": True,
            "count": len(logs),
            "logs": [log.to_dict() for log in logs]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting email logs: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/email-stats', methods=['GET'])
def get_email_stats():
    """Get email statistics"""
    try:
        hours = request.args.get('hours', default=24, type=int)
        stats = EmailSender.get_email_stats(hours)
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting email stats: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/test-dual-schedule', methods=['POST'])
def test_dual_schedule():
    """Test the dual email schedule"""
    try:
        from ..utils.auto_stock_notifier import get_auto_notifier
        
        notifier = get_auto_notifier()
        
        # Send both batches immediately for testing
        result1 = notifier.send_first_notification_batch()
        result2 = notifier.send_second_notification_batch()
        
        return jsonify({
            "success": True,
            "message": "Dual schedule test completed",
            "batch_1": result1,
            "batch_2": result2,
            "interval_minutes": current_app.config.get('EMAIL_INTERVAL_MINUTES', 5)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing dual schedule: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/scheduler-status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status"""
    try:
        from ..utils.auto_stock_notifier import get_auto_notifier
        
        notifier = get_auto_notifier()
        status = notifier.get_status()
        
        return jsonify({
            "success": True,
            "status": status
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500