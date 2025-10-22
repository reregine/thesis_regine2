from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..extension import db
from ..models.user import User

login_bp = Blueprint("login", __name__, url_prefix="/login")

# 🔑 Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin2025_atbi"


@login_bp.route("/")
def login():
    """Login page
        if session.get('admin_logged_in') or session.get('user_logged_in'):
            return redirect(url_for('home.index'))  # redirect users to home"""
    error = request.args.get('error')
    return render_template("login/login.html", error=error)


@login_bp.route("/authenticate", methods=["POST"])
def authenticate():
    """Handle login"""
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        #  Admin login (hardcoded)
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return jsonify({
                'success': True,
                'message': '✅ Login successful! Welcome Admin!',
                'redirect_url': url_for('admin.admin_dashboard')
            })

        # Normal user login
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_logged_in'] = True
            session['user_id'] = user.id_no
            session['username'] = user.username
            return jsonify({
                'success': True,
                'message': f'✅ Welcome back, {user.username}!',
                'redirect_url': url_for('home.index')})

        return jsonify({'success': False, 'message': '❌ Invalid username or password'}), 401

    except Exception as e:
        print("Login error:", e)
        return jsonify({'success': False, 'message': '❌ Login error occurred'}), 500


@login_bp.route("/register", methods=["GET"])
def register_page():
    """Show registration page"""
    return render_template("login/registration.html")

@login_bp.route("/register_api", methods=["POST"])
def register_api():
    """Receive username, password, confirm password from frontend and save to DB"""
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        confirm_password = data.get("confirm_password", "").strip()

        # Validate required fields
        if not username or not password or not confirm_password:
            return jsonify({"success": False, "message": "⚠ All fields are required"}), 400

        # Validate confirm password
        if password != confirm_password:
            return jsonify({"success": False, "message": "⚠ Passwords do not match"}), 400

        # Check if username exists
        if User.query.filter_by(username=username).first():
            return jsonify({"success": False, "message": "⚠ Username already exists"}), 409

        # Create and save new user
        new_user = User(username=username)
        new_user.set_password(password)  # this will hash + salt the password
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"success": True, "message": "✅ Registration successful! Please log in."})

    except Exception as e:
        print("Registration error:", e)
        return jsonify({"success": False, "message": "❌ Registration failed"}), 500


@login_bp.route("/logout")
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login.login'))

@login_bp.route("/status", methods=["GET"])
def login_status():
    """Return whether the current user is logged in."""
    if session.get("user_logged_in"):
        return jsonify({
            "success": True,
            "user_id": session.get("user_id"),
            "username": session.get("username"),
            "role": "user"
        })
    elif session.get("admin_logged_in"):
        return jsonify({
            "success": True,
            "admin": True,
            "username": session.get("admin_username"),
            "role": "admin"
        })
    else:
        return jsonify({"success": False, "message": "Not logged in"}), 401

