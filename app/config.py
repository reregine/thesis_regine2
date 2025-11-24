import os
import socket

class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    
    # File upload configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class LocalConfig(BaseConfig):
    """Local development configuration"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:cyla0917@localhost:5432/atbi_db"

class TeammateConfig(BaseConfig):
    """Teammate's local development configuration"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:thesisregine@localhost:5432/atbi_db"

class SupabaseConfig(BaseConfig):
    """Supabase production configuration with connection pooling"""
    # Fixed connection string (changed from port 6543 to 5432)
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres.knawfwgerjfutwurrbfx:R3gIne_Th3sis@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
    DEBUG = False
    
    # SQLAlchemy engine options for stable Supabase connection
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Verify connections before using them (prevents stale connections)
        'pool_pre_ping': True,
        
        # Recycle connections after 5 minutes (300 seconds)
        'pool_recycle': 300,
        
        # Maximum number of persistent connections
        'pool_size': 10,
        
        # Allow up to 5 additional connections when pool is full
        'max_overflow': 20,
        
        # Connection arguments for PostgreSQL
        'connect_args': {
            # Connection timeout (10 seconds)
            'connect_timeout': 10,
            
            # Require SSL for security
            'sslmode': 'require',
            
            # TCP keepalive settings to maintain connection
            'keepalives': 1,              # Enable TCP keepalives
            'keepalives_idle': 30,        # Start keepalives after 30s idle
            'keepalives_interval': 10,    # Send keepalive every 10s
            'keepalives_count': 5,        # Try 5 times before giving up
        }
    }

class ProductionConfig(BaseConfig):
    """Production configuration (uses DATABASE_URL environment variable)"""
    # Get DATABASE_URL and fix scheme if needed
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    DEBUG = False
    
    # Same connection pooling options as Supabase
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 5,
        'connect_args': {
            'connect_timeout': 10,
            'sslmode': 'require',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
    }

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
        return 'local'
    
    # Check if any of teammate's identifiers match  
    if any(identifier in computer_name or identifier in username for identifier in teammate_identifiers):
        return 'teammate'
    
    # Default fallback - change this based on who uses it more
    return 'teammate'  # 🟢 Set default to teammate

# Configuration mapping
config_dict = {
    'local': LocalConfig,
    'teammate': TeammateConfig,
    'supabase': SupabaseConfig,
    'production': ProductionConfig
}

# Select configuration based on environment variable
config_name = os.environ.get('APP_CONFIG', 'supabase')
Config = config_dict.get(config_name, SupabaseConfig)

# Validate configuration
if not Config.SQLALCHEMY_DATABASE_URI:
    raise ValueError(f"Database URI not configured for: {config_name}")

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1] if '@' in Config.SQLALCHEMY_DATABASE_URI else 'Local database'}")