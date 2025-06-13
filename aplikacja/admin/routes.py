from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from . import admin
from .forms import EditUserProfileForm, BookForm, KategoriaForm, GatunekForm, WydawnictwoForm, SettingsForm
from aplikacja import db
from aplikacja.models import Uzytkownik, Book, Kategoria, Gatunek, Wydawnictwo, Zamowienie, Recenzja, Powiadomienie, SiteSetting # Import SiteSetting
from aplikacja.books.routes import update_book_rating # Import the function
from aplikacja.services.fake_payment_service import get_fake_payment_logs
from functools import wraps
from datetime import datetime
from decimal import Decimal # For precise financial calculations
from sqlalchemy import func # For SQL functions like sum, count, distinct

# Decorator for admin-only access (admin or manager)
def admin_manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rola not in ['admin', 'manager']:
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

# Decorator for admin-only access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rola not in ['admin']: # Strictly admin for some tasks
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function

@admin.before_request
@admin_manager_required # Most admin routes can be accessed by manager too
def before_request():
    """Protect all admin routes."""
    pass

@admin.route('/') # No specific decorator, before_request handles it
def dashboard():
    user_count = Uzytkownik.query.count()
    book_count = Book.query.count()
    order_count = Zamowienie.query.count()
    pending_reviews_count = Recenzja.query.filter_by(zatwierdzona=False).count()
    # For unread notifications, it's better to use the context processor value if available
    # or query directly if needed for a specific part of the dashboard logic.
    return render_template('admin/dashboard.html', title="Panel Administracyjny",
                           user_count=user_count, book_count=book_count,
                           order_count=order_count, pending_reviews_count=pending_reviews_count)

# User Management - only admin can delete/edit roles potentially
@admin.route('/users')
@admin_required # Restrict listing users to admin only
def list_users():
    page = request.args.get('page', 1, type=int)
    users_pagination = Uzytkownik.query.order_by(Uzytkownik.data_rejestracji.desc()).paginate(
        page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 15), expected_type=int), error_out=False
    )
    return render_template('admin/users_list.html', title="Zarządzanie Użytkownikami", users_pagination=users_pagination)

@admin.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required # Stricter for editing users
def edit_user(user_id):
    user = Uzytkownik.query.get_or_404(user_id)
    form = EditUserProfileForm(original_login=user.login, original_email=user.email, obj=user)
    if form.validate_on_submit():
        user.login = form.login.data
        user.email = form.email.data
        user.imie = form.imie.data
        user.nazwisko = form.nazwisko.data
        user.numer_telefonu = form.numer_telefonu.data
        user.rola = form.rola.data
        user.aktywny = form.aktywny.data
        db.session.commit()
        flash('Profil użytkownika został zaktualizowany.', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/edit_user.html', title="Edytuj Użytkownika", form=form, user=user)

@admin.route('/user/<int:user_id>/delete', methods=['POST'])
@admin_required # Stricter for deleting users
def delete_user(user_id):
    user = Uzytkownik.query.get_or_404(user_id)
    if user.rola == 'admin' or user.id == current_user.id: # Prevent deleting admins or self
        flash('Nie można usunąć tego użytkownika.', 'danger')
        return redirect(url_for('admin.list_users'))
    # Consider what to do with user's data (orders, reviews, etc.) - soft delete or anonymize?
    # For now, a hard delete:
    db.session.delete(user)
    db.session.commit()
    flash('Użytkownik został usunięty.', 'success')
    return redirect(url_for('admin.list_users'))

# Book Management
@admin.route('/books')
def list_books():
    page = request.args.get('page', 1, type=int)
    books_pagination = Book.query.order_by(Book.data_dodania.desc()).paginate(
        page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False
    )
    return render_template('admin/books_list.html', title="Zarządzanie Książkami", books_pagination=books_pagination)

@admin.route('/book/add', methods=['GET', 'POST'])
def add_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            tytul=form.tytul.data,
            autor=form.autor.data,
            isbn=form.isbn.data,
            opis=form.opis.data,
            okladka_url=form.okladka_url.data,
            gatunek_id=form.gatunek_id.data if form.gatunek_id.data else None,
            wydawnictwo_id=form.wydawnictwo_id.data if form.wydawnictwo_id.data else None,
            cena=form.cena.data,
            rok_wydania=form.rok_wydania.data,
            ilosc_stron=form.ilosc_stron.data,
            format_pliku=form.format_pliku.data,
            rozmiar_pliku_mb=form.rozmiar_pliku_mb.data,
            sciezka_pliku=form.sciezka_pliku.data, # Handle file upload/path generation securely
            dostepny=form.dostepny.data
        )
        # Handle categories
        selected_kategorie = Kategoria.query.filter(Kategoria.id.in_(form.kategorie_ids.data)).all()
        book.kategorie = selected_kategorie
        
        db.session.add(book)
        db.session.commit()
        flash('Książka została dodana.', 'success')
        return redirect(url_for('admin.list_books'))
    return render_template('admin/edit_book.html', title="Dodaj Książkę", form=form, book=None)

