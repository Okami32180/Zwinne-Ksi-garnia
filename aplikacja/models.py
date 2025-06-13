from flask_sqlalchemy import SQLAlchemy
from . import db # Import the db instance from aplikacja/__init__.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
from sqlalchemy import event, inspect # Import inspect

# db = SQLAlchemy() # REMOVE THIS LINE - it creates a new, uninitialized instance

# Association table for many-to-many relationship between Book and Kategoria
ksiazka_kategoria_table = db.Table('Ksiazka_Kategoria',
    db.Column('id_ksiazki', db.Integer, db.ForeignKey('Ksiazka.id'), primary_key=True),
    db.Column('id_kategorii', db.Integer, db.ForeignKey('Kategoria.id'), primary_key=True)
)

class Uzytkownik(db.Model):
    __tablename__ = "Uzytkownik"
    
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    haslo_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False) # Still useful for login and communication if ever needed
    rola = db.Column(db.String(20), nullable=False, default='user') # e.g., 'user', 'admin', 'manager'
    data_rejestracji = db.Column(db.DateTime, default=datetime.utcnow)
    imie = db.Column(db.String(50), nullable=True)
    nazwisko = db.Column(db.String(50), nullable=True)
    numer_telefonu = db.Column(db.String(20), nullable=True)
    aktywny = db.Column(db.Boolean, default=True) # User activation might be instant or via admin
    ostatnie_logowanie = db.Column(db.DateTime, nullable=True)
    # adres_domyslny_id is defined after Adres model

    # Password reset token (simplified)
    reset_hasla_token = db.Column(db.String(128), nullable=True)
    reset_hasla_token_expiration = db.Column(db.DateTime, nullable=True)

    # Relacje
    zamowienia = db.relationship('Zamowienie', backref='uzytkownik', lazy='dynamic')
    recenzje = db.relationship('Recenzja', backref='uzytkownik', lazy='dynamic')
    adresy = db.relationship('Adres', foreign_keys='Adres.id_uzytkownika', backref='uzytkownik', lazy='dynamic')
    koszyk = db.relationship('Koszyk', backref='uzytkownik', uselist=False, lazy=True)
    dostepy_do_tresci = db.relationship('DostepDoTresci', backref='uzytkownik', lazy='dynamic')
    wyslane_powiadomienia = db.relationship('Powiadomienie', foreign_keys='Powiadomienie.id_uzytkownika_zglaszajacego', backref='zglaszajacy_uzytkownik', lazy='dynamic')
    otrzymane_powiadomienia = db.relationship('Powiadomienie', foreign_keys='Powiadomienie.id_uzytkownika_docelowego', backref='docelowy_uzytkownik', lazy='dynamic')


    def set_password(self, password):
        self.haslo_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.haslo_hash, password)

    def __repr__(self):
        return f'<Uzytkownik {self.login}>'

    @property
    def is_active(self):
        return self.aktywny

    @property
    def is_authenticated(self):
        # Assuming that if a user object exists and is active, they are authenticated.
        # For more complex scenarios (e.g., token-based auth), this might differ.
        return True # For a standard session-based login, this is fine.

    def get_id(self):
        return str(self.id)

class Gatunek(db.Model):
    __tablename__ = "Gatunek"
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(100), unique=True, nullable=False)
    ksiazki = db.relationship('Book', backref='gatunek_ref', lazy='dynamic', foreign_keys='Book.gatunek_id')

    def __repr__(self):
        return f'<Gatunek {self.nazwa}>'

class Wydawnictwo(db.Model):
    __tablename__ = "Wydawnictwo"
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(150), unique=True, nullable=False)
    ksiazki = db.relationship('Book', backref='wydawnictwo_ref', lazy='dynamic', foreign_keys='Book.wydawnictwo_id')

    def __repr__(self):
        return f'<Wydawnictwo {self.nazwa}>'

class Kategoria(db.Model):
    __tablename__ = "Kategoria"
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(100), unique=True, nullable=False)
    opis = db.Column(db.Text, nullable=True)
    nadkategoria_id = db.Column(db.Integer, db.ForeignKey('Kategoria.id'), nullable=True)
    podkategorie = db.relationship('Kategoria', backref=db.backref('nadkategoria', remote_side=[id]), lazy='dynamic')
    ksiazki = db.relationship('Book', secondary=ksiazka_kategoria_table, back_populates='kategorie', lazy='dynamic')

    def __repr__(self):
        return f'<Kategoria {self.nazwa}>'

