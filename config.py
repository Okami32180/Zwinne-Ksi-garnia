import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import timedelta # Import timedelta

basedir_string = r'D:/Projekt/ksiegarnia' # Hardcoded base directory string
load_dotenv(os.path.join(basedir_string, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key_should_be_changed_for_security'
    # Force SQLite with hardcoded absolute path
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{basedir_string.replace('\\\\', '/')}/ksiegarnia.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

    # Security settings (can be kept)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't') # False for local HTTP
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() in ('true', '1', 't')
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() in ('true', '1', 't') # False for local HTTP
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=int(os.environ.get('REMEMBER_COOKIE_DAYS', 30))) # Add remember me duration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'another_secret_for_csrf_forms'

    # Application specific
    BOOKS_PER_PAGE = int(os.environ.get('BOOKS_PER_PAGE', 10))
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@example.com' # Used for default admin creation
    EBOOKS_STORAGE_PATH = os.environ.get('EBOOKS_STORAGE_PATH') or os.path.join(basedir_string, 'ebook_files').replace('\\\\', '/')
    EBOOK_DOWNLOAD_TOKEN_VALIDITY_HOURS = int(os.environ.get('EBOOK_DOWNLOAD_TOKEN_VALIDITY_HOURS', 24))
    
    # Fake Payment System Log File
    FAKE_PAYMENT_LOG_FILE = os.environ.get('FAKE_PAYMENT_LOG_FILE') or os.path.join(basedir_string, 'fake_payments.csv').replace('\\\\', '/')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False # Set to True to see SQL queries for debugging

class TestingConfig(Config):
    TESTING = True
    # For testing, often a simpler, relative path is used, or an in-memory DB
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        f"sqlite:///{os.path.join(basedir_string, 'ksiegarnia_test.db').replace('\\\\', '/')}" # Ensure test DB is distinct
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    DEBUG = True # Often useful to have debug true for tests too
    # SERVER_NAME = "localhost.localdomain" # May be needed for url_for in some test contexts
    # APPLICATION_ROOT = "/"

class ProductionConfig(Config):
    DEBUG = False
    # Ensure SECRET_KEY, WTF_CSRF_SECRET_KEY are set strong in .env for production
    # SQLALCHEMY_DATABASE_URI should point to a persistent production DB in .env
    SESSION_COOKIE_SECURE = True # Enforce HTTPS for session cookies in production
    REMEMBER_COOKIE_SECURE = True # Enforce HTTPS for remember_me cookies

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}