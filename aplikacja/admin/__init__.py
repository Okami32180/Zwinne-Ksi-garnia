from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import routes, forms # Import routes and forms