class Book(db.Model):
    __tablename__ = "Ksiazka"
    id = db.Column(db.Integer, primary_key=True)
    tytul = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    opis = db.Column(db.Text, nullable=True)
    okladka_url = db.Column(db.String(255), nullable=True)
    gatunek_id = db.Column(db.Integer, db.ForeignKey('Gatunek.id'), nullable=True)
    wydawnictwo_id = db.Column(db.Integer, db.ForeignKey('Wydawnictwo.id'), nullable=True)
    cena = db.Column(db.Numeric(10,2), nullable=False)
    rok_wydania = db.Column(db.Integer, nullable=True)
    ilosc_stron = db.Column(db.Integer, nullable=True)
    format_pliku = db.Column(db.String(50), nullable=True, default="PDF")
    rozmiar_pliku_mb = db.Column(db.Numeric(6,2), nullable=True)
    sciezka_pliku = db.Column(db.String(255), nullable=False) # Relative to EBOOKS_STORAGE_PATH
    dostepny = db.Column(db.Boolean, default=True)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)
    srednia_ocen = db.Column(db.Numeric(3,2), default=0.00)
    liczba_ocen = db.Column(db.Integer, default=0)

    recenzje = db.relationship('Recenzja', backref='ksiazka', lazy='dynamic', cascade="all, delete-orphan")
    zamowienia_ksiazki = db.relationship('Zamowienie_Ksiazka', backref='ksiazka', lazy='dynamic') 
    kategorie = db.relationship('Kategoria', secondary=ksiazka_kategoria_table, back_populates='ksiazki', lazy='dynamic')
    elementy_koszyka = db.relationship('ElementKoszyka', backref='ksiazka', lazy='dynamic', cascade="all, delete-orphan")
    dostepy_do_tresci = db.relationship('DostepDoTresci', backref='ksiazka', lazy='dynamic', cascade="all, delete-orphan")
    
    @validates('cena')
    def validate_cena(self, key, cena):
        if cena is not None and cena < 0:
            raise ValueError("Cena nie może być ujemna.")
        return cena

    def __repr__(self):
        return f'<Book {self.tytul}>'

class Recenzja(db.Model):
    __tablename__ = "Recenzja"
    id = db.Column(db.Integer, primary_key=True)
    id_uzytkownika = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=False)
    id_ksiazki = db.Column(db.Integer, db.ForeignKey('Ksiazka.id'), nullable=False)
    ocena = db.Column(db.Integer, nullable=False)
    komentarz = db.Column(db.Text, nullable=True)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)
    zatwierdzona = db.Column(db.Boolean, default=False)

    @validates('ocena')
    def validate_ocena(self, key, ocena):
        if not 1 <= ocena <= 5:
            raise ValueError("Ocena musi być w zakresie od 1 do 5.")
        return ocena

    def __repr__(self):
        return f'<Recenzja {self.id_ksiazki} - {self.ocena}>'

# Listener to update book's average rating after a review is approved or deleted
@event.listens_for(Recenzja, 'after_insert')
@event.listens_for(Recenzja, 'after_update')
@event.listens_for(Recenzja, 'after_delete')
def update_book_rating_on_review_change(mapper, connection, target):
    # Correctly get history using sqlalchemy.inspect
    history = inspect(target).get_history('zatwierdzona', True)
    # Check if 'zatwierdzona' was True before deletion or is True now (for insert/update)
    if target.zatwierdzona or (history.deleted and history.deleted[0] is True): # history.deleted is a tuple
        book_id = target.id_ksiazki
        book = db.session.get(Book, book_id) # Use db.session.get for SQLAlchemy 2.0+
        if book:
            approved_reviews = db.session.query(Recenzja).filter_by(id_ksiazki=book_id, zatwierdzona=True).all()
            book.liczba_ocen = len(approved_reviews)
            if book.liczba_ocen > 0:
                book.srednia_ocen = round(sum(r.ocena for r in approved_reviews) / book.liczba_ocen, 2)
            else:
                book.srednia_ocen = 0.0
            # db.session.add(book) # Not needed if book is already in session and modified
            # db.session.commit() # Commit should happen at the end of request or transaction

