import os

class Config:
    # Secret key for sessions/CSRF (change this in production)
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")

    # PostgreSQL connection URL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:cyla0917@localhost:5432/atbiDB")

    # Disable track modifications to save memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Optional: Debug mode
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
