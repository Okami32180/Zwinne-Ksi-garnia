import click
from flask.cli import with_appcontext
import requests # For making API calls
import time     # For rate limiting
from sqlalchemy import func # Import func for SQL functions
import re # For parsing year
from aplikacja import db
from aplikacja.models import Book, Kategoria, Gatunek, Wydawnictwo
import random
from faker import Faker # Still useful for some fallbacks or minor details

fake = Faker('pl_PL')

# Google Books API base URL
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

# (Optional) Add your Google Books API Key here if you have one
# GOOGLE_BOOKS_API_KEY = "YOUR_API_KEY"
GOOGLE_BOOKS_API_KEY = None # Set to None if no key

def fetch_books_from_google_api(query, lang_restrict='pl', country='PL', max_results=40):
    """Fetches book data from Google Books API."""
    params = {
        'q': query,
        'langRestrict': lang_restrict,
        # 'country': country, # Country can sometimes be too restrictive
        'maxResults': min(max_results, 40), # API max is 40 per request
        'printType': 'books'
    }
    if GOOGLE_BOOKS_API_KEY:
        params['key'] = GOOGLE_BOOKS_API_KEY

    try:
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data.get('items', [])
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching data from Google Books API for query '{query}': {e}", err=True)
        return []
    except ValueError: # Includes JSONDecodeError
        click.echo(f"Error decoding JSON response from Google Books API for query '{query}'.", err=True)
        return []

def get_or_create_gatunek(nazwa):
    gatunek = Gatunek.query.filter_by(nazwa=nazwa).first()
    if not gatunek:
        gatunek = Gatunek(nazwa=nazwa)
        db.session.add(gatunek)
        # Commit immediately or as part of a larger transaction
    return gatunek

def get_or_create_wydawnictwo(nazwa):
    wydawnictwo = Wydawnictwo.query.filter_by(nazwa=nazwa).first()
    if not wydawnictwo:
        wydawnictwo = Wydawnictwo(nazwa=nazwa)
        db.session.add(wydawnictwo)
    return wydawnictwo

def get_or_create_kategoria(nazwa, nadkategoria=None):
    kategoria = Kategoria.query.filter_by(nazwa=nazwa).first()
    if not kategoria:
        kategoria = Kategoria(nazwa=nazwa, nadkategoria=nadkategoria)
        db.session.add(kategoria)
    return kategoria

