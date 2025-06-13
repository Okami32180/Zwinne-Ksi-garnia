from flask import Blueprint

orders = Blueprint('orders', __name__)

from . import routes, forms # Import routes and forms