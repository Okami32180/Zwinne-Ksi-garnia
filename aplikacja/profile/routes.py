from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import current_user, login_required
from . import profile # Blueprint import
from .forms import UpdateProfileForm, ChangePasswordForm, AddressForm
from aplikacja import db
from aplikacja.models import Uzytkownik, Adres, DostepDoTresci, Book, SiteSetting # Import SiteSetting
from werkzeug.utils import secure_filename # For potential file uploads like avatars
import os
from datetime import datetime, timedelta
import uuid # For download tokens

@profile.before_request
@login_required # All routes in this blueprint require login
def before_request():
    pass

@profile.route('/')
def dashboard():
    # Fetch some user-specific data for the dashboard
    order_count = current_user.zamowienia.count()
    purchased_ebooks_count = current_user.dostepy_do_tresci.count()
    # Add more stats as needed
    return render_template('profile/dashboard.html', title="Mój Profil",
                           order_count=order_count, purchased_ebooks_count=purchased_ebooks_count)

@profile.route('/edit', methods=['GET', 'POST'])
def edit_profile():
    form = UpdateProfileForm(obj=current_user) # Pre-populate with current_user data
    if form.validate_on_submit():
        current_user.login = form.login.data
        current_user.email = form.email.data
        current_user.imie = form.imie.data
        current_user.nazwisko = form.nazwisko.data
        current_user.numer_telefonu = form.numer_telefonu.data
        db.session.commit()
        flash('Twój profil został zaktualizowany.', 'success')
        return redirect(url_for('profile.dashboard'))
    return render_template('profile/edit_profile.html', title="Edytuj Profil", form=form)

@profile.route('/change_password', methods=['GET', 'POST'])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Twoje hasło zostało zmienione.', 'success')
        return redirect(url_for('profile.dashboard'))
    return render_template('profile/change_password.html', title="Zmień Hasło", form=form)

@profile.route('/addresses')
def list_addresses():
    adresy = current_user.adresy.order_by(Adres.domyslny.desc(), Adres.typ_adresu).all()
    return render_template('profile/addresses_list.html', title="Moje Adresy", adresy=adresy)

@profile.route('/address/add', methods=['GET', 'POST'])
def add_address():
    form = AddressForm()
    if form.validate_on_submit():
        nowy_adres = Adres(
            id_uzytkownika=current_user.id,
            typ_adresu=form.typ_adresu.data,
            imie=form.imie.data,
            nazwisko=form.nazwisko.data,
            linia_adresu1=form.linia_adresu1.data,
            linia_adresu2=form.linia_adresu2.data,
            miasto=form.miasto.data,
            kod_pocztowy=form.kod_pocztowy.data,
            kraj=form.kraj.data,
            numer_telefonu=form.numer_telefonu.data,
            domyslny=form.domyslny.data
        )
        if nowy_adres.domyslny: # If setting as default, unset other defaults of the same type
            Adres.query.filter_by(id_uzytkownika=current_user.id, typ_adresu=nowy_adres.typ_adresu, domyslny=True)\
                 .update({'domyslny': False})
        
        db.session.add(nowy_adres)
        db.session.commit()
        flash('Nowy adres został dodany.', 'success')
        return redirect(url_for('profile.list_addresses'))
    return render_template('profile/edit_address.html', title="Dodaj Adres", form=form, adres=None)

@profile.route('/address/<int:address_id>/edit', methods=['GET', 'POST'])
def edit_address(address_id):
    adres = Adres.query.get_or_404(address_id)
    if adres.id_uzytkownika != current_user.id:
        abort(403) # User can only edit their own addresses
    
    form = AddressForm(obj=adres)
    if form.validate_on_submit():
        adres.typ_adresu = form.typ_adresu.data
        adres.imie = form.imie.data
        adres.nazwisko = form.nazwisko.data
        adres.linia_adresu1 = form.linia_adresu1.data
        adres.linia_adresu2 = form.linia_adresu2.data
        adres.miasto = form.miasto.data
        adres.kod_pocztowy = form.kod_pocztowy.data
        adres.kraj = form.kraj.data
        adres.numer_telefonu = form.numer_telefonu.data
        
        if form.domyslny.data and not adres.domyslny: # If changed to default
            Adres.query.filter_by(id_uzytkownika=current_user.id, typ_adresu=adres.typ_adresu, domyslny=True)\
                 .filter(Adres.id != adres.id)\
                 .update({'domyslny': False})
        adres.domyslny = form.domyslny.data
        
        db.session.commit()
        flash('Adres został zaktualizowany.', 'success')
        return redirect(url_for('profile.list_addresses'))
    return render_template('profile/edit_address.html', title="Edytuj Adres", form=form, adres=adres)

@profile.route('/address/<int:address_id>/delete', methods=['POST'])
def delete_address(address_id):
    adres = Adres.query.get_or_404(address_id)
    if adres.id_uzytkownika != current_user.id:
        abort(403)
    
    # Check if address is used in any non-completed orders (optional, depends on business logic)
    # For now, allow deletion.
    db.session.delete(adres)
    db.session.commit()
    flash('Adres został usunięty.', 'success')
    return redirect(url_for('profile.list_addresses'))

