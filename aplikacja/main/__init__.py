from flask import Blueprint

main = Blueprint('main', __name__)

from . import routes, errors # Import routes and error handlers