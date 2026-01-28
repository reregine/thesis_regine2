# File: app/routes/stock_routes.py
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app
from ..utils.stock_monitor import StockMonitor
from ..utils.stock_notification_manager import StockNotificationManager

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

@stock_bp.route('/auto-check', methods=['POST'])
def auto_check_stock():
    """Auto-check low stock"""
    try:
        notification_manager = StockNotificationManager()
        result = notification_manager.auto_check_low_stock()
        
        return jsonify({
            "success": True,
            "message": "Auto stock check completed",
            "result": result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in auto stock check: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/test-email', methods=['POST'])
def test_email():
    """Test email sending"""
    try:
        from app.utils.email_sender import EmailSender
        
        test_data = {
            'product_name': 'Test Product',
            'current_stock': 5,
            'threshold': StockMonitor.LOW_STOCK_THRESHOLD,
            'incubatee_name': 'Test Incubatee',
            'email': current_app.config.get('ADMIN_EMAIL') or current_app.config.get('SMTP_USERNAME')
        }
        
        if not test_data['email']:
            return jsonify({"success": False, "error": "No email configured"}), 400
        
        success = EmailSender.send_low_stock_notification(test_data)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Test email sent to {test_data['email']}"
            })
        else:
            return jsonify({"success": False, "error": "Failed to send test email"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in test email: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@stock_bp.route('/settings', methods=['GET'])
def get_notification_settings():
    """Get current notification settings"""
    try:
        return jsonify({
            "success": True,
            "settings": {
                "low_stock_threshold": StockMonitor.LOW_STOCK_THRESHOLD,
                "notification_cooldown_hours": 24,  # From StockNotificationManager
                "auto_notifications_enabled": current_app.config.get('AUTO_STOCK_NOTIFICATIONS', True),
                "smtp_configured": bool(
                    current_app.config.get('SMTP_USERNAME') and 
                    current_app.config.get('SMTP_PASSWORD')
                ),
                "admin_email": current_app.config.get('ADMIN_EMAIL')
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting settings: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500