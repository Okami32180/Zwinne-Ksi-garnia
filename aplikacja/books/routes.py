from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user, login_required
from . import books # Blueprint import
from .forms import ReviewForm, SearchForm
from aplikacja import db
from aplikacja.models import Book, Recenzja, Kategoria, Gatunek, Uzytkownik, SiteSetting # Import SiteSetting
from sqlalchemy import func

def update_book_rating(book_id):
    """
    Recalculates and updates the average rating and number of ratings for a book.
    This should be called after a new review is approved or a review is deleted.
    """
    book = Book.query.get(book_id)
    if book:
        approved_reviews = Recenzja.query.filter_by(id_ksiazki=book_id, zatwierdzona=True)
        
        new_liczba_ocen = approved_reviews.count()
        new_srednia_ocen = approved_reviews.with_entities(func.avg(Recenzja.ocena)).scalar() or 0.0
        
        book.liczba_ocen = new_liczba_ocen
        book.srednia_ocen = round(new_srednia_ocen, 2)
        db.session.commit()

@books.route('/<int:book_id>')
@books.route('/details/<int:book_id>')
def book_details(book_id):
    book = Book.query.get_or_404(book_id)
    if not book.dostepny and (not current_user.is_authenticated or current_user.rola != 'admin'):
        flash("Ta książka nie jest aktualnie dostępna.", "info")
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    reviews_pagination = Recenzja.query.filter_by(id_ksiazki=book_id, zatwierdzona=True)\
                                     .order_by(Recenzja.data_dodania.desc())\
                                     .paginate(page=page, per_page=5, error_out=False) # 5 reviews per page
    
    review_form = None
    if current_user.is_authenticated:
        # Check if user has already reviewed this book
        user_review = Recenzja.query.filter_by(id_uzytkownika=current_user.id, id_ksiazki=book_id).first()
        if not user_review:
            review_form = ReviewForm(id_ksiazki=book_id)
            
    # Suggested books (simple example: same genre, different book)
    suggested_books = []
    if book.gatunek_ref:
        suggested_books = Book.query.filter(Book.gatunek_id == book.gatunek_id, Book.id != book.id, Book.dostepny == True)\
                                .order_by(func.random()).limit(4).all()
    if not suggested_books or len(suggested_books) < 4:
        # Fallback: recently added books, excluding current
        additional_needed = 4 - len(suggested_books)
        recent_books = Book.query.filter(Book.id != book.id, Book.dostepny == True)\
                                .order_by(Book.data_dodania.desc())\
                                .limit(additional_needed).all()
        suggested_books.extend(b for b in recent_books if b not in suggested_books)


    return render_template('books/book_details.html', title=book.tytul, book=book,
                           reviews_pagination=reviews_pagination, review_form=review_form,
                           suggested_books=suggested_books)

