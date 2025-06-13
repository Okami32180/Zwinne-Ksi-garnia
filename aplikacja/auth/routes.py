from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from aplikacja import db, login_manager
from aplikacja.models import Uzytkownik, Koszyk
from .forms import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm
from urllib.parse import urlparse, urljoin
from aplikacja.services.notification_service import notify_admins_and_managers, create_notification
import secrets # For generating secure tokens
from datetime import datetime, timedelta

@login_manager.user_loader
def load_user(user_id):
    return Uzytkownik.query.get(int(user_id))

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Uzytkownik.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.aktywny:
            login_user(user, remember=form.remember_me.data)
            
            # Merge session cart with user cart if applicable
            session_cart_id = request.cookies.get('cart_session_id')
            if session_cart_id:
                session_koszyk = Koszyk.query.filter_by(id_sesji=session_cart_id).first()
                if session_koszyk:
                    user_koszyk = Koszyk.query.filter_by(id_uzytkownika=user.id).first()
                    if not user_koszyk:
                        user_koszyk = Koszyk(id_uzytkownika=user.id)
                        db.session.add(user_koszyk)
                    
                    for item_session in session_koszyk.elementy_koszyka:
                        # Check if item already in user's cart, update quantity or add new
                        item_user = next((i for i in user_koszyk.elementy_koszyka if i.id_ksiazki == item_session.id_ksiazki), None)
                        if item_user:
                            item_user.ilosc += item_session.ilosc
                        else:
                            item_session.koszyk = user_koszyk # Reassign item to user's cart
                            item_session.id_koszyka = user_koszyk.id # Ensure FK is updated
                    
                    # Clean up session cart after merging
                    db.session.delete(session_koszyk)
                    db.session.commit()
                    # Consider deleting the cookie as well
                    # response.delete_cookie('cart_session_id')

            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('main.index')
            flash('Zalogowano pomyślnie.', 'success')
            return redirect(next_page)
        elif user and not user.aktywny:
            flash('Twoje konto jest nieaktywne. Skontaktuj się z administratorem.', 'warning')
        else:
            flash('Nieprawidłowy email lub hasło.', 'danger')
    return render_template('auth/login.html', title='Logowanie', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Wylogowano pomyślnie.', 'success')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Uzytkownik(
            login=form.login.data,
            email=form.email.data,
            aktywny=True # Activate user immediately for simplicity
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Create notification for admin/manager
        notify_admins_and_managers(
            typ='nowy_uzytkownik',
            tresc=f"Zarejestrowano nowego użytkownika: {user.login} ({user.email}).",
            id_uzytkownika_zglaszajacego=user.id,
            link_docelowy=url_for('admin.edit_user', user_id=user.id, _external=True)
        )
        
        flash('Rejestracja zakończona sukcesem! Możesz się teraz zalogować.', 'success')
        login_user(user) # Log in the user directly
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', title='Rejestracja', form=form)

@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = Uzytkownik.query.filter_by(email=form.email.data).first()
        if user:
            # Generate a simple token and store it (replace with a more robust method if needed)
            token = secrets.token_urlsafe(32)
            user.reset_hasla_token = token
            user.reset_hasla_token_expiration = datetime.utcnow() + timedelta(hours=1) # Token valid for 1 hour
            db.session.commit()
            
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            # Create notification for admin/manager about password reset request
            notify_admins_and_managers(
                typ='zadanie_resetu_hasla',
                tresc=f"Użytkownik {user.login} ({user.email}) poprosił o reset hasła. Link do resetu (dla celów demonstracyjnych): {reset_url}",
                id_uzytkownika_zglaszajacego=user.id,
                link_docelowy=url_for('admin.edit_user', user_id=user.id, _external=True)
            )
            # For the user, normally an email would be sent. Here, we flash a message with the link for demo purposes.
            flash(f'Żądanie resetu hasła zostało przetworzone. W systemie demonstracyjnym, użyj tego linku: {reset_url}', 'info')
        else:
            flash('Jeśli ten email istnieje w naszej bazie, przetworzono żądanie resetu hasła.', 'info') # Generic message
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Resetowanie Hasła', form=form)

@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = Uzytkownik.query.filter_by(reset_hasla_token=token).first()

    if not user or user.reset_hasla_token_expiration < datetime.utcnow():
        flash('Token resetowania hasła jest nieprawidłowy lub wygasł.', 'warning')
        return redirect(url_for('auth.reset_password_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_hasla_token = None # Invalidate the token
        user.reset_hasla_token_expiration = None
        db.session.commit()

        # Create notification for admin/manager
        notify_admins_and_managers(
            typ='haslo_zresetowane',
            tresc=f"Hasło dla użytkownika {user.login} ({user.email}) zostało pomyślnie zresetowane.",
            id_uzytkownika_zglaszajacego=user.id
        )
        flash('Twoje hasło zostało zresetowane. Możesz się teraz zalogować.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', title='Resetowanie Hasła', form=form, token=token)

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.aktywny: # Assuming 'aktywny' means confirmed
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html', title='Konto niepotwierdzone')

# Add more routes as needed: confirm_email, resend_confirmation_email, change_password, change_email_request, change_email