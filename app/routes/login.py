from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

login_bp = Blueprint("login", __name__, url_prefix="/login")

# Admin credentials (in production, use environment variables or database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin2025_atbi"

@login_bp.route("/")
def login():
    """Login page - serves the login form"""
    # If already logged in, redirect to admin dashboard
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_dashboard'))
    
    # Get error message from URL params if any
    error = request.args.get('error')
    return render_template("login/login.html", error=error)

@login_bp.route("/authenticate", methods=["POST"])
def authenticate():
    """Handle login form submission"""
    try:
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # Validate credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': '✅ Login successful! Welcome Admin!',
                    'redirect_url': url_for('admin.admin_dashboard')
                })
            else:
                return redirect(url_for('admin.admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': '❌ Invalid username or password'
                }), 401
            else:
                return redirect(url_for('login.login', error="Invalid credentials"))
                
    except Exception as e:
        if request.is_json:
            return jsonify({
                'success': False,
                'message': '❌ Login error occurred'
            }), 500
        else:
            return redirect(url_for('login.login', error="Login error occurred"))

@login_bp.route("/logout")
def logout():
    """Logout functionality"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('login.login'))