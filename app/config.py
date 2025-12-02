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
    """🟢 PRODUCTION CONFIG - Session Pooler for Render"""
    
    # 🟢 Use DATABASE_URL environment variable if available, otherwise fallback
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        # Fix postgres:// to postgresql:// if needed
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
        print("✅ Using DATABASE_URL from environment variable")
    else:
        # Fallback to hardcoded URL
        SQLALCHEMY_DATABASE_URI = "postgresql://postgres.knawfwgerjfutwurrbfx:Atbi_reg1neThesis@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
        print("⚠️ DATABASE_URL not set, using fallback URL")
    
    DEBUG = False
    
    # 🟢 OPTIMIZED FOR RENDER + SUPABASE FREE TIER
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 60,         # 1 minute (short for free tier)
        'pool_size': 2,             # Very small pool
        'max_overflow': 1,          # Minimal overflow
        'pool_timeout': 45,
        
        'connect_args': {
            'connect_timeout': 30,   # Longer timeout for cross-region
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 3,
            'sslmode': 'require',
            'application_name': 'atbi_app_render',
        }
    }

# 🟢 AUTO-DETECTION FOR RENDER
def auto_detect_config():
    # Priority 1: Environment variable
    env_config = os.environ.get('APP_CONFIG')
    if env_config:
        return env_config
    
    # Priority 2: Check if we're on Render
    if os.environ.get('RENDER'):
        print("🚀 Detected Render environment")
        return 'supabase'  # Use SupabaseConfig on Render
    
    # Priority 3: Local development detection
    computer_name = socket.gethostname().lower()
    username = os.environ.get('USERNAME', '').lower()
    
    your_identifiers = ['cyla', 'cyla-pc']
    teammate_identifiers = ['client', 'regine']
    
    if any(identifier in computer_name or identifier in username for identifier in your_identifiers):
        return 'local'
    
    if any(identifier in computer_name or identifier in username for identifier in teammate_identifiers):
        return 'teammate'
    
    # Default: Use SupabaseConfig (production)
    return 'supabase'

# Configuration mapping - REMOVED ProductionConfig
config_dict = {
    'local': LocalConfig,
    'teammate': TeammateConfig,
    'supabase': SupabaseConfig,  # 🟢 This is now the PRODUCTION config
}

config_name = auto_detect_config()
Config = config_dict.get(config_name, SupabaseConfig)  # Default to SupabaseConfig

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1] if '@' in Config.SQLALCHEMY_DATABASE_URI else 'Local database'}")