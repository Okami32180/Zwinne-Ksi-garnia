from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_wtf import FlaskForm # Import FlaskForm
from flask_login import current_user, login_required
from . import orders # Blueprint import
from .forms import CheckoutForm # GuestCheckoutForm can be added later
from aplikacja import db
from aplikacja.models import Book, Koszyk, ElementKoszyka, Zamowienie, Zamowienie_Ksiazka, Adres, Uzytkownik, DostepDoTresci, SiteSetting # Import SiteSetting
from aplikacja.cart.routes import get_or_create_cart
from aplikacja.services.fake_payment_service import process_fake_payment
from aplikacja.services.notification_service import notify_admins_and_managers, create_notification
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from flask import abort # Ensure abort is imported

def calculate_order_total(cart_items):
    total = Decimal('0.00')
    for item in cart_items:
        # Use price at the time of adding to cart if available, otherwise current price
        price_to_use = item.cena_w_momencie_dodania if item.cena_w_momencie_dodania is not None else item.ksiazka.cena
        total += item.ilosc * Decimal(price_to_use)
    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

@orders.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if current_user.is_authenticated and current_user.rola in ['admin', 'manager']:
        flash("Administratorzy i managerowie nie mają dostępu do procesu zamówienia.", "info")
        return redirect(url_for('admin.dashboard' if current_user.rola in ['admin', 'manager'] else 'main.index'))
    koszyk, _ = get_or_create_cart()
    if not koszyk or not koszyk.elementy_koszyka.count():
        flash('Twój koszyk jest pusty.', 'info')
        return redirect(url_for('cart.view_cart'))

    cart_items = koszyk.elementy_koszyka.all()
    order_total = calculate_order_total(cart_items)

    form = CheckoutForm()

    if request.method == 'GET':
        # Pre-fill form with user's default address if available
        default_address = Adres.query.filter_by(id_uzytkownika=current_user.id, domyslny=True, typ_adresu='rozliczeniowy').first()
        if not default_address and current_user.adresy.count() > 0: # Get any address if no default
             default_address = current_user.adresy.first()

        if default_address:
            form.imie_rozliczeniowe.data = default_address.imie or current_user.imie
            form.nazwisko_rozliczeniowe.data = default_address.nazwisko or current_user.nazwisko
            form.email_rozliczeniowy.data = current_user.email # Always use current user's email for contact
            form.telefon_rozliczeniowy.data = default_address.numer_telefonu or current_user.numer_telefonu
            form.linia_adresu1_rozliczeniowe.data = default_address.linia_adresu1
            form.linia_adresu2_rozliczeniowe.data = default_address.linia_adresu2
            form.miasto_rozliczeniowe.data = default_address.miasto
            form.kod_pocztowy_rozliczeniowy.data = default_address.kod_pocztowy
            form.kraj_rozliczeniowy.data = default_address.kraj
        else: # Pre-fill with user profile data if no address
            form.imie_rozliczeniowe.data = current_user.imie
            form.nazwisko_rozliczeniowe.data = current_user.nazwisko
            form.email_rozliczeniowy.data = current_user.email
            form.telefon_rozliczeniowy.data = current_user.numer_telefonu


    if form.validate_on_submit():
        # Create or update billing address
        billing_address = Adres(
            id_uzytkownika=current_user.id,
            typ_adresu='rozliczeniowy',
            imie=form.imie_rozliczeniowe.data,
            nazwisko=form.nazwisko_rozliczeniowe.data,
            # email field is not on Adres model, user's email is primary contact
            linia_adresu1=form.linia_adresu1_rozliczeniowe.data,
            linia_adresu2=form.linia_adresu2_rozliczeniowe.data,
            miasto=form.miasto_rozliczeniowe.data,
            kod_pocztowy=form.kod_pocztowy_rozliczeniowy.data,
            kraj=form.kraj_rozliczeniowy.data,
            numer_telefonu=form.telefon_rozliczeniowy.data,
            domyslny=True # Consider logic for setting default address
        )
        # Simple logic: remove old default if setting a new one
        Adres.query.filter_by(id_uzytkownika=current_user.id, domyslny=True, typ_adresu='rozliczeniowy').update({'domyslny': False})
        db.session.add(billing_address)
        # We need to commit here to get billing_address.id for the order
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving billing address: {e}")
            flash("Wystąpił błąd podczas zapisywania adresu. Spróbuj ponownie.", "danger")
            return render_template('orders/checkout.html', title="Podsumowanie zamówienia", form=form, cart_items=cart_items, order_total=order_total)


        # Create Order
        nowe_zamowienie = Zamowienie(
            id_uzytkownika=current_user.id,
            status='oczekujace_na_platnosc', # Initial status
            suma_calkowita=order_total,
            adres_rozliczeniowy_id=billing_address.id,
            metoda_platnosci="fake_payment_system" # Hardcode to fake payment
        )
        db.session.add(nowe_zamowienie)
        
        # Add items to order
        for item_koszyka in cart_items:
            element_zamowienia = Zamowienie_Ksiazka(
                zamowienie=nowe_zamowienie,
                id_ksiazki=item_koszyka.id_ksiazki,
                ilosc=item_koszyka.ilosc,
                cena_jednostkowa_w_momencie_zakupu=item_koszyka.cena_w_momencie_dodania or item_koszyka.ksiazka.cena,
                format_pliku_zakupiony=item_koszyka.ksiazka.format_pliku
            )
            db.session.add(element_zamowienia)
        
        try:
            db.session.commit()
            order_id = nowe_zamowienie.id
            
            # Create notification for admin/manager about new order
            notify_admins_and_managers(
                typ='nowe_zamowienie',
                tresc=f"Złożono nowe zamówienie #{order_id} przez użytkownika {current_user.login} na kwotę {order_total:.2f} zł.",
                id_uzytkownika_zglaszajacego=current_user.id,
                link_docelowy=url_for('admin.view_order', order_id=order_id, _external=True)
            )
            
            session['pending_order_id'] = order_id
            # Redirect to the fake payment processing page
            return redirect(url_for('orders.process_fake_payment_page'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating order: {e}")
            flash("Wystąpił błąd podczas tworzenia zamówienia. Spróbuj ponownie.", "danger")
            # Don't delete address here, it might be a transient DB issue

    return render_template('orders/checkout.html', title="Podsumowanie zamówienia", form=form, cart_items=cart_items, order_total=order_total)

@orders.route('/process_fake_payment', methods=['GET', 'POST']) # Changed to allow POST from the simulation page
@login_required
def process_fake_payment_page(): # Renamed to avoid conflict if a direct processing endpoint was needed
    order_id = session.get('pending_order_id')
    if not order_id:
        flash("Brak zamówienia do przetworzenia.", "warning")
        return redirect(url_for('main.index'))

    zamowienie = Zamowienie.query.get_or_404(order_id)
    if zamowienie.id_uzytkownika != current_user.id:
        abort(403)
    
    if zamowienie.status != 'oczekujace_na_platnosc':
        flash("To zamówienie nie oczekuje już na płatność lub zostało już przetworzone.", "info")
        return redirect(url_for('orders.order_confirmation', order_id=order_id))

    if request.method == 'POST': # User clicked "Zapłać" on the simulation page
        # Simulate payment
        payment_result = process_fake_payment(
            order_id=zamowienie.id,
            user_id=current_user.id,
            amount=zamowienie.suma_calkowita
        )
        
        if payment_result["success"]:
            zamowienie.status = 'zrealizowane'
            zamowienie.id_transakcji_platnosci = payment_result.get("transaction_id")
            grant_access_to_purchased_content(zamowienie)
            
            koszyk = Koszyk.query.filter_by(id_uzytkownika=current_user.id).first()
            if koszyk:
                ElementKoszyka.query.filter_by(id_koszyka=koszyk.id).delete()
                koszyk.data_modyfikacji = datetime.utcnow()
            
            db.session.commit()

            notify_admins_and_managers(
                typ='platnosc_zrealizowana',
                tresc=f"Płatność dla zamówienia #{order_id} (Użytkownik: {current_user.login}) została pomyślnie przetworzona. Kwota: {zamowienie.suma_calkowita:.2f} zł.",
                id_uzytkownika_zglaszajacego=current_user.id,
                link_docelowy=url_for('admin.view_order', order_id=order_id, _external=True)
            )
            flash('Płatność zakończona sukcesem! Dziękujemy za zamówienie.', 'success')
            session.pop('pending_order_id', None)
            return redirect(url_for('orders.order_confirmation', order_id=order_id))
        else:
            zamowienie.status = 'blad_platnosci'
            zamowienie.id_transakcji_platnosci = payment_result.get("transaction_id")
            db.session.commit()
            notify_admins_and_managers(
                typ='blad_platnosci',
                tresc=f"Płatność dla zamówienia #{order_id} (Użytkownik: {current_user.login}) nie powiodła się.",
                id_uzytkownika_zglaszajacego=current_user.id,
                link_docelowy=url_for('admin.view_order', order_id=order_id, _external=True)
            )
            flash('Płatność nie powiodła się. Spróbuj ponownie lub skontaktuj się z obsługą.', 'danger')
            return redirect(url_for('orders.order_confirmation', order_id=order_id))

    # GET request: Show the payment simulation page
    form = FlaskForm() # Create a dummy form for CSRF token
    return render_template('orders/process_fake_payment.html', title="Symulacja Płatności", zamowienie=zamowienie, form=form)


def grant_access_to_purchased_content(zamowienie_instance):
    if zamowienie_instance:
        for item_zamowienia in zamowienie_instance.elementy_zamowienia:
            # Check if access already granted for this user/book/order combination
            exists = DostepDoTresci.query.filter_by(
                id_uzytkownika=zamowienie_instance.id_uzytkownika,
                id_ksiazki=item_zamowienia.id_ksiazki,
                id_zamowienia=zamowienie_instance.id
            ).first()
            if not exists:
                dostep = DostepDoTresci(
                    id_uzytkownika=zamowienie_instance.id_uzytkownika,
                    id_ksiazki=item_zamowienia.id_ksiazki,
                    id_zamowienia=zamowienie_instance.id,
                    format_pliku=item_zamowienia.format_pliku_zakupiony or item_zamowienia.ksiazka.format_pliku
                    # token_pobierania and data_waznosci_tokenu can be generated here if needed immediately
                )
                db.session.add(dostep)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error granting content access for order {zamowienie_instance.id}: {e}")


@orders.route('/payment/success/<int:order_id>')
@login_required
def order_payment_success(order_id): # This route is now mainly for displaying confirmation after fake payment
    # The actual logic of success is handled in process_fake_payment_page POST
    zamowienie = Zamowienie.query.get_or_404(order_id)
    if zamowienie.id_uzytkownika != current_user.id:
        abort(403)
    
    # This route is now mostly a display confirmation, actual success logic moved to process_fake_payment
    if zamowienie.status == 'zrealizowane':
        flash('Płatność zakończona sukcesem! Dziękujemy za zamówienie.', 'success')
    elif zamowienie.status == 'blad_platnosci':
        flash('Płatność nie powiodła się. Spróbuj ponownie lub skontaktuj się z obsługą.', 'danger')
    # Other statuses might also land here if redirected.
    
    return redirect(url_for('orders.order_confirmation', order_id=order_id))


@orders.route('/payment/cancel/<int:order_id>', methods=['GET','POST']) # Allow POST if a form submits here
@login_required
def order_payment_cancel(order_id): # This might be called if user cancels from fake payment page
    zamowienie = Zamowienie.query.get_or_404(order_id)
    if zamowienie.id_uzytkownika != current_user.id:
        abort(403)
    
    original_status = zamowienie.status
    if zamowienie.status == 'oczekujace_na_platnosc':
        zamowienie.status = 'anulowane_przez_uzytkownika'
        db.session.commit()
        notify_admins_and_managers(
            typ='zamowienie_anulowane',
            tresc=f"Użytkownik {current_user.login} anulował zamówienie #{order_id} przed dokonaniem płatności.",
            id_uzytkownika_zglaszajacego=current_user.id,
            link_docelowy=url_for('admin.view_order', order_id=order_id, _external=True)
        )
        flash('Zamówienie zostało anulowane.', 'warning')
    elif original_status == 'anulowane_przez_uzytkownika':
         flash('Zamówienie zostało już wcześniej anulowane.', 'info')
    else:
        flash(f'Nie można anulować zamówienia w statusie "{original_status}".', 'info')

    session.pop('pending_order_id', None)
    return redirect(url_for('orders.order_confirmation', order_id=order_id))


@orders.route('/confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    zamowienie = Zamowienie.query.join(Uzytkownik).filter(Zamowienie.id == order_id).first_or_404()
    if zamowienie.id_uzytkownika != current_user.id and current_user.rola != 'admin':
        abort(403)
    return render_template('orders/order_confirmation.html', title="Potwierdzenie Zamówienia", zamowienie=zamowienie)

@orders.route('/history')
@login_required
def order_history():
    page = request.args.get('page', 1, type=int)
    orders_pagination = Zamowienie.query.filter_by(id_uzytkownika=current_user.id)\
                                    .order_by(Zamowienie.data_zamowienia.desc())\
                                    .paginate(page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False)
    return render_template('orders/order_history.html', title="Historia Zamówień", orders_pagination=orders_pagination)

@orders.route('/details/<int:order_id>')
@login_required
def view_order_details(order_id): # Renamed to avoid conflict with admin.view_order if it were global
    zamowienie = Zamowienie.query.get_or_404(order_id)
    if zamowienie.id_uzytkownika != current_user.id and current_user.rola != 'admin':
        abort(403) # Ensure user can only see their own orders, or admin can see any
    return render_template('orders/order_details.html', title=f"Szczegóły Zamówienia #{zamowienie.id}", zamowienie=zamowienie)

# Stripe Webhook (optional, for more robust payment confirmation)
# @orders.route('/stripe_webhook', methods=['POST'])
# def stripe_webhook():
#     payload = request.get_data(as_text=True)
#     sig_header = request.headers.get('Stripe-Signature')
#     endpoint_secret = current_app.config.get('STRIPE_ENDPOINT_SECRET')
#     event = None

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
#     except ValueError as e: # Invalid payload
#         return 'Invalid payload', 400
#     except stripe.error.SignatureVerificationError as e: # Invalid signature
#         return 'Invalid signature', 400

#     # Handle the event
#     if event.type == 'checkout.session.completed':
#         session = event.data.object
#         order_id = session.metadata.get('order_id')
#         if order_id:
#             zamowienie = Zamowienie.query.get(order_id)
#             if zamowienie and zamowienie.status == 'oczekujace_na_platnosc':
#                 if session.payment_status == 'paid':
#                     zamowienie.status = 'zrealizowane'
#                     zamowienie.id_platnosci_gateway = session.id # or session.payment_intent
#                     grant_access_to_purchased_content(zamowienie)
                            
#                     # Clear cart for the user associated with the order
#                     user_of_order = Uzytkownik.query.get(zamowienie.id_uzytkownika)
#                     if user_of_order:
#                         koszyk = Koszyk.query.filter_by(id_uzytkownika=user_of_order.id).first()
#                         if koszyk:
#                             ElementKoszyka.query.filter_by(id_koszyka=koszyk.id).delete()
#                             koszyk.data_modyfikacji = datetime.utcnow()
                    
#                     db.session.commit()
#                     # Send email confirmation etc.
#     # ... handle other event types
#     return 'Success', 200