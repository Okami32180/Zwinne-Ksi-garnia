import os
print(f"Base directory: {os.path.abspath(os.path.dirname(__file__))}")
print(f"Database path: {os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'ksiegarnia.db')}")
print(f"Database file exists: {os.path.exists(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'ksiegarnia.db'))}")
from aplikacja import create_app, db
from aplikacja.models import Uzytkownik, Book, Kategoria, Gatunek, Wydawnictwo # Add other models as needed
from flask_migrate import upgrade

# Create app instance using the factory
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.shell_context_processor
def make_shell_context():
    """
    Makes additional variables available in the Flask shell context.
    This allows for easier testing and interaction with the application
    and its components directly from the command line.
    """
    return dict(db=db, Uzytkownik=Uzytkownik, Book=Book, Kategoria=Kategoria, Gatunek=Gatunek, Wydawnictwo=Wydawnictwo)

@app.cli.command("init-db")
def init_db_command():
    """Initializes the database and creates an admin user."""
    with app.app_context():
        # Apply migrations
        upgrade()
        print("Database migrations applied.")
        
        # Create default roles or other initial data if needed
        # Example: db.session.add(Role(name='Admin'))
        # db.session.commit()
        
        # Create a default admin user (example)
        admin_login = 'admin'
        admin_email = app.config.get('ADMIN_EMAIL', 'admin@example.com')
        if not Uzytkownik.query.filter_by(login=admin_login).first():
            admin_user = Uzytkownik(
                login=admin_login,
                email=admin_email,
                rola='admin',
                imie='Główny',
                nazwisko='Administrator',
                aktywny=True
            )
            admin_user.set_password('adminpass') # Change this default password!
            db.session.add(admin_user)
            print(f"Admin user '{admin_user.login}' created with email '{admin_email}'. Default password: 'adminpass'")
        else:
            print(f"Admin user with login '{admin_login}' already exists.")

        # Create a default manager user (example)
        manager_login = 'manager'
        manager_email = 'manager@example.com' # Make this configurable if needed
        if not Uzytkownik.query.filter_by(login=manager_login).first():
            manager_user = Uzytkownik(
                login=manager_login,
                email=manager_email,
                rola='manager',
                imie='Kierownik',
                nazwisko='Sklepu',
                aktywny=True
            )
            manager_user.set_password('managerpass') # Change this default password!
            db.session.add(manager_user)
            print(f"Manager user '{manager_user.login}' created with email '{manager_email}'. Default password: 'managerpass'")
        else:
            print(f"Manager user with login '{manager_login}' already exists.")
        
        db.session.commit() # Commit once after adding users
            
    print("Database initialized with default admin and manager.")

# Import and register custom CLI commands
from seed_data import seed_books_command
app.cli.add_command(seed_books_command)

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])