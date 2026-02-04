import os
import socket
from datetime import timedelta

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
    FROM_EMAIL = 'atbi.system@gmail.com'  
    ADMIN_EMAIL = 'reginejoycefrancisco110603@gmail.com'  
    
    # Redis configuration (optional - comment out if not using Redis)
    REDIS_URL = 'redis://localhost:6379/0'  # Default local Redis
    
    # Low stock notification settings - UPDATED FOR THESIS DEMO
    LOW_STOCK_THRESHOLD = 10
    NOTIFICATION_COOLDOWN_HOURS = 24
    
    # Enable/disable auto notifications
    AUTO_STOCK_NOTIFICATIONS = True
    
    # 🔥 NEW: Email interval settings for thesis demonstration
    EMAIL_INTERVAL_MINUTES = 5  # Send emails every 5 minutes (for demo)
    STOCK_CHECK_INTERVAL_MINUTES = 5  # Check for low stock every 5 minutes
    
    # 🔥 NEW: Dual notification schedule within each 5-minute interval
    FIRST_NOTIFICATION_MINUTE = 1  # Send first batch at minute 1
    SECOND_NOTIFICATION_MINUTE = 4  # Send second batch at minute 4
    
    # 🔥 NEW: Email logging
    EMAIL_LOGGING_ENABLED = True
    EMAIL_LOG_RETENTION_DAYS = 7  # Keep logs for 7 days
    
    # 🔥 NEW: Notification batches configuration
    NOTIFICATION_BATCHES = [
        {
            'name': 'first_batch',
            'minute_offset': FIRST_NOTIFICATION_MINUTE,
            'send_to_admin': True  # Send admin summary with first batch
        },
        {
            'name': 'second_batch', 
            'minute_offset': SECOND_NOTIFICATION_MINUTE,
            'send_to_admin': False  # Don't send admin summary with second batch
        }
    ]
    
    # 🔥 NEW: Test mode for thesis demonstration
    DEMO_MODE = True  # Set to True for thesis demo
    DEMO_NOTIFICATIONS_PER_BATCH = 2  # Send 2 notifications per batch for demo

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
    
    # 🔥 LOCAL DEMO SETTINGS (faster for testing)
    EMAIL_INTERVAL_MINUTES = 2  # Faster interval for local testing
    STOCK_CHECK_INTERVAL_MINUTES = 2
    FIRST_NOTIFICATION_MINUTE = 0.5  # 30 seconds for first batch
    SECOND_NOTIFICATION_MINUTE = 1.5  # 90 seconds for second batch
    DEMO_MODE = True
    
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
    
    # 🔥 PRODUCTION SETTINGS FOR THESIS DEMO
    EMAIL_INTERVAL_MINUTES = 5  # 5-minute intervals for thesis demonstration
    STOCK_CHECK_INTERVAL_MINUTES = 5
    FIRST_NOTIFICATION_MINUTE = 1  # First batch at minute 1
    SECOND_NOTIFICATION_MINUTE = 4  # Second batch at minute 4
    DEMO_MODE = True  # Keep in demo mode for thesis presentation
    DEMO_NOTIFICATIONS_PER_BATCH = 2  # Show 2 notifications per batch
    
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
        
        # 🔥 NEW: Validate demo configuration
        print(f"🔥 DEMO MODE CONFIGURATION:")
        print(f"   Interval: {cls.EMAIL_INTERVAL_MINUTES} minutes")
        print(f"   First batch: minute {cls.FIRST_NOTIFICATION_MINUTE}")
        print(f"   Second batch: minute {cls.SECOND_NOTIFICATION_MINUTE}")
        print(f"   Emails per batch: {cls.DEMO_NOTIFICATIONS_PER_BATCH}")
        
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

# 🔥 NEW: Print demo configuration details
print(f"🔥 DEMO NOTIFICATION SYSTEM:")
print(f"   Interval: {Config.EMAIL_INTERVAL_MINUTES} minutes")
print(f"   First notification: minute {Config.FIRST_NOTIFICATION_MINUTE}")
print(f"   Second notification: minute {Config.SECOND_NOTIFICATION_MINUTE}")
print(f"   Mode: {'Thesis Demo' if Config.DEMO_MODE else 'Production'}")

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
print(f"📊 Email logging: {'✅ Enabled' if Config.EMAIL_LOGGING_ENABLED else '❌ Disabled'}")
print(f"🗄️ Log retention: {Config.EMAIL_LOG_RETENTION_DAYS} days")

# 🔥 NEW: Print schedule summary
print(f"\n🎯 NOTIFICATION SCHEDULE SUMMARY:")
print(f"   Every {Config.EMAIL_INTERVAL_MINUTES} minutes:")
print(f"     → Minute {Config.FIRST_NOTIFICATION_MINUTE}: Send first batch (with admin summary)")
print(f"     → Minute {Config.SECOND_NOTIFICATION_MINUTE}: Send second batch")
print(f"   Demo mode: {'✅ ON' if Config.DEMO_MODE else '❌ OFF'}")
print(f"   Emails per batch: {Config.DEMO_NOTIFICATIONS_PER_BATCH if Config.DEMO_MODE else 'All low stock products'}")