@admin.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    if form.validate_on_submit():
        book.tytul = form.tytul.data
        book.autor = form.autor.data
        book.isbn = form.isbn.data
        book.opis = form.opis.data
        book.okladka_url = form.okladka_url.data
        book.gatunek_id = form.gatunek_id.data if form.gatunek_id.data else None
        book.wydawnictwo_id = form.wydawnictwo_id.data if form.wydawnictwo_id.data else None
        book.cena = form.cena.data
        book.rok_wydania = form.rok_wydania.data
        book.ilosc_stron = form.ilosc_stron.data
        book.format_pliku = form.format_pliku.data
        book.rozmiar_pliku_mb = form.rozmiar_pliku_mb.data
        book.sciezka_pliku = form.sciezka_pliku.data
        book.dostepny = form.dostepny.data
        
        # Handle categories update
        selected_kategorie = Kategoria.query.filter(Kategoria.id.in_(form.kategorie_ids.data)).all()
        book.kategorie = selected_kategorie

        db.session.commit()
        flash('Książka została zaktualizowana.', 'success')
        return redirect(url_for('admin.list_books'))
    
    # Populate categories for the form when GET request
    form.kategorie_ids.data = [k.id for k in book.kategorie]
    return render_template('admin/edit_book.html', title="Edytuj Książkę", form=form, book=book)

