from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from aplikacja.models import Uzytkownik

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 120), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')

class RegistrationForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=8, message="Hasło musi mieć co najmniej 8 znaków.")])
    password2 = PasswordField(
        'Potwierdź hasło', validators=[DataRequired(), EqualTo('password', message="Hasła muszą się zgadzać.")])
    submit = SubmitField('Zarejestruj się')

    def validate_login(self, login):
        user = Uzytkownik.query.filter_by(login=login.data).first()
        if user:
            raise ValidationError('Ten login jest już zajęty. Proszę wybrać inny.')

    def validate_email(self, email):
        user = Uzytkownik.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Ten adres email jest już używany. Proszę wybrać inny.')

class RequestPasswordResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Zażądaj resetu hasła')

    def validate_email(self, email):
        user = Uzytkownik.query.filter_by(email=email.data).first()
        if not user:
            raise ValidationError('Nie znaleziono użytkownika z tym adresem email.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nowe hasło', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Potwierdź nowe hasło', validators=[DataRequired(), EqualTo('password', message="Hasła muszą się zgadzać.")])
    submit = SubmitField('Zresetuj hasło')