import os
import socket

class BaseConfig:
    """Base configuration with common settings"""
    SECRET_KEY = "your-secret-key-change-this-in-production-2025"  # Hardcoded for Render
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False  # Default to False for production
    
    # File upload configuration
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Email configuration for low stock notifications
    # HARDCODED VALUES for Render (change these to your actual values)
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'reginejoycefrancisco110603@gmail.com'
    SMTP_PASSWORD = 'lpsdyhyrsfpzewzy'
    FROM_EMAIL = 'atbi.system@gmail.com'  # ADD THIS - sender email
    ADMIN_EMAIL = 'reginejoycefrancisco110603@gmail.com'  # ADD THIS - admin notification email
    
    # Redis configuration (optional - comment out if not using Redis)
    REDIS_URL = 'redis://localhost:6379/0'  # Default local Redis
    
    # Low stock notification settings
    LOW_STOCK_THRESHOLD = 10
    NOTIFICATION_COOLDOWN_HOURS = 24
    
    # Enable/disable auto notifications
    AUTO_STOCK_NOTIFICATIONS = True

class LocalConfig(BaseConfig):
    """🟢 LOCAL DEVELOPMENT"""
    
    # 🟢 Use Supabase for local development too
    database_url = "postgresql://postgres.knawfwgerjfutwurrbfx:Atbi_reg1neThesis@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
    
    SQLALCHEMY_DATABASE_URI = database_url
    print("🔄 Local: Using Supabase database")
    
    DEBUG = True  # Debug mode ON for local development
    
    # Email settings for local development
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'reginejoycefrancisco110603@gmail.com'
    SMTP_PASSWORD = 'lpsdyhyrsfpzewzy'
    FROM_EMAIL = 'atbi.system.local@gmail.com'
    ADMIN_EMAIL = 'reginejoycefrancisco110603@gmail.com'
    
    # 🟢 Optimized for local development with Supabase
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 90,
        'pool_size': 2,
        'max_overflow': 1,
        'pool_timeout': 30,
        
        'connect_args': {
            'connect_timeout': 20,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 3,
            'sslmode': 'require',
            'application_name': 'atbi_app_local',
        }
    }

class SupabaseConfig(BaseConfig):
    """🟢 PRODUCTION CONFIG - Session Pooler for Render"""
    
    # 🟢 Hardcoded production database URL
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres.knawfwgerjfutwurrbfx:Atbi_reg1neThesis@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
    print("✅ Production: Using Supabase database")
    
    DEBUG = False
    
    # Email settings for production - HARDCODED
    SMTP_HOST = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'reginejoycefrancisco110603@gmail.com'
    SMTP_PASSWORD = 'lpsdyhyrsfpzewzy'
    FROM_EMAIL = 'atbi.system@gmail.com'
    ADMIN_EMAIL = 'reginejoycefrancisco110603@gmail.com'
    
    # Important: Validate email configuration
    @classmethod
    def validate_email_config(cls):
        """Validate that email credentials are set"""
        required_vars = {
            'SMTP_USERNAME': cls.SMTP_USERNAME,
            'SMTP_PASSWORD': cls.SMTP_PASSWORD,
            'FROM_EMAIL': cls.FROM_EMAIL,
            'ADMIN_EMAIL': cls.ADMIN_EMAIL
        }
        
        missing_or_default = []
        for var_name, value in required_vars.items():
            if not value or 'change' in value.lower() or 'your' in value.lower():
                missing_or_default.append(var_name)
        
        if missing_or_default:
            print(f"⚠️ WARNING: These email variables need to be updated: {', '.join(missing_or_default)}")
            print("⚠️ Low stock notifications will not work until you update them in config.py")
            return False
        return True
    
    # 🟢 OPTIMIZED FOR RENDER + SUPABASE FREE TIER
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 60,
        'pool_size': 2,
        'max_overflow': 1,
        'pool_timeout': 45,
        
        'connect_args': {
            'connect_timeout': 30,
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
    # Priority 1: Check if we're on Render
    if os.environ.get('RENDER') or os.environ.get('DYNO'):  # DYNO for Heroku compatibility
        print("🚀 Detected Render/Production environment")
        return 'supabase'
    
    # Priority 2: Local development detection
    computer_name = socket.gethostname().lower()
    username = os.environ.get('USERNAME', '').lower()
    
    your_identifiers = ['cyla', 'cyla-pc', 'desktop', 'laptop']
    
    if any(identifier in computer_name or identifier in username for identifier in your_identifiers):
        return 'local'
    
    # Default: Use production config
    return 'supabase'

# Configuration mapping
config_dict = {
    'local': LocalConfig,
    'supabase': SupabaseConfig,
}

config_name = auto_detect_config()
Config = config_dict.get(config_name, SupabaseConfig)  # Default to SupabaseConfig

print(f"🔧 Loaded configuration: {config_name}")
print(f"📊 Database: {Config.SQLALCHEMY_DATABASE_URI.split('@')[-1] if '@' in Config.SQLALCHEMY_DATABASE_URI else 'Local database'}")

# Validate email configuration
if hasattr(Config, 'validate_email_config'):
    Config.validate_email_config()
else:
    # Basic check for BaseConfig
    if not Config.SMTP_USERNAME or 'change' in Config.SMTP_USERNAME.lower():
        print("⚠️ WARNING: Please update SMTP_USERNAME in config.py")
    if not Config.SMTP_PASSWORD or 'change' in Config.SMTP_PASSWORD.lower():
        print("⚠️ WARNING: Please update SMTP_PASSWORD in config.py")

print(f"📦 Low stock threshold: {Config.LOW_STOCK_THRESHOLD} units")
print(f"🔄 Auto notifications: {'✅ Enabled' if Config.AUTO_STOCK_NOTIFICATIONS else '❌ Disabled'}")
print(f"📧 From email: {Config.FROM_EMAIL}")
print(f"📧 Admin email: {Config.ADMIN_EMAIL}")