import os
import socket

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

# 🟢 IMPROVED AUTO-DETECTION
def auto_detect_config():
    # Priority 1: Environment variable
    env_config = os.environ.get('APP_CONFIG')
    if env_config:
        return env_config
    
    # Priority 2: Computer name detection
    computer_name = socket.gethostname().lower()
    username = os.environ.get('USERNAME', '').lower()
    
    print(f"💻 Computer: {computer_name}")
    print(f"👤 User: {username}")
    
    # Your identifiers - add your computer names/usernames here
    your_identifiers = [
        'cyla',           # Your username
        'cyla-pc',        # Your computer name  
        'your-laptop'     # Add your actual computer names
    ]
    
    # Teammate's identifiers - add her computer names/usernames here
    teammate_identifiers = [
        'client',         # Her current computer name
        'regine',         # Her possible username
        'teammate-pc'     # Add her other computer names
    ]
    
    # Check if any of your identifiers match
    if any(identifier in computer_name or identifier in username for identifier in your_identifiers):
        return 'you'
    
    # Check if any of teammate's identifiers match  
    if any(identifier in computer_name or identifier in username for identifier in teammate_identifiers):
        return 'teammate'
    
    # Default fallback - change this based on who uses it more
    return 'teammate'  # 🟢 Set default to teammate

# Configuration mapping
config_dict = {
    'you': YourConfig,
    'teammate': TeammateConfig,
    'production': ProductionConfig
}

# Auto-detect configuration
config_name = auto_detect_config()
Config = config_dict.get(config_name, TeammateConfig)  # Default to TeammateConfig

# Validate configuration
if not Config.SQLALCHEMY_DATABASE_URI:
    raise ValueError(f"Database URI not configured for: {config_name}")

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1]}")