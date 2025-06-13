from flask import render_template, redirect, url_for, flash, request, make_response, current_app
from flask_login import current_user
from . import cart # Blueprint import
from .forms import AddToCartForm, UpdateCartItemForm, RemoveCartItemForm, ApplyPromoCodeForm
from aplikacja import db
from aplikacja.models import Book, Koszyk, ElementKoszyka, Promocja
import uuid # For session-based cart ID
from datetime import datetime, timedelta
from decimal import Decimal # For precise price calculations

def get_or_create_cart():
    """
    Retrieves the current user's cart or session-based cart.
    Creates a new cart if one doesn't exist.
    Returns the Koszyk object and a response object (to set cookies if needed).
    """
    response = make_response(redirect(url_for('cart.view_cart'))) # Default response
    koszyk = None

    if current_user.is_authenticated:
        koszyk = Koszyk.query.filter_by(id_uzytkownika=current_user.id).first()
        if not koszyk:
            koszyk = Koszyk(id_uzytkownika=current_user.id)
            db.session.add(koszyk)
            # No need to commit here if we are about to add items
    else:
        cart_session_id = request.cookies.get('cart_session_id')
        if cart_session_id:
            koszyk = Koszyk.query.filter_by(id_sesji=cart_session_id).first()
        
        if not koszyk:
            cart_session_id = str(uuid.uuid4())
            koszyk = Koszyk(id_sesji=cart_session_id)
            db.session.add(koszyk)
            # We need a response object to set the cookie
            # This will be handled by the calling route typically

    return koszyk, response


@cart.route('/')
def view_cart():
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Administratorzy i managerowie nie mają dostępu do funkcji koszyka.", "info")
        return redirect(url_for('admin.dashboard' if current_user.rola in ['admin', 'manager'] else 'main.index'))
    koszyk, _ = get_or_create_cart() # We don't need the response from here for viewing
    
    # If cart was just created (e.g., for anonymous user) and is empty, commit it.
    if koszyk and not koszyk.id: # Check if it's a new, uncommitted cart instance
        try:
            db.session.commit() # This will assign an ID if it's new
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error committing new cart: {e}")
            flash("Wystąpił błąd podczas tworzenia koszyka.", "danger")
            return redirect(url_for('main.index'))


    cart_items = []
    total_price = Decimal('0.00') # Initialize as Decimal

    if koszyk:
        cart_items = ElementKoszyka.query.filter_by(id_koszyka=koszyk.id).join(Book).all()
        for item in cart_items:
            # item.ksiazka.cena is already Decimal. item.ilosc is Integer.
            # Decimal * Integer results in Decimal.
            total_price += (Decimal(item.ilosc) * item.ksiazka.cena) # Ensure item.ilosc is also Decimal for safety, though not strictly needed here
    
    # Forms for cart page
    update_form = UpdateCartItemForm()
    remove_form = RemoveCartItemForm()
    promo_form = ApplyPromoCodeForm()

    return render_template('cart/view_cart.html', title="Mój Koszyk",
                           cart_items=cart_items, total_price=total_price,
                           update_form=update_form, remove_form=remove_form, promo_form=promo_form)

