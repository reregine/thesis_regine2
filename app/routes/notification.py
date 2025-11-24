from flask import Blueprint, request, jsonify, session, current_app, render_template, redirect, url_for
from ..extension import db
from ..models.notification import Notification
from ..models.reservation import Reservation
from ..models.admin import IncubateeProduct
from datetime import datetime, timezone

# Use notif_bp to match your existing route
notif_bp = Blueprint("notification", __name__, url_prefix="/notifications")

class NotificationManager:
    @staticmethod
    def create_reservation_notification(user_id, reservation_id, status, reason=None):
        """Create notification for reservation status changes"""
        try:
            reservation = Reservation.query.get(reservation_id)
            if not reservation:
                return False
            
            product = IncubateeProduct.query.get(reservation.product_id)
            product_name = product.name if product else "Unknown Product"
            
            notification_data = NotificationManager._get_reservation_notification_data(
                status, product_name, reservation.quantity, reason
            )
            
            notification = Notification(
                user_id=user_id,
                type='reservation',
                title=notification_data['title'],
                message=notification_data['message'],
                related_id=reservation_id,
                related_type='reservation',
                status='unread'
            )
            
            db.session.add(notification)
            db.session.commit()
            
            current_app.logger.info(f"Created {status} notification for user {user_id}, reservation {reservation_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating reservation notification: {e}")
            return False
    
    @staticmethod
    def _get_reservation_notification_data(status, product_name, quantity, reason=None):
        """Get notification content based on reservation status"""
        base_data = {
            'pending': {
                'title': '🕒 Reservation Submitted',
                'message': f'Your reservation for {quantity} {product_name} has been submitted and is pending approval. Status will update in 2 minutes.'
            },
            'approved': {
                'title': '✅ Reservation Approved!',
                'message': f'Great news! Your reservation for {quantity} {product_name} has been approved. You can now proceed to pick up your items.'
            },
            'completed': {
                'title': '🎉 Pickup Confirmed!',
                'message': f'Thank you! Pickup for {quantity} {product_name} has been confirmed. We hope you enjoy your purchase!'
            },
            'rejected': {
                'title': '❌ Reservation Rejected',
                'message': f'Your reservation for {quantity} {product_name} was rejected.'
            },
            'cancelled': {
                'title': '🗑️ Reservation Cancelled',
                'message': f'Your reservation for {quantity} {product_name} has been cancelled.'
            }
        }
        
        data = base_data.get(status, base_data['pending']).copy()
        
        # Add reason for rejected reservations
        if status == 'rejected' and reason:
            data['message'] += f" Reason: {reason}"
        
        return data
    
    @staticmethod
    def create_system_notification(user_id, title, message):
        """Create system notification"""
        try:
            notification = Notification(
                user_id=user_id,
                type='system',
                title=title,
                message=message,
                status='unread'
            )
            
            db.session.add(notification)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating system notification: {e}")
            return False

# Template Route (for HTML page)
@notif_bp.route("/")
def list_notifications():
    """Render notifications page"""
    # ✅ Check if user is logged in
    if not session.get("user_logged_in") and not session.get("admin_logged_in"):
        return redirect(url_for("login.login"))  # back to login page
    
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login.login"))
    
    # Get notifications for the current user
    notifications = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.created_at.desc())\
        .all()
    
    return render_template("notification/list.html", 
                         notifications=notifications,
                         user_logged_in=session.get("user_logged_in"),
                         admin_logged_in=session.get("admin_logged_in"))

# API Routes for JavaScript functionality
@notif_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user_notifications(user_id):
    """Get all notifications for a user (API endpoint)"""
    try:
        # Check if user is authorized
        if session.get('user_id') != user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        notifications = Notification.query.filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc())\
            .all()
        
        return jsonify({
            "success": True,
            "notifications": [notification.to_dict() for notification in notifications]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching notifications: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@notif_bp.route("/unread-count/<int:user_id>", methods=["GET"])
def get_unread_count(user_id):
    """Get count of unread notifications"""
    try:
        if session.get('user_id') != user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        count = Notification.query.filter_by(
            user_id=user_id, 
            status='unread'
        ).count()
        
        return jsonify({
            "success": True,
            "unread_count": count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching unread count: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@notif_bp.route("/mark-read/<int:notification_id>", methods=["POST"])
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"success": False, "message": "Notification not found"}), 404
        
        # Check authorization
        if session.get('user_id') != notification.user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        notification.mark_as_read()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Notification marked as read"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking notification as read: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@notif_bp.route("/mark-all-read/<int:user_id>", methods=["POST"])
def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    try:
        if session.get('user_id') != user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        notifications = Notification.query.filter_by(
            user_id=user_id, 
            status='unread'
        ).all()
        
        for notification in notifications:
            notification.mark_as_read()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"All notifications marked as read",
            "marked_count": len(notifications)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@notif_bp.route("/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    """Delete a notification"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"success": False, "message": "Notification not found"}), 404
        
        # Check authorization
        if session.get('user_id') != notification.user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Notification deleted"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting notification: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

@notif_bp.route("/clear-all/<int:user_id>", methods=["DELETE"])
def clear_all_notifications(user_id):
    """Clear all notifications for a user"""
    try:
        if session.get('user_id') != user_id and not session.get('admin_logged_in'):
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        
        deleted_count = Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"All notifications cleared",
            "deleted_count": deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing all notifications: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

# Utility function to be called from reservation routes
def notify_reservation_status_change(reservation_id, status, reason=None):
    """Utility function to be called when reservation status changes"""
    try:
        reservation = Reservation.query.get(reservation_id)
        if reservation:
            return NotificationManager.create_reservation_notification(
                reservation.user_id, 
                reservation_id, 
                status, 
                reason
            )
        return False
    except Exception as e:
        current_app.logger.error(f"Error in notify_reservation_status_change: {e}")
        return False