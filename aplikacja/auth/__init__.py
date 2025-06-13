from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import routes, forms # Import routes and forms