from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, DecimalField, IntegerField, SelectField, FileField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from aplikacja.models import Uzytkownik, Kategoria, Gatunek, Wydawnictwo

class EditUserProfileForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    imie = StringField('Imię', validators=[Optional(), Length(max=50)])
    nazwisko = StringField('Nazwisko', validators=[Optional(), Length(max=50)])
    numer_telefonu = StringField('Numer telefonu', validators=[Optional(), Length(max=20)])
    rola = SelectField('Rola', choices=[('user', 'Użytkownik'), ('editor', 'Edytor'), ('admin', 'Administrator')], validators=[DataRequired()])
    aktywny = BooleanField('Aktywny')
    submit = SubmitField('Zapisz zmiany')

    def __init__(self, original_login, original_email, *args, **kwargs):
        super(EditUserProfileForm, self).__init__(*args, **kwargs)
        self.original_login = original_login
        self.original_email = original_email

    def validate_login(self, login):
        if login.data != self.original_login:
            user = Uzytkownik.query.filter_by(login=login.data).first()
            if user:
                raise ValidationError('Ten login jest już zajęty.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = Uzytkownik.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Ten adres email jest już używany.')

class BookForm(FlaskForm):
    tytul = StringField('Tytuł', validators=[DataRequired(), Length(max=200)])
    autor = StringField('Autor', validators=[DataRequired(), Length(max=200)])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=20)])
    opis = TextAreaField('Opis', validators=[Optional()])
    okladka_url = StringField('URL Okładki', validators=[Optional(), Length(max=255)])
    # okladka_plik = FileField('Plik Okładki (opcjonalnie, nadpisze URL)') # For file uploads
    
    gatunek_id = SelectField('Gatunek', coerce=int, validators=[Optional()])
    wydawnictwo_id = SelectField('Wydawnictwo', coerce=int, validators=[Optional()])
    
    kategorie_ids = SelectMultipleField('Kategorie', coerce=int, validators=[Optional()])

    cena = DecimalField('Cena', validators=[DataRequired(), NumberRange(min=0)], places=2)
    rok_wydania = IntegerField('Rok wydania', validators=[Optional(), NumberRange(min=1000, max=2100)])
    ilosc_stron = IntegerField('Ilość stron', validators=[Optional(), NumberRange(min=1)])
    format_pliku = StringField('Format pliku (np. PDF, EPUB)', default="PDF", validators=[Optional(), Length(max=50)])
    rozmiar_pliku_mb = DecimalField('Rozmiar pliku (MB)', validators=[Optional(), NumberRange(min=0)], places=2)
    sciezka_pliku = StringField('Ścieżka do pliku ebooka', validators=[DataRequired(), Length(max=255)]) # This might be handled differently (e.g. upload)
    dostepny = BooleanField('Dostępny w sprzedaży', default=True)
    submit = SubmitField('Zapisz książkę')

    def __init__(self, *args, **kwargs):
        super(BookForm, self).__init__(*args, **kwargs)
        self.gatunek_id.choices = [(g.id, g.nazwa) for g in Gatunek.query.order_by('nazwa').all()]
        self.gatunek_id.choices.insert(0, (0, '--- Wybierz gatunek ---')) # Optional placeholder
        
        self.wydawnictwo_id.choices = [(w.id, w.nazwa) for w in Wydawnictwo.query.order_by('nazwa').all()]
        self.wydawnictwo_id.choices.insert(0, (0, '--- Wybierz wydawnictwo ---')) # Optional placeholder

        self.kategorie_ids.choices = [(k.id, k.nazwa) for k in Kategoria.query.order_by('nazwa').all()]

    def validate_isbn(self, isbn):
        # Add ISBN validation logic if needed (e.g., check format or uniqueness if it's a new book)
        # For editing, ensure it's unique if changed.
        pass

class KategoriaForm(FlaskForm):
    nazwa = StringField('Nazwa kategorii', validators=[DataRequired(), Length(max=100)])
    opis = TextAreaField('Opis (opcjonalnie)', validators=[Optional()])
    nadkategoria_id = SelectField('Nadkategoria (opcjonalnie)', coerce=int, validators=[Optional()])
    submit = SubmitField('Zapisz kategorię')

    def __init__(self, *args, **kwargs):
        super(KategoriaForm, self).__init__(*args, **kwargs)
        self.nadkategoria_id.choices = [(k.id, k.nazwa) for k in Kategoria.query.order_by('nazwa').all()]
        self.nadkategoria_id.choices.insert(0, (0, '--- Brak nadkategorii ---')) # 0 or None for no parent

    def validate_nazwa(self, nazwa_field):
        # Add uniqueness validation if needed, especially for new categories
        # For editing, ensure it's unique if changed from original.
        kategoria_id = kwargs.get('_obj_id', None) # Pass obj_id if editing
        query = Kategoria.query.filter(Kategoria.nazwa == nazwa_field.data)
        if kategoria_id:
            query = query.filter(Kategoria.id != kategoria_id)
        if query.first():
            raise ValidationError('Kategoria o tej nazwie już istnieje.')


class GatunekForm(FlaskForm):
    nazwa = StringField('Nazwa gatunku', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Zapisz gatunek')

    def validate_nazwa(self, nazwa_field):
        # Similar uniqueness validation as KategoriaForm
        pass

class WydawnictwoForm(FlaskForm):
    nazwa = StringField('Nazwa wydawnictwa', validators=[DataRequired(), Length(max=150)])
    submit = SubmitField('Zapisz wydawnictwo')

    def validate_nazwa(self, nazwa_field):
        # Similar uniqueness validation
        pass

class SettingsForm(FlaskForm):
    # Example: Site-wide settings
    books_per_page = IntegerField('Książek na stronę (katalog)', validators=[DataRequired(), NumberRange(min=1, max=100)])
    admin_email = StringField('Email administratora', validators=[DataRequired(), Email()])
    submit = SubmitField('Zapisz ustawienia')