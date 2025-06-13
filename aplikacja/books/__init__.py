from flask import Blueprint

books = Blueprint('books', __name__)

from . import routes, forms # Import routes and forms