@admin.route('/book/<int:book_id>/delete', methods=['POST'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    # Consider implications: orders with this book, reviews, etc.
    # Soft delete might be better: book.dostepny = False
    db.session.delete(book) # Hard delete for now
    db.session.commit()
    flash('Książka została usunięta.', 'success')
    return redirect(url_for('admin.list_books'))

# Category Management
@admin.route('/categories')
def list_categories():
    kategorie = Kategoria.query.order_by(Kategoria.nazwa).all()
    return render_template('admin/categories_list.html', title="Zarządzanie Kategoriami", kategorie=kategorie)

@admin.route('/category/add', methods=['GET', 'POST'])
def add_category():
    form = KategoriaForm()
    if form.validate_on_submit():
        kategoria = Kategoria(
            nazwa=form.nazwa.data, 
            opis=form.opis.data,
            nadkategoria_id=form.nadkategoria_id.data if form.nadkategoria_id.data else None
            )
        db.session.add(kategoria)
        db.session.commit()
        flash('Kategoria została dodana.', 'success')
        return redirect(url_for('admin.list_categories'))
    return render_template('admin/edit_category.html', title="Dodaj Kategorię", form=form, kategoria=None)

@admin.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
def edit_category(category_id):
    kategoria = Kategoria.query.get_or_404(category_id)
    form = KategoriaForm(obj=kategoria, _obj_id=kategoria.id) # Pass obj_id for validation
    if form.validate_on_submit():
        kategoria.nazwa = form.nazwa.data
        kategoria.opis = form.opis.data
        kategoria.nadkategoria_id = form.nadkategoria_id.data if form.nadkategoria_id.data else None
        db.session.commit()
        flash('Kategoria została zaktualizowana.', 'success')
        return redirect(url_for('admin.list_categories'))
    return render_template('admin/edit_category.html', title="Edytuj Kategorię", form=form, kategoria=kategoria)

@admin.route('/category/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    kategoria = Kategoria.query.get_or_404(category_id)
    if kategoria.ksiazki.count() > 0 or kategoria.podkategorie.count() > 0:
        flash('Nie można usunąć kategorii, która zawiera książki lub podkategorie. Usuń je najpierw lub przypisz do innej kategorii.', 'danger')
        return redirect(url_for('admin.list_categories'))
    db.session.delete(kategoria)
    db.session.commit()
    flash('Kategoria została usunięta.', 'success')
    return redirect(url_for('admin.list_categories'))

# Genre Management (similar to Categories)
@admin.route('/genres')
def list_genres():
    gatunki = Gatunek.query.order_by(Gatunek.nazwa).all()
    return render_template('admin/genres_list.html', title="Zarządzanie Gatunkami", gatunki=gatunki)

@admin.route('/genre/add', methods=['GET', 'POST'])
def add_genre():
    form = GatunekForm()
    if form.validate_on_submit():
        gatunek = Gatunek(nazwa=form.nazwa.data)
        try:
            db.session.add(gatunek)
            db.session.commit()
            flash('Gatunek został dodany.', 'success')
            return redirect(url_for('admin.list_genres'))
        except Exception as e: # Catch potential unique constraint errors
            db.session.rollback()
            flash(f'Błąd podczas dodawania gatunku: {e}', 'danger')
    return render_template('admin/edit_genre.html', title="Dodaj Gatunek", form=form, gatunek=None)

@admin.route('/genre/<int:genre_id>/edit', methods=['GET', 'POST'])
def edit_genre(genre_id):
    gatunek = Gatunek.query.get_or_404(genre_id)
    form = GatunekForm(obj=gatunek)
    if form.validate_on_submit():
        gatunek.nazwa = form.nazwa.data
        try:
            db.session.commit()
            flash('Gatunek został zaktualizowany.', 'success')
            return redirect(url_for('admin.list_genres'))
        except Exception as e:
            db.session.rollback()
            flash(f'Błąd podczas aktualizacji gatunku: {e}', 'danger')
    return render_template('admin/edit_genre.html', title="Edytuj Gatunek", form=form, gatunek=gatunek)

@admin.route('/genre/<int:genre_id>/delete', methods=['POST'])
def delete_genre(genre_id):
    gatunek = Gatunek.query.get_or_404(genre_id)
    if gatunek.ksiazki.count() > 0: # Check if Gatunek model has 'ksiazki' relationship
        flash('Nie można usunąć gatunku przypisanego do książek.', 'danger')
        return redirect(url_for('admin.list_genres'))
    db.session.delete(gatunek)
    db.session.commit()
    flash('Gatunek został usunięty.', 'success')
    return redirect(url_for('admin.list_genres'))


# Publisher Management (similar to Categories/Genres)
@admin.route('/publishers')
def list_publishers():
    wydawnictwa = Wydawnictwo.query.order_by(Wydawnictwo.nazwa).all()
    return render_template('admin/publishers_list.html', title="Zarządzanie Wydawnictwami", wydawnictwa=wydawnictwa)

@admin.route('/publisher/add', methods=['GET', 'POST'])
def add_publisher():
    form = WydawnictwoForm()
    if form.validate_on_submit():
        wydawnictwo = Wydawnictwo(nazwa=form.nazwa.data)
        try:
            db.session.add(wydawnictwo)
            db.session.commit()
            flash('Wydawnictwo zostało dodane.', 'success')
            return redirect(url_for('admin.list_publishers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Błąd podczas dodawania wydawnictwa: {e}', 'danger')
    return render_template('admin/edit_publisher.html', title="Dodaj Wydawnictwo", form=form, wydawnictwo=None)

@admin.route('/publisher/<int:publisher_id>/edit', methods=['GET', 'POST'])
def edit_publisher(publisher_id):
    wydawnictwo = Wydawnictwo.query.get_or_404(publisher_id)
    form = WydawnictwoForm(obj=wydawnictwo)
    if form.validate_on_submit():
        wydawnictwo.nazwa = form.nazwa.data
        try:
            db.session.commit()
            flash('Wydawnictwo zostało zaktualizowane.', 'success')
            return redirect(url_for('admin.list_publishers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Błąd podczas aktualizacji wydawnictwa: {e}', 'danger')
    return render_template('admin/edit_publisher.html', title="Edytuj Wydawnictwo", form=form, wydawnictwo=wydawnictwo)

@admin.route('/publisher/<int:publisher_id>/delete', methods=['POST'])
def delete_publisher(publisher_id):
    wydawnictwo = Wydawnictwo.query.get_or_404(publisher_id)
    if wydawnictwo.ksiazki.count() > 0: # Check if Wydawnictwo model has 'ksiazki' relationship
        flash('Nie można usunąć wydawnictwa przypisanego do książek.', 'danger')
        return redirect(url_for('admin.list_publishers'))
    db.session.delete(wydawnictwo)
    db.session.commit()
    flash('Wydawnictwo zostało usunięte.', 'success')
    return redirect(url_for('admin.list_publishers'))

# Order Management
@admin.route('/orders')
def list_orders():
    page = request.args.get('page', 1, type=int)
    orders_pagination = Zamowienie.query.order_by(Zamowienie.data_zamowienia.desc()).paginate(
        page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 15), expected_type=int), error_out=False
    )
    return render_template('admin/orders_list.html', title="Zarządzanie Zamówieniami", orders_pagination=orders_pagination)

@admin.route('/order/<int:order_id>')
def view_order(order_id):
    order = Zamowienie.query.get_or_404(order_id)
    return render_template('admin/view_order.html', title=f"Zamówienie #{order.id}", order=order)

@admin.route('/order/<int:order_id>/update_status', methods=['POST'])
def update_order_status(order_id):
    order = Zamowienie.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status: # Add validation for allowed statuses
        order.status = new_status
        db.session.commit()
        flash(f'Status zamówienia #{order.id} został zaktualizowany na "{new_status}".', 'success')
    else:
        flash('Nie podano nowego statusu.', 'warning')
    return redirect(url_for('admin.view_order', order_id=order.id))


# Review Management
@admin.route('/reviews')
def list_reviews():
    page = request.args.get('page', 1, type=int)
    # Filter for unapproved reviews first, then all
    reviews_pagination = Recenzja.query.order_by(Recenzja.zatwierdzona.asc(), Recenzja.data_dodania.desc()).paginate(
        page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 15), expected_type=int), error_out=False
    )
    return render_template('admin/reviews_list.html', title="Zarządzanie Recenzjami", reviews_pagination=reviews_pagination)

@admin.route('/review/<int:review_id>/approve', methods=['POST'])
def approve_review(review_id):
    review = Recenzja.query.get_or_404(review_id)
    review.zatwierdzona = True
    db.session.commit()
    update_book_rating(review.id_ksiazki) # Call the imported function
    flash('Recenzja została zatwierdzona.', 'success')
    return redirect(url_for('admin.list_reviews'))

@admin.route('/review/<int:review_id>/delete', methods=['POST'])
def delete_review(review_id):
    review = Recenzja.query.get_or_404(review_id)
    book_id_for_rating_update = review.id_ksiazki
    is_approved_before_delete = review.zatwierdzona
    
    db.session.delete(review)
    db.session.commit()
    
    if is_approved_before_delete: # Only update rating if an approved review was deleted
        update_book_rating(book_id_for_rating_update)
    flash('Recenzja została usunięta.', 'success')
    return redirect(url_for('admin.list_reviews'))

# Site Settings (Example)
@admin.route('/settings', methods=['GET', 'POST'])
@admin_required # Only full admin can change site settings
def site_settings():
    form = SettingsForm()
    # Populate form with current settings from SiteSetting model
    if request.method == 'GET':
        form.books_per_page.data = SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int)
        form.admin_email.data = SiteSetting.get('ADMIN_EMAIL', default=current_app.config.get('ADMIN_EMAIL', 'admin@example.com'))
        # Example for a boolean setting if you add one to the form:
        # form.some_boolean_setting.data = SiteSetting.get('SOME_BOOLEAN_SETTING', default=False, expected_type=bool)

    if form.validate_on_submit():
        SiteSetting.set('BOOKS_PER_PAGE', form.books_per_page.data, value_type='integer')
        SiteSetting.set('ADMIN_EMAIL', form.admin_email.data, value_type='string')
        # Example for a boolean setting:
        # SiteSetting.set('SOME_BOOLEAN_SETTING', form.some_boolean_setting.data, value_type='boolean')
        try:
            db.session.commit()
            flash('Ustawienia zostały zapisane.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Błąd podczas zapisywania ustawień: {e}', 'danger')
        return redirect(url_for('admin.site_settings'))
    return render_template('admin/site_settings.html', title="Ustawienia Strony", form=form)

