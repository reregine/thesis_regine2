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
    """Session Pooler with VERY SMALL pool"""
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres.knawfwgerjfutwurrbfx:Atbi_reg1neThesis@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
    DEBUG = False
    
    # 🟢 REDUCE POOL SIZE DRAMATICALLY
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 45,         # 45 seconds (very short)
        'pool_size': 1,             # 🟢 ONLY 1 CONNECTION!
        'max_overflow': 0,          # 🟢 NO overflow connections
        'pool_timeout': 60,         # Longer timeout
        
        'connect_args': {
            'connect_timeout': 30,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 3,
            'sslmode': 'require',
            'application_name': 'atbi_app',
        }
    }

class ProductionConfig(BaseConfig):
    """Production configuration"""
    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url
    DEBUG = False
    
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

# 🟢 AUTO-DETECTION
def auto_detect_config():
    env_config = os.environ.get('APP_CONFIG')
    if env_config:
        return env_config
    
    computer_name = socket.gethostname().lower()
    username = os.environ.get('USERNAME', '').lower()
    
    your_identifiers = ['cyla', 'cyla-pc']
    teammate_identifiers = ['client', 'regine']
    
    if any(identifier in computer_name or identifier in username for identifier in your_identifiers):
        return 'local'
    
    if any(identifier in computer_name or identifier in username for identifier in teammate_identifiers):
        return 'teammate'
    
    return 'supabase'

# Configuration mapping
config_dict = {
    'local': LocalConfig,
    'teammate': TeammateConfig,
    'supabase': SupabaseConfig,  # 🟢 Session Pooler
    'production': ProductionConfig
}

config_name = os.environ.get('APP_CONFIG', 'supabase')
Config = config_dict.get(config_name, SupabaseConfig)

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1] if '@' in Config.SQLALCHEMY_DATABASE_URI else 'Local database'}")