class Koszyk(db.Model):
    __tablename__ = "Koszyk"
    id = db.Column(db.Integer, primary_key=True)
    id_uzytkownika = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), unique=True, nullable=True)
    id_sesji = db.Column(db.String(128), unique=True, nullable=True) # For anonymous users
    data_utworzenia = db.Column(db.DateTime, default=datetime.utcnow)
    data_modyfikacji = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    elementy_koszyka = db.relationship('ElementKoszyka', backref='koszyk', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Koszyk {self.id}>'

class ElementKoszyka(db.Model):
    __tablename__ = "ElementKoszyka"
    id = db.Column(db.Integer, primary_key=True)
    id_koszyka = db.Column(db.Integer, db.ForeignKey('Koszyk.id'), nullable=False)
    id_ksiazki = db.Column(db.Integer, db.ForeignKey('Ksiazka.id'), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False, default=1)
    cena_w_momencie_dodania = db.Column(db.Numeric(10,2), nullable=False)
    data_dodania = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ElementKoszyka {self.id_ksiazki} x {self.ilosc}>'

class Adres(db.Model):
    __tablename__ = "Adres"
    id = db.Column(db.Integer, primary_key=True)
    id_uzytkownika = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=False)
    typ_adresu = db.Column(db.String(50), nullable=False, default='rozliczeniowy') # 'rozliczeniowy', 'wysylkowy'
    imie = db.Column(db.String(50), nullable=True)
    nazwisko = db.Column(db.String(50), nullable=True)
    linia_adresu1 = db.Column(db.String(100), nullable=False)
    linia_adresu2 = db.Column(db.String(100), nullable=True)
    miasto = db.Column(db.String(50), nullable=False)
    kod_pocztowy = db.Column(db.String(20), nullable=False)
    kraj = db.Column(db.String(50), nullable=False)
    numer_telefonu = db.Column(db.String(20), nullable=True)
    domyslny = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Adres {self.id_uzytkownika} - {self.typ_adresu}>'

Uzytkownik.adres_domyslny_id = db.Column(db.Integer, db.ForeignKey('Adres.id'), nullable=True)
Uzytkownik.domyslny_adres_rozliczeniowy = db.relationship(
    'Adres',
    primaryjoin="and_(Uzytkownik.id==Adres.id_uzytkownika, Adres.typ_adresu=='rozliczeniowy', Adres.domyslny==True)",
    uselist=False,
    post_update=True, # Important for this type of relationship
    overlaps="adresy,uzytkownik" # Address the SAWarning
)


class Zamowienie(db.Model):
    __tablename__ = "Zamowienie"
    id = db.Column(db.Integer, primary_key=True)
    id_uzytkownika = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=False)
    data_zamowienia = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), default='oczekujace_na_platnosc') # e.g., 'oczekujace_na_platnosc', 'w_realizacji', 'zrealizowane', 'anulowane', 'blad_platnosci'
    suma_calkowita = db.Column(db.Numeric(10,2), nullable=False)
    adres_rozliczeniowy_id = db.Column(db.Integer, db.ForeignKey('Adres.id'), nullable=True)
    metoda_platnosci = db.Column(db.String(50), nullable=True, default="fake_payment")
    id_transakcji_platnosci = db.Column(db.String(100), nullable=True) # For fake payment log reference

    elementy_zamowienia = db.relationship('Zamowienie_Ksiazka', backref='zamowienie', lazy='dynamic', cascade="all, delete-orphan")
    dostepy_do_tresci = db.relationship('DostepDoTresci', backref='zamowienie', lazy='dynamic', cascade="all, delete-orphan")

    @validates('suma_calkowita')
    def validate_suma_calkowita(self, key, suma_calkowita):
        if suma_calkowita is not None and suma_calkowita < 0:
            raise ValueError("Suma całkowita zamówienia nie może być ujemna.")
        return suma_calkowita

    def __repr__(self):
        return f'<Zamowienie {self.id}>'

class Zamowienie_Ksiazka(db.Model):
    __tablename__ = "Zamowienie_Ksiazka"
    id = db.Column(db.Integer, primary_key=True)
    id_zamowienia = db.Column(db.Integer, db.ForeignKey('Zamowienie.id'), nullable=False)
    id_ksiazki = db.Column(db.Integer, db.ForeignKey('Ksiazka.id'), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False, default=1)
    cena_jednostkowa_w_momencie_zakupu = db.Column(db.Numeric(10,2), nullable=False)
    format_pliku_zakupiony = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<Zamowienie_Ksiazka {self.id_zamowienia}-{self.id_ksiazki}>'

