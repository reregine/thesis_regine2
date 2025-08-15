from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Create extension instances (not bound to app yet)
db = SQLAlchemy()
migrate = Migrate()
