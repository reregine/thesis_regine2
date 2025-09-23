from flask import Flask
from .config import Config
from .extension import db, migrate
from .routes import home, inventory, incubatee_showroom, layouts, reservation, shop,notification, reports, showroom

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(home.bp)  
    app.register_blueprint(inventory.bp)
    app.register_blueprint(incubatee_showroom.incubatee_bp)  
    app.register_blueprint(layouts.layouts_bp)  
    app.register_blueprint(notification.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(reservation.bp)
    app.register_blueprint(shop.shop_bp)  # Uncomment if shop blueprint is implemented
    app.register_blueprint(showroom.bp)
    # app.register_blueprint(admin.bp)  # Uncomment if admin blueprint is implemented

    return app