# Notifications
@admin.route('/notifications')
def list_notifications():
    page = request.args.get('page', 1, type=int)
    # Show notifications for admin/manager roles or specifically for this admin user
    # Unread first, then by date descending
    notifications_query = Powiadomienie.query.filter(
        (Powiadomienie.rola_docelowa.in_(['admin', 'manager'])) |
        (Powiadomienie.id_uzytkownika_docelowego == current_user.id)
    ).order_by(Powiadomienie.czy_przeczytane.asc(), Powiadomienie.data_utworzenia.desc())
    
    notifications_pagination = notifications_query.paginate(
        page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 20), expected_type=int), error_out=False
    )
    return render_template('admin/notifications_list.html', title="Powiadomienia Systemowe", notifications_pagination=notifications_pagination)

@admin.route('/notification/<int:notification_id>/mark_read', methods=['POST'])
def mark_as_read(notification_id):
    notification = Powiadomienie.query.get_or_404(notification_id)
    # Ensure the current admin/manager is authorized to mark this as read
    # (e.g., it's for their role or specifically for them)
    can_mark = (notification.rola_docelowa in [current_user.rola, 'admin', 'manager'] or # 'admin' can read 'manager' ones too
                  notification.id_uzytkownika_docelowego == current_user.id)

    if can_mark and not notification.czy_przeczytane:
        notification.czy_przeczytane = True
        notification.data_przeczytania = datetime.utcnow()
        db.session.commit()
        flash('Powiadomienie oznaczone jako przeczytane.', 'success')
    elif not can_mark:
        flash('Nie masz uprawnień do oznaczenia tego powiadomienia.', 'danger')
    else:
        flash('Powiadomienie było już oznaczone jako przeczytane.', 'info')
    
    return redirect(request.referrer or url_for('admin.list_notifications'))

