import os

class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"

class YourConfig(BaseConfig):
    """Your local development configuration"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:cyla0917@localhost:5432/atbi_db"

class TeammateConfig(BaseConfig):
    """Your teammate's local development configuration"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:thesisregine@localhost:5432/atbi_db"

class ProductionConfig(BaseConfig):
    """Production configuration (uses environment variables)"""
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    DEBUG = False

# Configuration mapping
config_dict = {
    'you': YourConfig,
    'teammate': TeammateConfig,
    'production': ProductionConfig
}

# Select configuration based on environment variable
config_name = os.environ.get('APP_CONFIG', 'you')
Config = config_dict.get(config_name, YourConfig)

# Validate configuration
if not Config.SQLALCHEMY_DATABASE_URI:
    raise ValueError(f"Database URI not configured for: {config_name}")

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1]}")