@click.command('seed-books')
@click.option('--count', default=50, help='Number of books to create.')
@with_appcontext
def seed_books_command(count):
    """Seeds the database with fake books."""
    click.echo(f'Seeding {count} books...')

    # Create some default publishers, categories if they don't exist
    # Genres will be created based on API results or a fallback list
    default_publishers_names = ['SuperWydawnictwo', 'Czytamy Razem', 'Nowa Era Książki', 'Literacki Świat', 'Wydawnictwo XYZ', 'Książkowe Horyzonty']
    default_categories_names = ['Bestsellery', 'Nowości', 'Promocje', 'Ebooki PL', 'Audiobooki', 'Klasyka', 'Young Adult', 'Popularnonaukowe']
    
    default_publishers = [get_or_create_wydawnictwo(name) for name in default_publishers_names]
    default_categories = [get_or_create_kategoria(name) for name in default_categories_names]
    db.session.commit() # Commit these base entities
    click.echo('Default publishers and categories ensured.')

    # List of queries to search for books - prioritize specific titles/authors
    # For better results, ensure these are likely to yield Polish editions with langRestrict='pl'
    specific_queries = [
        "Wiedźmin Ostatnie życzenie Andrzej Sapkowski", "Hobbit J.R.R. Tolkien", "Lalka Bolesław Prus",
        "Pan Tadeusz Adam Mickiewicz", "Quo Vadis Henryk Sienkiewicz", "Harry Potter i Kamień Filozoficzny",
        "Solaris Stanisław Lem", "Remigiusz Mróz Kasacja", "Olga Tokarczuk Księgi Jakubowe", "Szczepan Twardoch Król",
        "Mały Książę", "Zbrodnia i kara Fiodor Dostojewski", "Rok 1984 George Orwell",
        "Rozdroże kruków Andrzej Sapkowski", "Zapomniane niedziele Valérie Perrin",
        "Pierwsza Dama Jolanta Kwaśniewska", "Cienie pośród mroku Remigiusz Mróz", "Glutologia Adam Mirek"
    ]
    general_queries = [ # Fallback to more general queries if count not met
        "popularne książki fantasy Polska", "bestsellery kryminały Polska", "książki historyczne Polska",
        "literatura piękna Polska", "reportaże Polska", "książki dla dzieci Polska", "klasyka literatury polskiej",
        "książki science fiction Polska", "romanse współczesne Polska", "thrillery psychologiczne Polska"
    ]
    search_queries = specific_queries + general_queries # Process specific ones first
    
    # Genre mapping from common API terms (often English) to Polish
    # This needs to be expanded based on typical API responses
    genre_mapping = {
        "Fiction": "Literatura piękna",
        "Juvenile Fiction": "Dla dzieci", # Google often uses this for children's books
        "Fantasy": "Fantastyka",
        "Science Fiction": "Science Fiction",
        "Thrillers": "Thriller", # Note: API might use "Thrillers (Fiction)" etc.
        "Mystery": "Kryminał", # Or "Detective and mystery stories"
        "Crime": "Kryminał",
        "Romance": "Romans",
        "Historical Fiction": "Historyczna", # If it's fiction
        "History": "Historia", # If non-fiction
        "Biography & Autobiography": "Biografie",
        "Nonfiction": "Literatura faktu",
        "Self-Help": "Poradnik",
        "Business & Economics": "Biznes i ekonomia",
        "Computers": "Informatyka",
        # Add more mappings as you observe API results
    }
    # Ensure all target Polish genres from mapping exist in DB, plus fallbacks
    fallback_genre_names = list(set(list(genre_mapping.values()) + ['Fantastyka', 'Science Fiction', 'Kryminał', 'Romans', 'Literatura faktu', 'Poradnik', 'Dla dzieci', 'Historyczna', 'Literatura piękna', 'Thriller', 'Inne']))

    all_books_added = []
    created_books_count = 0
    max_api_books_per_query = 10 # Fetch fewer per query to diversify, up to 40 is API max

    # Ensure some base genres exist for fallback
    fallback_genre_names = ['Fantastyka', 'Science Fiction', 'Kryminał', 'Romans', 'Literatura faktu', 'Poradnik', 'Dla dzieci', 'Historyczna', 'Literatura piękna', 'Thriller', 'Inne']
    for genre_name in fallback_genre_names:
        get_or_create_gatunek(genre_name)
    db.session.commit()
    
    # Shuffle queries to get variety if count is less than total possible results
    random.shuffle(search_queries)

    for query_idx, query in enumerate(search_queries):
        if created_books_count >= count:
            break
        
        click.echo(f"\nFetching books for query: '{query}'...")
        api_books = fetch_books_from_google_api(query, max_results=max_api_books_per_query)
        
        if not api_books:
            click.echo(f"No books found for query: '{query}'.")
            if GOOGLE_BOOKS_API_KEY is None and query_idx > 3: # After a few queries, if no key, API might be blocking
                click.echo("Warning: Multiple queries without results. Consider adding a Google Books API Key for better results.", err=True)
            time.sleep(1) # Wait a bit before next query if this one failed
            continue

        for item_idx, item in enumerate(api_books):
            if created_books_count >= count:
                break

            volume_info = item.get('volumeInfo', {})
            title = volume_info.get('title')
            authors = volume_info.get('authors', [])
            author_str = ", ".join(authors) if authors else "Autor nieznany"
            
            if not title:
                click.echo("Skipping item with no title.")
                continue

            # ISBN
            isbn_13 = None
            isbn_10 = None
            for identifier in volume_info.get('industryIdentifiers', []):
                if identifier.get('type') == 'ISBN_13':
                    isbn_13 = identifier.get('identifier')
                elif identifier.get('type') == 'ISBN_10':
                    isbn_10 = identifier.get('identifier')
            
            final_isbn = isbn_13 or isbn_10
            if not final_isbn: # Fallback to fake ISBN if API doesn't provide one
                final_isbn = fake.isbn13()
            
            # Check for existing book by ISBN or Title/Author to avoid exact duplicates
            if Book.query.filter_by(isbn=final_isbn).first() or \
               Book.query.filter_by(tytul=title, autor=author_str).first():
                click.echo(f"Book '{title}' by {author_str} (ISBN: {final_isbn}) already exists or is a duplicate. Skipping.")
                continue

            description = volume_info.get('description', "Brak opisu.")
            if len(description) > 800: # Truncate long descriptions
                description = description[:797] + "..."
            
            image_links = volume_info.get('imageLinks', {})
            cover_url = image_links.get('thumbnail') or image_links.get('smallThumbnail')
            if not cover_url: # Fallback to picsum if no cover from API
                cover_url = f'https://picsum.photos/seed/{final_isbn}/300/450'
            
            # Genres/Categories from API (often just one primary category)
            api_categories = volume_info.get('categories', [])
            assigned_gatunek = None
            if api_categories:
                # Try to match API category to our Gatunek model using the mapping
                for api_cat_name_original in api_categories:
                    # Normalize API category name slightly (e.g., "Fiction / Fantasy" -> "Fantasy")
                    api_cat_name_parts = [part.strip() for part in api_cat_name_original.split('/')]
                    
                    found_mapped_genre = False
                    for part in reversed(api_cat_name_parts): # Check specific part first
                        polish_genre_name = genre_mapping.get(part)
                        if polish_genre_name:
                            assigned_gatunek = Gatunek.query.filter_by(nazwa=polish_genre_name).first()
                            if not assigned_gatunek: # Should have been created from fallback_genre_names
                                assigned_gatunek = get_or_create_gatunek(polish_genre_name)
                            found_mapped_genre = True
                            break
                        # Try case-insensitive match if direct map fails
                        for key_map, val_map in genre_mapping.items():
                            if key_map.lower() == part.lower():
                                assigned_gatunek = Gatunek.query.filter_by(nazwa=val_map).first()
                                if not assigned_gatunek: assigned_gatunek = get_or_create_gatunek(val_map)
                                found_mapped_genre = True
                                break
                        if found_mapped_genre: break
                    if found_mapped_genre: break
                
                # If still no assigned_gatunek after checking all API categories, use a fallback
                if not assigned_gatunek:
                    # If the API provided categories but none mapped, we could try creating the first one (potentially English)
                    # or just use a generic Polish fallback. Let's prefer Polish.
                    assigned_gatunek = Gatunek.query.filter_by(nazwa="Inne").first() or get_or_create_gatunek("Inne")

            if not assigned_gatunek: # Absolute fallback if everything else failed
                assigned_gatunek = Gatunek.query.filter_by(nazwa="Inne").first() or get_or_create_gatunek("Inne")


            # Prepare rok_wydania
            parsed_rok_wydania = None
            published_date_str = volume_info.get('publishedDate')
            if published_date_str:
                # import re # Moved to top
                match = re.search(r'\b(\d{4})\b', published_date_str)
                if match:
                    try:
                        parsed_rok_wydania = int(match.group(1))
                    except ValueError:
                        pass # Fallback to random if parsing fails
            if parsed_rok_wydania is None:
                 parsed_rok_wydania = random.randint(1990, 2024)

            book = Book(
                tytul=title,
                autor=author_str,
                isbn=final_isbn,
                opis=description,
                okladka_url=cover_url,
                gatunek_ref=assigned_gatunek,
                wydawnictwo_ref=random.choice(default_publishers) if default_publishers else None,
                cena=round(random.uniform(19.99, 129.99), 2), # Wider price range
                rok_wydania=parsed_rok_wydania,
                ilosc_stron=volume_info.get('pageCount') or random.randint(150, 700),
                format_pliku=random.choice(['PDF', 'EPUB']), # Simplified
                rozmiar_pliku_mb=round(random.uniform(0.5, 15.0), 2),
                sciezka_pliku=f'/ebooks/api_seeded/{final_isbn}.{random.choice(["pdf", "epub"])}', # Placeholder
                dostepny=True,
                srednia_ocen=round(volume_info.get('averageRating', 0.0), 2),
                liczba_ocen=volume_info.get('ratingsCount', 0)
            )
            
            # Assign random existing categories from our predefined list
            num_db_categories = random.randint(0, 2) # 0 to 2 additional categories
            if default_categories and num_db_categories > 0:
                 book.kategorie = random.sample(default_categories, min(num_db_categories, len(default_categories)))
            
            db.session.add(book)
            all_books_added.append(title)
            created_books_count += 1
            click.echo(f"  Added ({created_books_count}/{count}): {title} by {author_str}")

            if created_books_count % 20 == 0: # Commit more frequently with API calls
                try:
                    db.session.commit()
                    click.echo(f"Committed batch. Total created: {created_books_count}")
                except Exception as e:
                    db.session.rollback()
                    click.echo(f"Error committing batch: {e}", err=True)
                time.sleep(0.5) # Small delay to be nice to the API

            if item_idx % 5 == 0 and item_idx > 0: # Slightly longer pause between batches of API items
                 time.sleep(1)


    try:
        db.session.commit() # Commit any remaining books
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error committing final batch: {e}", err=True)
        
    click.echo(f"\nSuccessfully attempted to seed {count} books. Total unique books added: {len(set(all_books_added))}.")
    if GOOGLE_BOOKS_API_KEY is None:
        click.echo("Consider adding a GOOGLE_BOOKS_API_KEY to seed_data.py for more reliable and extensive results.", err=True)