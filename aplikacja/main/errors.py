from flask import render_template
from . import main # Import the main blueprint
from aplikacja import db

@main.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    # It's good practice to rollback the session in case of a DB error
    # leading to a 500, though this might be better handled globally
    # or in a request teardown function.
    try:
        db.session.rollback()
    except Exception as ex:
        # Log this failure to rollback, as it might indicate a deeper issue
        current_app.logger.error(f"Failed to rollback session: {ex}")
    return render_template('errors/500.html'), 500