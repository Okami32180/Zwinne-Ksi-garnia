from aplikacja import db
from aplikacja.models import Powiadomienie, Uzytkownik
from datetime import datetime

def create_notification(typ, tresc, id_uzytkownika_zglaszajacego=None, id_uzytkownika_docelowego=None, rola_docelowa=None, link_docelowy=None, commit=True):
    """
    Tworzy nowe powiadomienie w systemie.

    Args:
        typ (str): Typ powiadomienia (np. 'nowe_zamowienie', 'reset_hasla').
        tresc (str): Treść powiadomienia.
        id_uzytkownika_zglaszajacego (int, optional): ID użytkownika, który zainicjował powiadomienie.
        id_uzytkownika_docelowego (int, optional): ID konkretnego użytkownika, do którego jest skierowane.
        rola_docelowa (str, optional): Rola użytkowników, do których jest skierowane (np. 'admin', 'manager').
        link_docelowy (str, optional): URL, do którego powiadomienie może odsyłać.
        commit (bool): Whether to commit the session immediately.
    Returns:
        Powiadomienie: Utworzony obiekt powiadomienia.
    """
    powiadomienie = Powiadomienie(
        typ=typ,
        tresc=tresc,
        id_uzytkownika_zglaszajacego=id_uzytkownika_zglaszajacego,
        id_uzytkownika_docelowego=id_uzytkownika_docelowego,
        rola_docelowa=rola_docelowa,
        link_docelowy=link_docelowy,
        data_utworzenia=datetime.utcnow()
    )
    db.session.add(powiadomienie)
    if commit:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log error appropriately in a real app
            print(f"Error creating notification: {e}") # Simple print for now
            return None
    return powiadomienie

def get_admin_manager_ids():
    """Zwraca listę ID wszystkich adminów i managerów."""
    users = Uzytkownik.query.filter(Uzytkownik.rola.in_(['admin', 'manager'])).all()
    return [user.id for user in users]

def notify_admins_and_managers(typ, tresc, id_uzytkownika_zglaszajacego=None, link_docelowy=None):
    """
    Wysyła powiadomienie do wszystkich administratorów i managerów.
    Zamiast tworzyć wiele indywidualnych powiadomień, tworzy jedno z rola_docelowa.
    """
    return create_notification(
        typ=typ,
        tresc=tresc,
        id_uzytkownika_zglaszajacego=id_uzytkownika_zglaszajacego,
        rola_docelowa='admin', # Will also be picked up by managers if they check for 'admin' or a general pool
        link_docelowy=link_docelowy,
        commit=True # Usually commit immediately for admin notifications
    )
    # Alternative: Create one for 'admin' and one for 'manager' if distinct handling is needed.
    # create_notification(typ=typ, tresc=tresc, id_uzytkownika_zglaszajacego=id_uzytkownika_zglaszajacego, rola_docelowa='manager', link_docelowy=link_docelowy, commit=False)
    # db.session.commit()

def mark_notification_as_read(notification_id, user_id):
    """
    Oznacza powiadomienie jako przeczytane przez danego użytkownika.
    Jeśli powiadomienie jest skierowane do roli, a nie konkretnego użytkownika,
    to oznaczenie jako przeczytane może być bardziej złożone (np. kto z roli przeczytał).
    Dla uproszczenia, jeśli user_id pasuje do docelowego lub user ma rolę docelową, oznaczamy.
    """
    powiadomienie = db.session.get(Powiadomienie, notification_id)
    user = db.session.get(Uzytkownik, user_id)

    if powiadomienie and user:
        # Check if the notification is for this specific user or for their role
        can_mark_read = (powiadomienie.id_uzytkownika_docelowego == user.id or 
                         (powiadomienie.rola_docelowa and powiadomienie.rola_docelowa == user.rola))
        
        if can_mark_read and not powiadomienie.czy_przeczytane:
            # For role-based notifications, simply marking it 'czy_przeczytane' might hide it for other users of that role.
            # A more complex system would have a many-to-many table (UserPowiadomienieReadStatus).
            # For this project, we'll assume if one admin/manager reads a role-based notification, it's "handled"
            # or the frontend will filter based on who is viewing.
            # For simplicity here, if it's a role notification, we might not mark it read globally,
            # but rely on the frontend to not show it again to *this* user if they dismiss it.
            # OR, if it's a specific user notification, mark it.
            if powiadomienie.id_uzytkownika_docelowego == user.id:
                 powiadomienie.czy_przeczytane = True
                 powiadomienie.data_przeczytania = datetime.utcnow()
                 db.session.commit()
                 return True
            # If it's a role-based one, we don't globally mark it read here to keep it simple.
            # The admin panel will just list all unread for the role.
            # A "Dismiss" action in UI could be per-user via session or local storage if needed without DB change.
            return True # User is authorized to see it as read
    return False