import sqlite3
import os

db_filename = 'ksiegarnia.db'

if os.path.exists(db_filename):
    os.remove(db_filename)

conn = sqlite3.connect(db_filename)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE Uzytkownik (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imie VARCHAR(50) NOT NULL,
    nazwisko VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL CHECK (email LIKE '%@%.%'),
    data_rejestracji DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_ostatniego_logowania DATETIME
);
''')

cursor.execute('''
CREATE TABLE Ksiazka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tytul VARCHAR(100) NOT NULL,
    autor VARCHAR(100) NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    cena DECIMAL(10,2) NOT NULL CHECK (cena > 0),
    rok_wydania INTEGER,
    ilosc_stron INTEGER
);
''')

cursor.execute('''
CREATE TABLE Zamowienie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uzytkownika INTEGER NOT NULL,
    data_zamowienia DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'nowe' CHECK (status IN ('nowe', 'w realizacji', 'wysłane', 'dostarczone', 'anulowane')),
    adres_dostawy VARCHAR(200),
    FOREIGN KEY (id_uzytkownika) REFERENCES Uzytkownik(id)
);
''')

cursor.execute('''
CREATE TABLE Zamowienie_Ksiazka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_zamowienia INTEGER NOT NULL,
    id_ksiazki INTEGER NOT NULL,
    ilosc INTEGER NOT NULL DEFAULT 1 CHECK (ilosc > 0),
    cena_jednostkowa DECIMAL(10,2) NOT NULL CHECK (cena_jednostkowa > 0),
    FOREIGN KEY (id_zamowienia) REFERENCES Zamowienie(id),
    FOREIGN KEY (id_ksiazki) REFERENCES Ksiazka(id)
);
''')

cursor.execute('''
CREATE TABLE Recenzja (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_uzytkownika INTEGER NOT NULL,
    id_ksiazki INTEGER NOT NULL,
    ocena INTEGER NOT NULL CHECK(ocena BETWEEN 1 AND 5),
    komentarz VARCHAR(500),
    data_dodania DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_uzytkownika) REFERENCES Uzytkownik(id),
    FOREIGN KEY (id_ksiazki) REFERENCES Ksiazka(id),
    UNIQUE(id_uzytkownika, id_ksiazki)
);
''')

cursor.execute('CREATE INDEX idx_zamowienie_uzytkownik ON Zamowienie(id_uzytkownika);')
cursor.execute('CREATE INDEX idx_zamowienie_ksiazka_zamowienie ON Zamowienie_Ksiazka(id_zamowienia);')
cursor.execute('CREATE INDEX idx_zamowienie_ksiazka_ksiazka ON Zamowienie_Ksiazka(id_ksiazki);')
cursor.execute('CREATE INDEX idx_recenzja_uzytkownik ON Recenzja(id_uzytkownika);')
cursor.execute('CREATE INDEX idx_recenzja_ksiazka ON Recenzja(id_ksiazki);')

cursor.execute('''
INSERT INTO Uzytkownik (imie, nazwisko, email, data_rejestracji) VALUES 
    ('Anna', 'Kowalska', 'anna.kowalska@example.com', '2025-01-15 10:30:00'),
    ('Jan', 'Nowak', 'jan.nowak@example.com', '2025-02-20 15:45:20'),
    ('Maria', 'Wójcik', 'maria.wojcik@example.com', '2025-03-10 09:15:30');
''')

cursor.execute('''
INSERT INTO Ksiazka (tytul, autor, isbn, cena, rok_wydania, ilosc_stron) VALUES 
    ('Wiedźmin: Ostatnie życzenie', 'Andrzej Sapkowski', '9788375780635', 39.99, 2014, 332),
    ('Lalka', 'Bolesław Prus', '9788373271821', 29.99, 2018, 890),
    ('Solaris', 'Stanisław Lem', '9788308054383', 34.50, 2016, 224),
    ('Chłopi', 'Władysław Reymont', '9788377916728', 45.00, 2019, 640);
''')

cursor.execute('''
INSERT INTO Zamowienie (id_uzytkownika, data_zamowienia, status, adres_dostawy) VALUES 
    (1, '2025-04-01 13:25:10', 'dostarczone', 'ul. Kwiatowa 5, 00-001 Warszawa'),
    (2, '2025-04-02 09:45:30', 'wysłane', 'ul. Polna 10/2, 30-001 Kraków'),
    (3, '2025-04-10 16:20:00', 'w realizacji', 'ul. Długa 15, 61-001 Poznań');
''')

cursor.execute('''
INSERT INTO Zamowienie_Ksiazka (id_zamowienia, id_ksiazki, ilosc, cena_jednostkowa) VALUES 
    (1, 1, 1, 39.99),
    (1, 3, 2, 34.50),
    (2, 2, 1, 29.99),
    (3, 1, 1, 39.99),
    (3, 4, 1, 45.00);
''')

cursor.execute('''
INSERT INTO Recenzja (id_uzytkownika, id_ksiazki, ocena, komentarz, data_dodania) VALUES 
    (1, 1, 5, 'Świetna książka, polecam! Fascynująca historia i niesamowite postacie.', '2025-04-05 18:30:00'),
    (2, 2, 4, 'Klasyk literatury, warto przeczytać. Skomplikowana fabuła i interesujący bohaterowie.', '2025-04-07 20:15:00'),
    (3, 3, 5, 'Najlepsza książka Lema. Zmusza do refleksji nad kondycją człowieka i jego relacjami z nieznanym.', '2025-04-12 14:40:00');
''')

conn.commit()
conn.close()

print(f'Baza danych "{db_filename}" została utworzona i wypełniona przykładowymi danymi.')
