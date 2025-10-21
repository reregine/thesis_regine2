from flask import Flask
from .config import Config
from .extension import db, migrate
from .routes.reservation import reservation_bp
from .routes.cart import cart_bp
from .routes import home, incubatee_showroom, layouts, shop, notification, reports, showroom, login, admin, contact

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(home.home_bp)  
    app.register_blueprint(incubatee_showroom.incubatee_bp)  
    app.register_blueprint(layouts.layouts_bp)  
    app.register_blueprint(login.login_bp)
    app.register_blueprint(notification.notif_bp)
    app.register_blueprint(reports.report_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(shop.shop_bp)  
    app.register_blueprint(showroom.showroom_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(contact.contact_bp) 
    app.register_blueprint(cart_bp) 
    return app
