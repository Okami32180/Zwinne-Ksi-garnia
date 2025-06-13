from flask import Blueprint

profile = Blueprint('profile', __name__)

from . import routes, forms # Import routes and forms