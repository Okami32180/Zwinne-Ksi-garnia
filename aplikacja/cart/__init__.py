from flask import Blueprint

cart = Blueprint('cart', __name__)

from . import routes, forms # Import routes and forms