class DostepDoTresci(db.Model):
    __tablename__ = "DostepDoTresci"
    id = db.Column(db.Integer, primary_key=True)
    id_uzytkownika = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=False)
    id_ksiazki = db.Column(db.Integer, db.ForeignKey('Ksiazka.id'), nullable=False)
    id_zamowienia = db.Column(db.Integer, db.ForeignKey('Zamowienie.id'), nullable=False)
    data_udzielenia_dostepu = db.Column(db.DateTime, default=datetime.utcnow)
    token_pobierania = db.Column(db.String(128), unique=True, nullable=True)
    liczba_pobran = db.Column(db.Integer, default=0)
    limit_pobran = db.Column(db.Integer, nullable=True, default=5) # Example limit
    data_waznosci_tokenu = db.Column(db.DateTime, nullable=True)
    format_pliku = db.Column(db.String(50))

    def __repr__(self):
        return f'<DostepDoTresci U:{self.id_uzytkownika} K:{self.id_ksiazki}>'

class Promocja(db.Model):
    __tablename__ = "Promocja"
    id = db.Column(db.Integer, primary_key=True)
    kod_promocyjny = db.Column(db.String(50), unique=True, nullable=True)
    nazwa = db.Column(db.String(100), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    znizka_procentowa = db.Column(db.Numeric(5,2), nullable=True)
    znizka_kwotowa = db.Column(db.Numeric(10,2), nullable=True)
    data_rozpoczecia = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_zakonczenia = db.Column(db.DateTime, nullable=True)
    aktywna = db.Column(db.Boolean, default=True)
    minimalna_wartosc_zamowienia = db.Column(db.Numeric(10,2), nullable=True)
    jednorazowy_na_uzytkownika = db.Column(db.Boolean, default=False)
    max_uzyc = db.Column(db.Integer, nullable=True)
    aktualne_uzycia = db.Column(db.Integer, default=0)

    @validates('znizka_procentowa')
    def validate_znizka_procentowa(self, key, znizka_procentowa):
        if znizka_procentowa is not None and not 0 <= znizka_procentowa <= 100:
            raise ValueError("Zniżka procentowa musi być między 0 a 100.")
        return znizka_procentowa

    def __repr__(self):
        return f'<Promocja {self.nazwa}>'

class Powiadomienie(db.Model):
    __tablename__ = "Powiadomienie"
    id = db.Column(db.Integer, primary_key=True)
    # Kto zainicjował (np. system, użytkownik który złożył zamówienie) - opcjonalne
    id_uzytkownika_zglaszajacego = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=True) 
    # Do kogo jest skierowane (np. admin, manager, konkretny użytkownik) - opcjonalne
    id_uzytkownika_docelowego = db.Column(db.Integer, db.ForeignKey('Uzytkownik.id'), nullable=True) 
    rola_docelowa = db.Column(db.String(50), nullable=True) # np. 'admin', 'manager' - do filtrowania
    
    typ = db.Column(db.String(100), nullable=False) 
    # np. 'nowy_uzytkownik', 'zadanie_resetu_hasla', 'nowe_zamowienie', 'platnosc_zrealizowana', 'blad_platnosci'
    tresc = db.Column(db.Text, nullable=False)
    link_docelowy = db.Column(db.String(255), nullable=True) # np. url_for('admin.view_order', order_id=X)
    data_utworzenia = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    czy_przeczytane = db.Column(db.Boolean, default=False, index=True)
    data_przeczytania = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Powiadomienie {self.id} - {self.typ}>'

class SiteSetting(db.Model):
    __tablename__ = "SiteSetting"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=True) # Store as string, cast as needed
    value_type = db.Column(db.String(20), default='string') # 'string', 'integer', 'boolean'

    def __repr__(self):
        return f'<SiteSetting {self.key}={self.value}>'

    @staticmethod
    def get(key_name, default=None, expected_type=str):
        setting = SiteSetting.query.filter_by(key=key_name).first()
        if setting and setting.value is not None:
            if expected_type == int:
                try:
                    return int(setting.value)
                except ValueError:
                    return default
            elif expected_type == bool:
                return setting.value.lower() in ['true', '1', 'yes', 'on']
            return setting.value # String by default
        return default

    @staticmethod
    def set(key_name, value, value_type='string'):
        setting = SiteSetting.query.filter_by(key=key_name).first()
        if not setting:
            setting = SiteSetting(key=key_name)
            db.session.add(setting)
        
        str_value = str(value)
        # Basic type validation/conversion for storage
        if value_type == 'integer':
            try:
                int(value) # Validate
            except ValueError:
                raise ValueError(f"Invalid integer value for setting '{key_name}': {value}")
        elif value_type == 'boolean':
            if not isinstance(value, bool):
                 str_value = 'true' if str(value).lower() in ['true', '1', 'yes', 'on'] else 'false'

        setting.value = str_value
        setting.value_type = value_type
        # Commit should happen in the route after calling set
