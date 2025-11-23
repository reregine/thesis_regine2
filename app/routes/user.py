from flask import Blueprint, request, jsonify, session, current_app
from ..extension import db
from ..models.user import User
from werkzeug.security import generate_password_hash, check_password_hash

user_bp = Blueprint("user_bp", __name__, url_prefix="/user")

@user_bp.route("/current", methods=["GET"])
def get_current_user():
    """Get current user info"""
    try:
        if session.get("user_logged_in"):
            user_id = session.get("user_id")
            username = session.get("username")
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'username': username
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Not logged in'
            }), 401
            
    except Exception as e:
        current_app.logger.error(f"Error getting current user: {e}")
        return jsonify({
            'success': False, 
            'message': 'Server error'
        }), 500

@user_bp.route("/profile", methods=["GET"])
def get_user_profile():
    """Get user profile data"""
    try:
        if not session.get("user_logged_in"):
            return jsonify({
                'success': False, 
                'message': 'Not logged in'
            }), 401

        user_id = session.get("user_id")
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False, 
                'message': 'User not found'
            }), 404

        # Return basic profile info (extend this based on your user model fields)
        profile_data = {
            'username': user.username,
            'created_at': user.created_at.isoformat() if user.created_at else None
        }

        return jsonify({
            'success': True,
            'profile': profile_data
        })

    except Exception as e:
        current_app.logger.error(f"Error getting user profile: {e}")
        return jsonify({
            'success': False, 
            'message': 'Server error'
        }), 500

@user_bp.route("/profile", methods=["POST"])
def update_user_profile():
    """Update user profile"""
    try:
        if not session.get("user_logged_in"):
            return jsonify({
                'success': False, 
                'message': 'Not logged in'
            }), 401

        user_id = session.get("user_id")
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False, 
                'message': 'User not found'
            }), 404

        data = request.get_json()
        
        # Add profile fields here as needed
        # For now, we'll just return success since username can't be changed
        # and we don't have other fields in the current model
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user profile: {e}")
        return jsonify({
            'success': False, 
            'message': 'Server error'
        }), 500

@user_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change user password"""
    try:
        if not session.get("user_logged_in"):
            return jsonify({
                'success': False, 
                'message': 'Not logged in'
            }), 401

        user_id = session.get("user_id")
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False, 
                'message': 'User not found'
            }), 404

        data = request.get_json()
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        confirm_password = data.get('confirmPassword')

        # Validate input
        if not all([current_password, new_password, confirm_password]):
            return jsonify({
                'success': False, 
                'message': 'All fields are required'
            }), 400

        if new_password != confirm_password:
            return jsonify({
                'success': False, 
                'message': 'New passwords do not match'
            }), 400

        # Check current password
        if not user.check_password(current_password):
            return jsonify({
                'success': False, 
                'message': 'Current password is incorrect'
            }), 400

        # Set new password
        user.set_password(new_password)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password: {e}")
        return jsonify({
            'success': False, 
            'message': 'Server error'
        }), 500

@user_bp.route("/stats", methods=["GET"])
def get_user_stats():
    """Get user statistics for dashboard"""
    try:
        if not session.get("user_logged_in"):
            return jsonify({
                'success': False, 
                'message': 'Not logged in'
            }), 401

        user_id = session.get("user_id")
        
        # You can add more stats here based on your models
        stats = {
            'total_reservations': 0,
            'completed_orders': 0,
            'member_since': None
        }

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {e}")
        return jsonify({
            'success': False, 
            'message': 'Server error'}), 500