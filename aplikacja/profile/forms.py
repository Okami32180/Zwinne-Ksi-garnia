from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
from aplikacja.models import Uzytkownik # Assuming Uzytkownik model is in aplikacja.models
from flask_login import current_user

class UpdateProfileForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    imie = StringField('Imię', validators=[Optional(), Length(max=50)])
    nazwisko = StringField('Nazwisko', validators=[Optional(), Length(max=50)])
    numer_telefonu = StringField('Numer telefonu', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Zaktualizuj profil')

    def validate_login(self, login):
        if login.data != current_user.login:
            user = Uzytkownik.query.filter_by(login=login.data).first()
            if user:
                raise ValidationError('Ten login jest już zajęty. Proszę wybrać inny.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = Uzytkownik.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Ten adres email jest już używany. Proszę wybrać inny.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Obecne hasło', validators=[DataRequired()])
    new_password = PasswordField('Nowe hasło', validators=[DataRequired(), Length(min=8, message="Hasło musi mieć co najmniej 8 znaków.")])
    new_password2 = PasswordField(
        'Potwierdź nowe hasło', validators=[DataRequired(), EqualTo('new_password', message="Nowe hasła muszą się zgadzać.")])
    submit = SubmitField('Zmień hasło')

    def validate_current_password(self, current_password):
        if not current_user.check_password(current_password.data):
            raise ValidationError('Nieprawidłowe obecne hasło.')


class AddressForm(FlaskForm):
    typ_adresu = SelectField('Typ adresu', choices=[('rozliczeniowy', 'Rozliczeniowy'), ('wysylkowy', 'Wysyłkowy (dla e-booków nieużywany)')], default='rozliczeniowy', validators=[DataRequired()])
    imie = StringField('Imię', validators=[DataRequired(), Length(max=50)])
    nazwisko = StringField('Nazwisko', validators=[DataRequired(), Length(max=50)])
    linia_adresu1 = StringField('Adres - linia 1', validators=[DataRequired(), Length(max=100)])
    linia_adresu2 = StringField('Adres - linia 2', validators=[Optional(), Length(max=100)])
    miasto = StringField('Miasto', validators=[DataRequired(), Length(max=50)])
    kod_pocztowy = StringField('Kod pocztowy', 
                               validators=[DataRequired(), 
                                           Length(min=5, max=10, message="Nieprawidłowy format kodu pocztowego."),
                                           Regexp(r'^\d{2}-\d{3}$|^\d{5}$', message="Nieprawidłowy format kodu pocztowego (np. 00-000 lub 00000).")])
    kraj = SelectField('Kraj', choices=[('PL', 'Polska')], default='PL', validators=[DataRequired()]) # Add more countries if needed
    numer_telefonu = StringField('Numer telefonu', validators=[Optional(), Length(max=20)])
    domyslny = BooleanField('Ustaw jako domyślny adres tego typu')
    submit = SubmitField('Zapisz adres')