@admin.route('/notifications/mark_all_read', methods=['POST'])
def mark_all_as_read():
    notifications_to_mark = Powiadomienie.query.filter(
        ((Powiadomienie.rola_docelowa.in_(['admin', 'manager'])) |
         (Powiadomienie.id_uzytkownika_docelowego == current_user.id)),
        Powiadomienie.czy_przeczytane == False
    ).all()

    for notification in notifications_to_mark:
        notification.czy_przeczytane = True
        notification.data_przeczytania = datetime.utcnow()
    
    if notifications_to_mark:
        db.session.commit()
        flash(f'Oznaczono {len(notifications_to_mark)} powiadomień jako przeczytane.', 'success')
    else:
        flash('Brak nowych powiadomień do oznaczenia.', 'info')
    return redirect(url_for('admin.list_notifications'))


# Fake Payment Logs
@admin.route('/payment_logs')
def list_payment_logs():
    page = request.args.get('page', 1, type=int)
    per_page = SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 20), expected_type=int)
    
    logs, total_logs = get_fake_payment_logs(page=page, per_page=per_page)
    
    # Manual pagination for list of dicts
    from flask_sqlalchemy.pagination import Pagination
    # The get_fake_payment_logs already returns a paginated slice and total.
    # We need to construct a Pagination object if we want to use the macro.
    # For simplicity, we can pass logs and total_logs and handle pagination in template or pass page numbers.
    
    # Let's try to make a simple pagination object for the macro
    # This is a bit of a hack as Pagination is usually for SQLAlchemy queries
    class ManualPagination:
        def __init__(self, page, per_page, total, items):
            self.page = page
            self.per_page = per_page
            self.total = total
            self.items = items
        
        @property
        def pages(self):
            if self.per_page == 0:
                return 0
            return (self.total + self.per_page - 1) // self.per_page

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        @property
        def prev_num(self):
            return self.page - 1 if self.has_prev else None

        @property
        def next_num(self):
            return self.page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=5):
            # Simplified iter_pages logic for manual pagination
            if self.pages <= (left_edge + left_current + right_edge + right_current + 1):
                return range(1, self.pages + 1)
            
            pages_to_show = []
            # Left edge
            pages_to_show.extend(range(1, left_edge + 1))
            pages_to_show.append(None) # Ellipsis

            # Current window
            start_curr = max(self.page - left_current, left_edge + 2)
            end_curr = min(self.page + right_current, self.pages - right_edge -1)
            
            if start_curr > left_edge + 2 : pages_to_show.append(None)
            pages_to_show.extend(range(start_curr, end_curr + 1))
            if end_curr < self.pages - right_edge -1 : pages_to_show.append(None)


            # Right edge
            pages_to_show.extend(range(self.pages - right_edge + 1, self.pages + 1))
            
            # Remove duplicate Nones and ensure unique page numbers
            final_pages = []
            last_p = -2
            for p in pages_to_show:
                if p is None and last_p is None:
                    continue
                if p is not None and p in final_pages: # Avoid duplicate page numbers if ranges overlap
                    if final_pages[-1] is None: # if previous was None, replace it
                        final_pages[-1] = p
                    # else skip
                else:
                     final_pages.append(p)
                last_p = p
            return final_pages


    payment_logs_pagination = ManualPagination(page=page, per_page=per_page, total=total_logs, items=logs)

    return render_template('admin/fake_payments_list.html', title="Logi Płatności (Fake)",
                           payment_logs_pagination=payment_logs_pagination)