@cart.route('/add', methods=['POST'])
def add_to_cart():
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Administratorzy i managerowie nie mogą dodawać produktów do koszyka.", "danger")
        return redirect(request.referrer or url_for('main.index'))
    form = AddToCartForm() # This form might be submitted from book_details page
    response = make_response(redirect(request.referrer or url_for('cart.view_cart'))) # Default redirect

    if form.validate_on_submit():
        book_id = form.id_ksiazki.data
        quantity = form.ilosc.data
        book = Book.query.get_or_404(book_id)

        if not book.dostepny:
            flash("Ta książka jest obecnie niedostępna.", "warning")
            return response

        koszyk, cart_creation_response = get_or_create_cart()

        if not koszyk: # Should not happen if get_or_create_cart works
            flash("Nie udało się utworzyć lub znaleźć koszyka.", "danger")
            return response

        # If cart was newly created for an anonymous user, set the cookie
        if not current_user.is_authenticated and koszyk.id_sesji and not request.cookies.get('cart_session_id'):
            expires = datetime.utcnow() + timedelta(days=30)
            response.set_cookie('cart_session_id', koszyk.id_sesji, expires=expires, httponly=True, samesite='Lax')
        
        # Check if item already in cart
        cart_item = ElementKoszyka.query.filter_by(id_koszyka=koszyk.id, id_ksiazki=book.id).first()

        if cart_item:
            cart_item.ilosc += quantity
        else:
            cart_item = ElementKoszyka(
                id_koszyka=koszyk.id,
                id_ksiazki=book.id,
                ilosc=quantity,
                cena_w_momencie_dodania=book.cena # Store price at time of adding
            )
            db.session.add(cart_item)
        
        koszyk.data_modyfikacji = datetime.utcnow()
        try:
            db.session.commit()
            flash(f'Dodano "{book.tytul}" do koszyka.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding to cart: {e}")
            flash('Wystąpił błąd podczas dodawania do koszyka.', 'danger')
        
        return response # This response might have the cookie set

    # If form validation fails (e.g., from a dedicated add-to-cart page, not typical here)
    flash('Nie udało się dodać produktu do koszyka. Sprawdź dane.', 'danger')
    return response


@cart.route('/update/<int:item_id>', methods=['POST']) # item_id from URL is for identifying the item, not for form data
def update_cart_item(item_id):
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Niedozwolona operacja dla administratora/managera.", "danger")
        return redirect(url_for('main.index'))
    form = UpdateCartItemForm() # Instantiate without passing item_id here
    if form.validate_on_submit(): # validate_on_submit will use request.form
        # The form.id_elementu_koszyka.data should come from the hidden input in the template
        cart_item = ElementKoszyka.query.get_or_404(form.id_elementu_koszyka.data)
        # It's good practice to also verify item_id from URL matches form.id_elementu_koszyka.data
        if item_id != cart_item.id:
            flash("Niezgodność ID elementu koszyka.", "danger")
            return redirect(url_for('cart.view_cart'))
        koszyk = Koszyk.query.get(cart_item.id_koszyka)

        # Security check: ensure the item belongs to the current user's/session's cart
        if (current_user.is_authenticated and koszyk.id_uzytkownika != current_user.id) or \
           (not current_user.is_authenticated and koszyk.id_sesji != request.cookies.get('cart_session_id')):
            flash("Nieautoryzowana operacja.", "danger")
            return redirect(url_for('cart.view_cart'))

        new_quantity = form.ilosc.data
        if new_quantity > 0:
            cart_item.ilosc = new_quantity
            koszyk.data_modyfikacji = datetime.utcnow()
            db.session.commit()
            flash('Ilość zaktualizowana.', 'success')
        else: # If quantity is 0 or less, treat as removal
            db.session.delete(cart_item)
            koszyk.data_modyfikacji = datetime.utcnow()
            db.session.commit()
            flash('Produkt usunięty z koszyka.', 'success')
    else:
        # This case might happen if the form is submitted with errors from the cart page itself
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Błąd w polu '{getattr(form, field).label.text}': {error}", "danger")

    return redirect(url_for('cart.view_cart'))

@cart.route('/remove/<int:item_id>', methods=['POST'])
def remove_cart_item(item_id):
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Niedozwolona operacja dla administratora/managera.", "danger")
        return redirect(url_for('main.index'))
    # Using a simple direct removal, assuming item_id is passed directly
    # For form-based removal, use RemoveCartItemForm as in update_cart_item
    cart_item = ElementKoszyka.query.get_or_404(item_id)
    koszyk = Koszyk.query.get(cart_item.id_koszyka)

    # Security check
    if (current_user.is_authenticated and koszyk.id_uzytkownika != current_user.id) or \
       (not current_user.is_authenticated and koszyk.id_sesji != request.cookies.get('cart_session_id')):
        flash("Nieautoryzowana operacja.", "danger")
        return redirect(url_for('cart.view_cart'))

    db.session.delete(cart_item)
    koszyk.data_modyfikacji = datetime.utcnow()
    db.session.commit()
    flash('Produkt usunięty z koszyka.', 'success')
    return redirect(url_for('cart.view_cart'))

@cart.route('/clear', methods=['POST'])
def clear_cart():
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Niedozwolona operacja dla administratora/managera.", "danger")
        return redirect(url_for('main.index'))
    koszyk, _ = get_or_create_cart()
    if koszyk:
        ElementKoszyka.query.filter_by(id_koszyka=koszyk.id).delete()
        koszyk.data_modyfikacji = datetime.utcnow()
        db.session.commit()
        flash('Koszyk został opróżniony.', 'success')
    return redirect(url_for('cart.view_cart'))

@cart.route('/apply_promo', methods=['POST'])
def apply_promo_code():
    form = ApplyPromoCodeForm()
    if form.validate_on_submit():
        code = form.kod_promocyjny.data
        # Logic to validate and apply promo code
        # This is a placeholder. You'd look up the code in Promocja table,
        # check its validity, conditions, and then store it in session or cart model.
        promo = Promocja.query.filter_by(kod_promocyjny=code, aktywna=True).first()
        if promo:
            # Check date validity, usage limits, etc.
            # For now, just a simple check
            if promo.data_zakonczenia and promo.data_zakonczenia < datetime.utcnow():
                flash('Ten kod promocyjny wygasł.', 'warning')
            elif promo.max_uzyc is not None and promo.aktualne_uzycia >= promo.max_uzyc:
                 flash('Ten kod promocyjny został już wykorzystany maksymalną liczbę razy.', 'warning')
            else:
                # Store applied promo code, e.g., in session
                # session['promo_code_id'] = promo.id
                flash(f'Kod promocyjny "{promo.nazwa}" został zastosowany.', 'success')
                # Recalculate cart total if needed
        else:
            flash('Nieprawidłowy lub nieaktywny kod promocyjny.', 'danger')
    else:
        flash('Wprowadź kod promocyjny.', 'info')
    return redirect(url_for('cart.view_cart'))