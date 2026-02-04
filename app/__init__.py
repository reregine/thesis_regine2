from flask import Flask, session
from .config import Config
from .extension import db, migrate
from .routes.reservation import reservation_bp, init_scheduler
from .routes.cart import cart_bp
from .routes.favorites import favorites_bp
from .routes.dashboard import dashboard_bp
from .routes import home, incubatee_showroom, layouts, shop, notification, login, admin, contact, about, user
from .utils.auto_stock_notifier import get_auto_notifier


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(about.about_bp)
    app.register_blueprint(home.home_bp)  
    app.register_blueprint(incubatee_showroom.incubatee_bp)  
    app.register_blueprint(layouts.layouts_bp)  
    app.register_blueprint(login.login_bp)
    app.register_blueprint(notification.notif_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(shop.shop_bp)  
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(contact.contact_bp) 
    app.register_blueprint(cart_bp) 
    app.register_blueprint(favorites_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(user.user_bp)
    
    @app.context_processor
    def inject_user_data():
        return dict(user_logged_in=session.get('user_logged_in'),admin_logged_in=session.get('admin_logged_in'),username=session.get('username'),admin_username=session.get('admin_username'))
    
    # Initialize product popularity data on startup
    with app.app_context():
        try:
            from app.services.popularity_service import ProductPopularityService
            ProductPopularityService.initialize_on_startup()
        except Exception as e:
            print(f"⚠️ Could not initialize popularity data: {e}")
            
    # Initialize the scheduler with the app
    init_scheduler(app)
    
    # Initialize auto stock notifier AFTER app context is fully set up
    from .utils.auto_stock_notifier import init_auto_notifier
    init_auto_notifier(app)
    
    return app