# Reports Section
@admin.route('/reports')
@admin_required # Only admins can see reports
def reports_dashboard():
    return render_template('admin/reports_dashboard.html', title="Raporty")

@admin.route('/reports/sales')
@admin_required
def sales_report():
    total_orders = Zamowienie.query.filter(Zamowienie.status == 'zrealizowane').count()
    total_revenue_query = db.session.query(func.sum(Zamowienie.suma_calkowita)).filter(Zamowienie.status == 'zrealizowane').scalar()
    total_revenue = total_revenue_query if total_revenue_query is not None else Decimal('0.00')
    
    unique_customers = db.session.query(func.count(func.distinct(Zamowienie.id_uzytkownika)))\
                                 .filter(Zamowienie.status == 'zrealizowane')\
                                 .scalar() or 0

    return render_template('admin/sales_report_placeholder.html',
                           title="Raport Sprzedaży",
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           unique_customers=unique_customers)

@admin.route('/reports/popular_books')
@admin_required
def popular_books_report():
    from aplikacja.models import Zamowienie_Ksiazka # Import locally or at top if used elsewhere
    
    popular_books_data = db.session.query(
            Book.tytul,
            Book.autor,
            func.sum(Zamowienie_Ksiazka.ilosc).label('total_sold')
        ).join(Book, Zamowienie_Ksiazka.id_ksiazki == Book.id)\
        .join(Zamowienie, Zamowienie_Ksiazka.id_zamowienia == Zamowienie.id)\
        .filter(Zamowienie.status == 'zrealizowane')\
        .group_by(Book.id, Book.tytul, Book.autor)\
        .order_by(func.sum(Zamowienie_Ksiazka.ilosc).desc())\
        .limit(20).all() # Top 20 for example

    return render_template('admin/popular_books_report_placeholder.html',
                           title="Raport Popularności Książek",
                           popular_books=popular_books_data)

@admin.route('/reports/user_activity')
@admin_required
def user_activity_report():
    total_users = Uzytkownik.query.count()
    # Count users who have at least one 'zrealizowane' order
    users_with_orders = db.session.query(func.count(func.distinct(Zamowienie.id_uzytkownika)))\
                                  .filter(Zamowienie.status == 'zrealizowane')\
                                  .scalar() or 0
                                  
    return render_template('admin/user_activity_report_placeholder.html',
                           title="Raport Aktywności Użytkowników",
                           total_users=total_users,
                           users_with_orders=users_with_orders)