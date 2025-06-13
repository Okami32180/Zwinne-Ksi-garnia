from flask import render_template, request, current_app, redirect, url_for, flash
from . import main # Import the main blueprint
from aplikacja.models import db, Book, Kategoria, Gatunek, Wydawnictwo, SiteSetting # Import models & SiteSetting
# from aplikacja.books_service import search_google_books, get_popular_books # Assuming this will be refactored or replaced

# Placeholder for book services - to be refactored or integrated
def search_books_in_db(query=None, sort_by='tytul', genre_filter=None, min_price=None, max_price=None, page=1):
    books_query = Book.query.filter(Book.dostepny == True)

    if query:
        search_term = f"%{query}%"
        books_query = books_query.filter(
            db.or_(
                Book.tytul.ilike(search_term),
                Book.autor.ilike(search_term),
                Book.opis.ilike(search_term),
                Book.isbn.ilike(search_term)
            )
        )

    if genre_filter:
        # Assuming genre_filter is the ID of the Gatunek
        try:
            genre_id = int(genre_filter)
            books_query = books_query.filter(Book.gatunek_id == genre_id)
        except ValueError:
            flash("Nieprawidłowy filtr gatunku.", "warning")


    if min_price is not None:
        try:
            books_query = books_query.filter(Book.cena >= float(min_price))
        except ValueError:
            flash("Nieprawidłowa minimalna cena.", "warning")
            
    if max_price is not None:
        try:
            books_query = books_query.filter(Book.cena <= float(max_price))
        except ValueError:
            flash("Nieprawidłowa maksymalna cena.", "warning")

    # Sorting
    if sort_by == 'tytul_asc':
        books_query = books_query.order_by(Book.tytul.asc())
    elif sort_by == 'tytul_desc':
        books_query = books_query.order_by(Book.tytul.desc())
    elif sort_by == 'cena_asc':
        books_query = books_query.order_by(Book.cena.asc())
    elif sort_by == 'cena_desc':
        books_query = books_query.order_by(Book.cena.desc())
    elif sort_by == 'autor_asc':
        books_query = books_query.order_by(Book.autor.asc())
    elif sort_by == 'autor_desc':
        books_query = books_query.order_by(Book.autor.desc())
    elif sort_by == 'data_dodania_desc':
        books_query = books_query.order_by(Book.data_dodania.desc())
    else: # Default sort
        books_query = books_query.order_by(Book.tytul.asc())
        
    pagination = books_query.paginate(page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False)
    return pagination


@main.route("/")
@main.route("/index")
def index():
    page = request.args.get('page', 1, type=int)
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'tytul_asc')
    genre_filter_id = request.args.get('genre', '') # Expecting Gatunek ID
    min_price_str = request.args.get('min_price', '')
    max_price_str = request.args.get('max_price', '')

    min_price = float(min_price_str) if min_price_str else None
    max_price = float(max_price_str) if max_price_str else None
    
    books_pagination = search_books_in_db(
        query=query,
        sort_by=sort_by,
        genre_filter=genre_filter_id,
        min_price=min_price,
        max_price=max_price,
        page=page
    )
    
    all_genres = Gatunek.query.order_by(Gatunek.nazwa).all()
    
    return render_template('main/index.html', # Assuming templates will be in blueprint folders
                           books_pagination=books_pagination,
                           query=query,
                           sort_by=sort_by,
                           selected_genre_id=genre_filter_id,
                           min_price=min_price_str, # Pass string back for form repopulation
                           max_price=max_price_str, # Pass string back for form repopulation
                           all_genres=all_genres,
                           get_page_url=lambda p: url_for('.index', page=p, q=query, sort=sort_by, genre=genre_filter_id, min_price=min_price_str, max_price=max_price_str)
                           )

@main.route("/about")
def about():
    return render_template("main/about.html", title="O nas")

# Example error handlers for the main blueprint
@main.app_errorhandler(404) # Use app_errorhandler for global handlers if not in __init__
def page_not_found(e):
    return render_template('errors/404.html'), 404

@main.app_errorhandler(500)
def internal_server_error(e):
    db.session.rollback() # Rollback in case of DB error
    return render_template('errors/500.html'), 500

@main.app_errorhandler(403)
def forbidden_error(e):
    return render_template('errors/403.html'), 403