# aplikacja/__init__.py
from flask import Flask, request # Added request import
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime as dt # For the custom date filter
import re # For nl2br filter
from markupsafe import escape, Markup # For nl2br filter
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
# from flask_mail import Mail # Removed
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
# mail = Mail() # Removed

# Login manager configuration
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
login_manager.login_message = "Proszę się zalogować, aby uzyskać dostęp do tej strony."

# Custom Jinja filter for date formatting
def format_date(value, format_string='%Y'):
    current_time = dt.utcnow()
    if value == "now":
        if format_string:
            return current_time.strftime(format_string)
        return current_time # Return datetime object if no format_string
    if isinstance(value, dt):
        if format_string:
            return value.strftime(format_string)
        return value # Return datetime object if no format_string
    return value

# Custom Jinja filter for nl2br
def nl2br_filter(s):
    if s is None:
        return ''
    # Escape the string first to prevent XSS, then replace newlines with <br>
    # The 'safe' filter in the template should ideally be applied *after* nl2br if nl2br itself doesn't produce Markup.
    # However, for simplicity and common usage, nl2br often produces Markup directly.
    # Let's make it produce Markup.
    s = escape(s)
    return Markup(s.replace('\\r\\n', '<br>').replace('\\n', '<br>').replace('\\r', '<br>'))

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    instance_path = app.config.get('INSTANCE_PATH', app.instance_path)
    try:
        os.makedirs(instance_path)
    except OSError:
        pass # Already exists
    
    # Ensure ebook storage path exists if defined relative to instance
    ebook_storage = app.config.get('EBOOKS_STORAGE_PATH')
    if ebook_storage and not os.path.isabs(ebook_storage):
        # If it's a relative path, assume it's relative to the project root or instance path
        # For simplicity, let's assume it's relative to project root if not absolute
        ebook_full_path = os.path.join(app.root_path, '..', ebook_storage) if 'instance' not in ebook_storage else os.path.join(instance_path, os.path.basename(ebook_storage))
        # A bit convoluted, better to define EBOOKS_STORAGE_PATH in .env as absolute or clearly relative to instance
        # For now, let's ensure the one from config (which defaults to instance/ebook_files) is created
        default_ebook_path = os.path.join(instance_path, 'ebook_files')
        try:
            os.makedirs(default_ebook_path, exist_ok=True)
        except OSError as e:
            app.logger.warning(f"Could not create ebook storage directory {default_ebook_path}: {e}")


    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    # mail.init_app(app) # Removed

    # Register custom Jinja filters
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['nl2br'] = nl2br_filter

    # Import and register blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    
    from .books import books as books_blueprint
    app.register_blueprint(books_blueprint, url_prefix='/books')

    from .cart import cart as cart_blueprint
    app.register_blueprint(cart_blueprint, url_prefix='/cart')

    from .orders import orders as orders_blueprint
    app.register_blueprint(orders_blueprint, url_prefix='/orders')

    from .profile import profile as profile_blueprint
    app.register_blueprint(profile_blueprint, url_prefix='/profile')
    
    # Context processors
    @app.context_processor
    def inject_cart_item_count():
        from .models import Koszyk, ElementKoszyka # Local import
        from flask_login import current_user
        if current_user.is_authenticated:
            koszyk = Koszyk.query.filter_by(id_uzytkownika=current_user.id).first()
            if koszyk:
                return dict(cart_item_count=sum(item.ilosc for item in koszyk.elementy_koszyka))
        # For anonymous users, session-based cart count
        elif request.cookies.get('cart_session_id'):
            koszyk = Koszyk.query.filter_by(id_sesji=request.cookies.get('cart_session_id')).first()
            if koszyk:
                 return dict(cart_item_count=sum(item.ilosc for item in koszyk.elementy_koszyka))
        return dict(cart_item_count=0)

    @app.context_processor
    def inject_unread_notifications_count():
        from .models import Powiadomienie # Local import
        from flask_login import current_user
        if current_user.is_authenticated and (current_user.rola == 'admin' or current_user.rola == 'manager'):
            count = Powiadomienie.query.filter(
                (Powiadomienie.rola_docelowa == current_user.rola) | 
                (Powiadomienie.id_uzytkownika_docelowego == current_user.id),
                Powiadomienie.czy_przeczytane == False
            ).count()
            return dict(unread_notifications_count=count)
        return dict(unread_notifications_count=0)

    return app