@books.route('/<int:book_id>/add_review', methods=['POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    form = ReviewForm(id_ksiazki=book_id) # id_ksiazki is a HiddenField
    
    if form.validate_on_submit():
        # Check if user has already reviewed this book
        existing_review = Recenzja.query.filter_by(id_uzytkownika=current_user.id, id_ksiazki=book_id).first()
        if existing_review:
            flash('Już zrecenzjowałeś/aś tę książkę.', 'warning')
            return redirect(url_for('books.book_details', book_id=book_id))
            
        review = Recenzja(
            ocena=form.ocena.data,
            komentarz=form.komentarz.data,
            id_uzytkownika=current_user.id,
            id_ksiazki=book_id,
            zatwierdzona=False # Reviews require admin approval by default
        )
        db.session.add(review)
        db.session.commit()
        flash('Twoja recenzja została dodana i oczekuje na zatwierdzenie.', 'success')
        return redirect(url_for('books.book_details', book_id=book_id))
    
    # If form validation fails, re-render the details page with errors
    page = request.args.get('page', 1, type=int)
    reviews_pagination = Recenzja.query.filter_by(id_ksiazki=book_id, zatwierdzona=True)\
                                     .order_by(Recenzja.data_dodania.desc())\
                                     .paginate(page=page, per_page=5, error_out=False)
    suggested_books = Book.query.filter(Book.gatunek_id == book.gatunek_id, Book.id != book.id, Book.dostepny == True)\
                                .order_by(func.random()).limit(4).all() # Duplicated logic, consider helper
    
    return render_template('books/book_details.html', title=book.tytul, book=book,
                           reviews_pagination=reviews_pagination, review_form=form, # Pass the invalid form back
                           suggested_books=suggested_books)


@books.route('/category/<int:category_id>')
def books_by_category(category_id):
    kategoria = Kategoria.query.get_or_404(category_id)
    page = request.args.get('page', 1, type=int)
    
    # Include books from subcategories if any
    # This requires a more complex query if you have deep nesting.
    # For a single level of subcategories:
    category_ids = [kategoria.id]
    for sub_kat in kategoria.podkategorie:
        category_ids.append(sub_kat.id)
        # For deeper nesting, this would need to be recursive or use CTEs in SQL.

    books_pagination = Book.query.join(Book.kategorie).filter(Kategoria.id.in_(category_ids), Book.dostepny == True)\
                               .order_by(Book.tytul.asc())\
                               .paginate(page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False)
    
    return render_template('books/books_list.html', title=f"Książki w kategorii: {kategoria.nazwa}",
                           books_pagination=books_pagination, list_title=f"Kategoria: {kategoria.nazwa}",
                           get_page_url=lambda p: url_for('.books_by_category', category_id=category_id, page=p))

@books.route('/genre/<int:genre_id>')
def books_by_genre(genre_id):
    gatunek = Gatunek.query.get_or_404(genre_id)
    page = request.args.get('page', 1, type=int)
    books_pagination = Book.query.filter_by(gatunek_id=genre_id, dostepny=True)\
                               .order_by(Book.tytul.asc())\
                               .paginate(page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False)
    
    return render_template('books/books_list.html', title=f"Książki z gatunku: {gatunek.nazwa}",
                           books_pagination=books_pagination, list_title=f"Gatunek: {gatunek.nazwa}",
                           get_page_url=lambda p: url_for('.books_by_genre', genre_id=genre_id, page=p))

@books.route('/search', methods=['GET', 'POST']) # Allow POST if search form submits to here
def search():
    # This route might be redundant if main.index handles search well.
    # It can be a dedicated search results page.
    query = request.args.get('q', request.form.get('query', '')).strip() # Handles GET and POST search
    page = request.args.get('page', 1, type=int)
    
    if not query:
        flash("Proszę wpisać frazę do wyszukania.", "info")
        return redirect(url_for('main.index')) # Or render a search page with a form

    # Using the search logic from main.routes as a base
    from aplikacja.main.routes import search_books_in_db # Temporary import, ideally refactor search_books_in_db
    
    books_pagination = search_books_in_db(query=query, page=page)
    all_genres = Gatunek.query.order_by(Gatunek.nazwa).all() # For potential filtering on results page

    return render_template('main/index.html', # Or a dedicated 'search_results.html'
                           books_pagination=books_pagination,
                           query=query,
                           sort_by='tytul_asc', # Default sort for search results
                           selected_genre_id=None,
                           min_price=None,
                           max_price=None,
                           all_genres=all_genres,
                           list_title=f"Wyniki wyszukiwania dla: '{query}'",
                           get_page_url=lambda p: url_for('.search', q=query, page=p))

# This route is now in main.routes.py, this is a placeholder if you want a dedicated page.
# @books.route('/')
# def list_all_books():
#     page = request.args.get('page', 1, type=int)
#     books_pagination = Book.query.filter_by(dostepny=True).order_by(Book.tytul.asc()).paginate(
#         page=page, per_page=current_app.config.get('BOOKS_PER_PAGE', 10), error_out=False
#     )
#     return render_template('books/books_list.html', title="Wszystkie Książki",
#                            books_pagination=books_pagination, list_title="Wszystkie Książki",
#                            get_page_url=lambda p: url_for('.list_all_books', page=p))