from flask import Blueprint, render_template, session, redirect, url_for, jsonify

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def user_dashboard():
    """Dashboard route that returns the dashboard HTML"""
    # Check if user is logged in
    if not session.get('user_logged_in'):
        return redirect(url_for('login.login'))
    
    # Get username from session or database
    username = session.get('username', 'User')
    
    return render_template("dashboard.html", username=username)

@dashboard_bp.route("/dashboard-content")
def dashboard_content():
    """API endpoint to load dashboard content for modal"""
    if not session.get('user_logged_in'):
        return jsonify({"success": False, "message": "User not logged in"}), 401
    
    username = session.get('username', 'User')
    return render_template("dashboard.html", username=username)

# Additional dashboard-related API endpoints
@dashboard_bp.route("/user/stats", methods=["GET"])
def user_stats():
    """Get user statistics for dashboard"""
    try:
        if not session.get('user_logged_in'):
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        user_id = session.get('user_id')
        
        # Example stats - customize based on your models
        stats = {
            "total_reservations": 0,
            "pending_reservations": 0,
            "completed_orders": 0,
            "member_since": "2024-01-01"  # You'll need to get this from your user model
        }
        
        return jsonify({"success": True, "stats": stats})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@dashboard_bp.route("/user/profile", methods=["POST"])
def update_profile():
    """Update user profile"""
    try:
        if not session.get('user_logged_in'):
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        # Add your profile update logic here
        # You'll need to implement this based on your user model
        
        return jsonify({"success": True, "message": "Profile updated successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@dashboard_bp.route("/user/change-password", methods=["POST"])
def change_password():
    """Change user password"""
    try:
        if not session.get('user_logged_in'):
            return jsonify({"success": False, "message": "User not logged in"}), 401
        
        # Add your password change logic here
        # You'll need to implement this based on your user model
        
        return jsonify({"success": True, "message": "Password changed successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500