@profile.route('/address/<int:address_id>/set_default', methods=['POST'])
def set_default_address(address_id):
    adres = Adres.query.get_or_404(address_id)
    if adres.id_uzytkownika != current_user.id:
        abort(403)

    Adres.query.filter_by(id_uzytkownika=current_user.id, typ_adresu=adres.typ_adresu, domyslny=True)\
         .filter(Adres.id != adres.id)\
         .update({'domyslny': False})
    adres.domyslny = True
    db.session.commit()
    flash(f'Adres został ustawiony jako domyślny {adres.typ_adresu}.', 'success')
    return redirect(url_for('profile.list_addresses'))


@profile.route('/my_ebooks')
def my_ebooks():
    page = request.args.get('page', 1, type=int)
    # dostepy = current_user.dostepy_do_tresci.order_by(DostepDoTresci.data_udzielenia_dostepu.desc()) # This is a dynamic relationship
    dostepy_pagination = DostepDoTresci.query.filter_by(id_uzytkownika=current_user.id)\
                                        .join(Book)\
                                        .order_by(DostepDoTresci.data_udzielenia_dostepu.desc())\
                                        .paginate(page=page, per_page=SiteSetting.get('BOOKS_PER_PAGE', default=current_app.config.get('BOOKS_PER_PAGE', 10), expected_type=int), error_out=False)
    
    return render_template('profile/my_ebooks.html', title="Moje Ebooki", dostepy_pagination=dostepy_pagination)


@profile.route('/download_ebook/<int:dostep_id>/<token>')
def download_ebook(dostep_id, token):
    dostep = DostepDoTresci.query.get_or_404(dostep_id)

    if dostep.id_uzytkownika != current_user.id:
        abort(403, "Nie masz uprawnień do pobrania tego pliku.")
    
    if dostep.token_pobierania != token:
        abort(403, "Nieprawidłowy token pobierania.")

    if dostep.data_waznosci_tokenu and dostep.data_waznosci_tokenu < datetime.utcnow():
        flash("Token pobierania wygasł. Wygeneruj nowy link.", "warning")
        return redirect(url_for('profile.my_ebooks'))

    if dostep.limit_pobran is not None and dostep.liczba_pobran >= dostep.limit_pobran:
        flash("Osiągnięto limit pobrań dla tego ebooka.", "warning")
        return redirect(url_for('profile.my_ebooks'))

    ebook_file_path = dostep.ksiazka.sciezka_pliku
    if not ebook_file_path or not os.path.isabs(ebook_file_path):
         # Assuming files are stored relative to a configured EBOOKS_FOLDER
        ebooks_dir = current_app.config.get('EBOOKS_STORAGE_PATH', os.path.join(current_app.instance_path, 'ebook_files'))
        secure_path = secure_filename(os.path.basename(ebook_file_path)) # Sanitize filename part
        full_path = os.path.join(ebooks_dir, secure_path)
    else: # If sciezka_pliku is absolute and trusted
        full_path = ebook_file_path


    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        current_app.logger.error(f"Ebook file not found for Dostep ID {dostep.id}: Path {full_path} (Original: {dostep.ksiazka.sciezka_pliku})")
        flash("Plik ebooka nie został znaleziony na serwerze. Skontaktuj się z administratorem.", "danger")
        abort(404)

    dostep.liczba_pobran += 1
    db.session.commit()
    
    # Determine filename for download
    download_filename = f"{secure_filename(dostep.ksiazka.tytul)}_{secure_filename(dostep.ksiazka.autor)}.{dostep.format_pliku or 'pdf'}"

    try:
        return send_from_directory(os.path.dirname(full_path), 
                                   os.path.basename(full_path), 
                                   as_attachment=True,
                                   download_name=download_filename) # Use download_name in Flask 2.0+
                                   # attachment_filename=download_filename for older Flask
    except Exception as e:
        current_app.logger.error(f"Error sending file: {e}")
        abort(500)


@profile.route('/generate_download_link/<int:dostep_id>', methods=['POST'])
def generate_download_link(dostep_id):
    dostep = DostepDoTresci.query.get_or_404(dostep_id)
    if dostep.id_uzytkownika != current_user.id:
        abort(403)

    if dostep.limit_pobran is not None and dostep.liczba_pobran >= dostep.limit_pobran:
        flash("Osiągnięto już limit pobrań dla tego ebooka.", "warning")
        return redirect(url_for('profile.my_ebooks'))

    dostep.token_pobierania = str(uuid.uuid4())
    dostep.data_waznosci_tokenu = datetime.utcnow() + timedelta(hours=current_app.config.get('EBOOK_DOWNLOAD_TOKEN_VALIDITY_HOURS', 24))
    # Resetting liczba_pobran on new link generation might be a business decision.
    # For now, it continues to count towards the overall limit.
    db.session.commit()

    download_url = url_for('profile.download_ebook', dostep_id=dostep.id, token=dostep.token_pobierania, _external=True)
    flash(f"Wygenerowano nowy link do pobrania. Link jest ważny przez {current_app.config.get('EBOOK_DOWNLOAD_TOKEN_VALIDITY_HOURS', 24)} godzin.", "success")
    # For UX, you might want to display this link or copy to clipboard,
    # but for simplicity, we'll just redirect. The user can click "Download" again.
    # Or, pass the URL to the template.
    
    # For now, just redirect back to my_ebooks, the template will show the new download button/link
    return redirect(url_for('profile.my_ebooks'))