from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, HiddenField, TextAreaField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Length, Email, Optional, Regexp

class CheckoutForm(FlaskForm):
    # Billing Address Fields
    imie_rozliczeniowe = StringField('Imię (rozliczeniowe)', validators=[DataRequired(), Length(max=50)])
    nazwisko_rozliczeniowe = StringField('Nazwisko (rozliczeniowe)', validators=[DataRequired(), Length(max=50)])
    email_rozliczeniowy = StringField('Email (rozliczeniowy)', validators=[DataRequired(), Email(), Length(max=120)])
    telefon_rozliczeniowy = StringField('Telefon (rozliczeniowy)', validators=[DataRequired(), Length(max=20)])
    linia_adresu1_rozliczeniowe = StringField('Adres - linia 1', validators=[DataRequired(), Length(max=100)])
    linia_adresu2_rozliczeniowe = StringField('Adres - linia 2', validators=[Optional(), Length(max=100)])
    miasto_rozliczeniowe = StringField('Miasto', validators=[DataRequired(), Length(max=50)])
    kod_pocztowy_rozliczeniowy = StringField('Kod pocztowy', 
                                           validators=[DataRequired(), 
                                                       Length(min=5, max=10, message="Nieprawidłowy format kodu pocztowego."),
                                                       Regexp(r'^\d{2}-\d{3}$|^\d{5}$', message="Nieprawidłowy format kodu pocztowego (np. 00-000 lub 00000).")])
    kraj_rozliczeniowy = SelectField('Kraj', choices=[('PL', 'Polska')], default='PL', validators=[DataRequired()]) # Add more countries if needed
    
    # Since ebooks don't have shipping, we might not need shipping address.
    # If physical goods were sold, you'd add:
    # uzyj_jako_wysylkowy = BooleanField('Użyj tego samego adresu do wysyłki', default=True)
    # imie_wysylkowe = StringField(...) etc.

    # Payment Method
    # This will likely be more complex with actual payment gateway integration
    # For now, a simple selection or it's handled by the gateway's UI.
    # metoda_platnosci = SelectField('Metoda płatności',
    #                              choices=[('stripe', 'Karta płatnicza (Stripe)'),
    #                                       ('paypal', 'PayPal'),
    #                                       ('przelew', 'Przelew bankowy')],
    #                              validators=[DataRequired()]) # Removed as we use fake payment only
    
    zgoda_regulamin = BooleanField('Akceptuję regulamin sklepu', validators=[DataRequired(message="Musisz zaakceptować regulamin.")])
    zgoda_newsletter = BooleanField('Zapisz mnie na newsletter (opcjonalnie)')

    uwagi_do_zamowienia = TextAreaField('Uwagi do zamówienia (opcjonalnie)', validators=[Optional(), Length(max=500)])

    submit = SubmitField('Złóż zamówienie i zapłać')

class GuestCheckoutForm(CheckoutForm): # Inherits from CheckoutForm
    # For guests, we might not pre-fill email or create an account by default
    # Or add a "create account" checkbox
    create_account = BooleanField('Stwórz konto z podanych danych (opcjonalnie)')
    password = PasswordField('Hasło dla nowego konta', validators=[Optional(), Length(min=8)])
    # No need for separate email_rozliczeniowy if it's the main email for guest