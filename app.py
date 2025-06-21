import os
import time
import requests
import bcrypt
import sqlite3
import pandas as pd
import streamlit as st
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyAppLogger")

# Ensure media directory exists
if not os.path.exists('media'):
    os.makedirs('media')

# Helper functions
def create_connection():
    """Create a database connection."""
    try:
        conn = sqlite3.connect("app.db", check_same_thread=False)
        return conn
    except sqlite3.Error as e:
        error_message = f"Błąd połączenia z bazą danych: {e}"
        logger.error(error_message)
        st.error(error_message)
        return None

def initialize_db():
    """Initialize the database and create necessary tables."""
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                password TEXT NOT NULL, 
                city TEXT NOT NULL, 
                profile_picture TEXT
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT NOT NULL, 
                city TEXT NOT NULL, 
                description TEXT, 
                members_count INTEGER, 
                latitude REAL, 
                longitude REAL
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS user_customizations (
                username TEXT PRIMARY KEY, 
                background_color TEXT, 
                font_size TEXT, 
                font_family TEXT, 
                theme TEXT
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS members (
                username TEXT, 
                club_id INTEGER, 
                FOREIGN KEY(username) REFERENCES users(username), 
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS reviews (
                username TEXT, 
                club_id INTEGER, 
                rating INTEGER, 
                review TEXT, 
                FOREIGN KEY(username) REFERENCES users(username), 
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS private_messages (
                sender TEXT, 
                receiver TEXT, 
                content TEXT, 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS notifications (
                username TEXT, 
                message TEXT, 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                read INTEGER DEFAULT 0
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS club_events (
                club_id INTEGER, 
                event_name TEXT, 
                event_date DATE, 
                location TEXT, 
                description TEXT, 
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            );''')
            conn.execute('''CREATE TABLE IF NOT EXISTS media_gallery (
                club_id INTEGER, 
                media_type TEXT, 
                media_path TEXT, 
                uploaded_by TEXT, 
                FOREIGN KEY(club_id) REFERENCES clubs(id)
            );''')
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()

def hash_password(password):
    """Create a hashed password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(hashed_password, user_password):
    """Check if the provided password matches the stored hashed password."""
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

def log_performance(endpoint, duration):
    """Log the performance of API endpoints."""
    logger.info(f"Endpoint: {endpoint}, Duration: {duration:.2f} seconds")

def get_weather(city):
    """Get weather information for a city."""
    try:
        start_time = time.time()
        response = requests.get(f"http://wttr.in/{city}?format=3")
        response.raise_for_status()
        duration = time.time() - start_time
        log_performance('get_weather', duration)
        return response.text
    except requests.exceptions.RequestException as err:
        error_message = f"Nie udało się uzyskać danych pogodowych: {err}"
        logger.error(error_message)
        st.error(error_message)
        return None

def geocode_city(city):
    """Get geographic coordinates for a given city."""
    return 50.0619474, 19.9368564  # Example coordinates for Kraków

def register_user():
    """Register a new user."""
    st.subheader("Rejestracja")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    city = st.text_input("City")
    if st.button("Zarejestruj się"):
        if username and password and city:
            hashed_pw = hash_password(password)
            try:
                with create_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (username, password, city) VALUES (?, ?, ?)", (username, hashed_pw, city))
                    st.success("Rejestracja powiodła się!")
            except sqlite3.IntegrityError:
                st.error("Ten użytkownik już istnieje.")
            except sqlite3.Error as e:
                st.error(f"Błąd dostępu do bazy danych: {e}")
        else:
            st.warning("Wszystkie pola muszą być wypełnione.")

def login_user():
    """Login a user."""
    st.subheader("Logowanie")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Zaloguj się"):
        if username and password:
            conn = create_connection()
            if conn is None:
                return
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
                    user = cursor.fetchone()
                    if user and check_password(user[0], password):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.success(f"Witaj, {username}!")
                    else:
                        st.error("Błędna nazwa użytkownika lub hasło.")
            except sqlite3.Error as e:
                st.error(f"Błąd dostępu do bazy danych: {e}")
            finally:
                conn.close()
        else:
            st.warning("Wszystkie pola muszą być wypełnione.")

def logout():
    """Logout the current user."""
    st.session_state.clear()
    st.success("Wylogowano pomyślnie!")

def set_user_customizations():
    """Set user customization options."""
    st.subheader("Ustawienia personalizacji")
    background_color = st.color_picker("Kolor tła", "#FFFFFF")
    font_size = st.selectbox("Rozmiar czcionki", ['small', 'medium', 'large'])
    font_family = st.selectbox("Czcionka", ['Arial', 'Courier New', 'Comic Sans MS', 'Georgia'])
    theme = st.selectbox("Motyw", ['light', 'dark'])

    if st.button("Zapisz ustawienia"):
        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO user_customizations (username, background_color, font_size, font_family, theme) VALUES (?, ?, ?, ?, ?)",
                    (st.session_state['username'], background_color, font_size, font_family, theme))
            st.success("Zmiany zapisane!")
        except sqlite3.Error as e:
            st.error(f"Błąd dostępu do bazy danych: {e}")
        finally:
            conn.close()

def apply_customizations():
    """Apply user customizations to the interface."""
    username = st.session_state.get('username')
    if not username:
        st.error("Błąd: Brak nazwy użytkownika w stanie sesji")
        return

    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT background_color, font_size, font_family, theme FROM user_customizations WHERE username = ?", (username,))
            customizations = cursor.fetchone()

            if customizations:
                bg_color, font_size, font_family, theme = customizations
                # Ensure font size is valid
                font_size = font_size if font_size in ['small', 'medium', 'large'] else 'medium'
                st.markdown(f"""
                    <style>
                        .reportview-container {{
                            background-color: {bg_color};
                            font-size: {font_size}px;
                            font-family: {font_family};
                        }}
                    </style>
                """, unsafe_allow_html=True)
            else:
                st.info("Brak ustawień personalizacyjnych dla tego użytkownika.")
    except sqlite3.Error as e:
        error_message = f"Błąd dostępu do bazy danych: {e}"
        st.error(error_message)
        logger.error(error_message)
    finally:
        conn.close()

def admin_dashboard():
    """Admin panel to manage users and clubs."""
    st.subheader("Panel Administracyjny")
    analytics_choice = st.radio("Wybierz typ analizy", ("Aktywność użytkowników", "Statystyki klubów"))

    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            if analytics_choice == "Aktywność użytkowników":
                user_activity = pd.read_sql_query("SELECT username, COUNT(*) as post_count FROM forum_posts GROUP BY username", conn)
                st.bar_chart(user_activity, x='username', y='post_count', use_container_width=True)

            elif analytics_choice == "Statystyki klubów":
                club_stats = pd.read_sql_query("SELECT name, members_count FROM clubs", conn)
                st.bar_chart(club_stats, x='name', y='members_count', use_container_width=True)

            users = pd.read_sql_query("SELECT * FROM users", conn)
            clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

    st.write("Lista użytkowników:")
    st.table(users)

    user_to_delete = st.selectbox("Wybierz użytkownika do usunięcia", users['username'])
    if st.button("Usuń wybranego użytkownika"):
        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                st.success(f"Użytkownik {user_to_delete} został usunięty!")
        except sqlite3.Error as e:
            st.error(f"Błąd usuwania użytkownika: {e}")
        finally:
            conn.close()

    st.write("Lista klubów:")
    st.table(clubs)

    club_to_delete = st.selectbox("Wybierz klub do usunięcia", clubs['name'])
    if st.button("Usuń wybrany klub"):
        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute("DELETE FROM clubs WHERE name = ?", (club_to_delete,))
                st.success(f"Klub {club_to_delete} został usunięty!")
        except sqlite3.Error as e:
            st.error(f"Błąd usuwania klubu: {e}")
        finally:
            conn.close()

def create_club():
    """Create a new club."""
    st.subheader("Utwórz Klub")
    club_name = st.text_input("Nazwa Klubu")
    city = st.text_input("Miasto")
    description = st.text_area("Opis")
    if st.button("Utwórz klub"):
        conn = create_connection()
        if conn is None:
            return
        try:
            lat, lon = geocode_city(city)
            with conn:
                conn.execute("INSERT INTO clubs (name, city, description, members_count, latitude, longitude) VALUES (?, ?, ?, 0, ?, ?)", (club_name, city, description, lat, lon))
            st.success(f"Klub {club_name} utworzony!")
        except sqlite3.Error as e:
            st.error(f"Błąd tworzenia klubu: {e}")
        finally:
            conn.close()

def view_clubs():
    """View and manage club information."""
    st.subheader("Lista klubów")
    search_term = st.text_input("Wyszukaj kluby (według nazwy lub miasta)")
    conn = create_connection()
    if conn is None:
        return
    try:
        df = pd.read_sql_query("SELECT * FROM clubs", conn)
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) | df['city'].str.contains(search_term, case=False)]

        if df.empty:
            st.info("Brak klubów do wyświetlenia.")
            return

        for index, row in df.iterrows():
            st.markdown(f"### {row['name']} ({row['city']})")
            st.write(row['description'])
            weather = get_weather(row['city'])
            if weather:
                st.write(f"Pogoda: {weather}")
            st.write(f"Członkowie: {row['members_count']}")
            rating = calculate_average_rating(row['id'])
            st.write(f"Średnia ocena: {rating}")
            st.button(f"Dołącz do {row['name']}", key=f"join_club_{index}", on_click=join_club, args=(row['id'],))

            with st.expander("Oceny i Recenzje"):
                reviews = get_club_reviews(row['id'])
                for review in reviews:
                    st.write(f"**{review['username']}**: {review['rating']}/5 - {review['review']}")
                rating = st.slider("Twoja ocena", 1, 5, 3)
                review_text = st.text_area("Twoja recenzja", key=f"review_text_{index}")
                if st.button("Dodaj recenzję", key=f"review_{index}"):
                    add_review(row['id'], rating, review_text)
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

def calculate_average_rating(club_id):
    """Calculate the average rating for a club."""
    conn = create_connection()
    if conn is None:
        return "Brak ocen"
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(rating) FROM reviews WHERE club_id = ?", (club_id,))
        return cursor.fetchone()[0] or "Brak ocen"
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
        return "Brak ocen"
    finally:
        conn.close()

def join_club(club_id):
    """Join a selected club."""
    username = st.session_state.get('username')
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO members (username, club_id) VALUES (?, ?)", (username, club_id))
            conn.execute("UPDATE clubs SET members_count = members_count + 1 WHERE id = ?", (club_id,))
            st.success("Dołączyłeś do klubu!")
    except sqlite3.Error as e:
        st.error(f"Błąd podczas dołączania do klubu: {e}")
    finally:
        conn.close()

def get_club_reviews(club_id):
    """Get all reviews for a club."""
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, rating, review FROM reviews WHERE club_id = ?", (club_id,))
        reviews = cursor.fetchall()
        return [{'username': row[0], 'rating': row[1], 'review': row[2]} for row in reviews]
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
        return []
    finally:
        conn.close()

def add_review(club_id, rating, review_text):
    """Add a review for a club."""
    username = st.session_state.get('username')
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO reviews (username, club_id, rating, review) VALUES (?, ?, ?, ?)", (username, club_id, rating, review_text))
        st.success("Recenzja dodana!")
    except sqlite3.Error as e:
        st.error(f"Błąd podczas dodawania recenzji: {e}")
    finally:
        conn.close()

def manage_gallery(club_id):
    """Manage club's media gallery."""
    st.subheader("Galeria Klubu")
    uploaded_file = st.file_uploader("Wybierz zdjęcie lub wideo", type=['jpg', 'jpeg', 'png', 'mp4'])
    if uploaded_file:
        media_type = "video" if uploaded_file.type.startswith('video') else "image"
        file_path = os.path.join('media', uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute("INSERT INTO media_gallery (club_id, media_type, media_path, uploaded_by) VALUES (?, ?, ?, ?)",
                             (club_id, media_type, file_path, st.session_state['username']))
            st.success("Plik dodany do galerii!")
        except sqlite3.Error as e:
            st.error(f"Błąd podczas dodawania pliku do galerii: {e}")
        finally:
            conn.close()

    conn = create_connection()
    if conn is None:
        return
    try:
        media_files = pd.read_sql_query(
            "SELECT media_type, media_path FROM media_gallery WHERE club_id = ?", 
            conn,
            params=(club_id,))
        if not media_files.empty:
            for file in media_files.itertuples():
                if file.media_type == 'image':
                    st.image(file.media_path)
                elif file.media_type == 'video':
                    st.video(file.media_path)
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

def show_messages():
    """Display private messages for the user."""
    st.subheader("Wiadomości prywatne")
    conn = create_connection()
    if conn is None:
        return
    try:
        username = st.session_state['username']
        messages = pd.read_sql_query(
            "SELECT sender, content, timestamp FROM private_messages WHERE receiver = ? ORDER BY timestamp DESC",
            conn, params=(username,))
        if messages.empty:
            st.info("Brak wiadomości.")
        else:
            for message in messages.itertuples():
                st.markdown(f"Od: {message.sender} - {message.timestamp}")
                st.write(message.content)
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

def send_message():
    """Send a private message to another user."""
    st.subheader("Wyślij wiadomość")
    receiver = st.text_input("Do kogo:")
    content = st.text_area("Treść wiadomości")
    if st.button("Wyślij"):
        if receiver and content:
            sender = st.session_state['username']
            conn = create_connection()
            if conn is None:
                return
            try:
                with conn:
                    conn.execute("INSERT INTO private_messages (sender, receiver, content) VALUES (?, ?, ?)", (sender, receiver, content))
                st.success("Wiadomość wysłana!")
            except sqlite3.Error as e:
                st.error(f"Błąd podczas wysyłania wiadomości: {e}")
            finally:
                conn.close()
        else:
            st.warning("Oba pola muszą być wypełnione!")

def show_notifications():
    """Display notifications for the user."""
    st.subheader("Powiadomienia")
    conn = create_connection()
    if conn is None:
        return
    try:
        username = st.session_state['username']
        notifications = pd.read_sql_query(
            "SELECT message, timestamp FROM notifications WHERE username = ? AND read = 0", conn, params=(username,))
        conn.execute("UPDATE notifications SET read = 1 WHERE username = ?", (username,))
        if notifications.empty:
            st.info("Brak nowych powiadomień.")
        else:
            for notification in notifications.itertuples():
                st.write(f"{notification.timestamp} - {notification.message}")
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

def manage_events():
    """Manage club events."""
    st.subheader("Wydarzenia klubowe")
    conn = create_connection()
    if conn is None:
        return
    try:
        clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
        club_names = clubs['name'].unique()
        selected_club = st.selectbox("Wybierz klub", club_names)
        if selected_club:
            event_name = st.text_input("Nazwa wydarzenia")
            event_date = st.date_input("Data wydarzenia")
            location = st.text_input("Miejsce wydarzenia")
            description = st.text_area("Opis wydarzenia")
            if st.button("Dodaj wydarzenie"):
                club_id = clubs.loc[clubs['name'] == selected_club, 'id'].iloc[0]
                try:
                    with conn:
                        conn.execute(
                            "INSERT INTO club_events (club_id, event_name, event_date, location, description) VALUES (?, ?, ?, ?, ?)",
                            (club_id, event_name, event_date, location, description))
                    st.success("Wydarzenie dodane!")
                except sqlite3.Error as e:
                    st.error(f"Błąd podczas dodawania wydarzenia: {e}")
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

def display_events():
    """Display upcoming club events."""
    st.subheader("Nadchodzące Wydarzenia")
    conn = create_connection()
    if conn is None:
        return
    try:
        events = pd.read_sql_query(
            "SELECT clubs.name, event_name, event_date, location, description FROM club_events JOIN clubs ON club_events.club_id = clubs.id",
            conn)
        if events.empty:
            st.info("Brak nadchodzących wydarzeń.")
        else:
            for event in events.itertuples():
                st.markdown(f"### {event.event_name} w klubie {event.name}")
                st.write(f"Data: {event.event_date}")
                st.write(f"Miejsce: {event.location}")
                st.write(f"Opis: {event.description}")
    except sqlite3.Error as e:
        st.error(f"Błąd dostępu do bazy danych: {e}")
    finally:
        conn.close()

# Main application
def main():
    initialize_db()
    st.set_page_config(page_title="Aplikacja Klubowa", layout="wide")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    st.markdown('<h1 class="title">📌 Aplikacja Klubowa</h1>', unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        menu = ["Logowanie", "Rejestracja", "Panel Administracyjny"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Rejestracja":
            register_user()
        elif choice == "Logowanie":
            login_user()
        elif choice == "Panel Administracyjny":
            admin_dashboard()
    else:
        apply_customizations()
        menu = ["Profil", "Utwórz klub", "Lista klubów", "Galeria", "Mapa Pogody", "Wiadomości", "Powiadomienia", "Wydarzenia", "Wyloguj"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Profil":
            st.subheader(f"Profil użytkownika: {st.session_state['username']}")
            set_user_customizations()

        elif choice == "Utwórz klub":
            create_club()

        elif choice == "Lista klubów":
            view_clubs()

        elif choice == "Galeria":
            st.write("Wybierz klub z listy klubów, żeby zobaczyć jego galerię.")

        elif choice == "Mapa Pogody":
            st.info("Funkcjonalność mapy będzie rozwijana.")

        elif choice == "Wiadomości":
            show_messages()
            send_message()

        elif choice == "Powiadomienia":
            show_notifications()

        elif choice == "Wydarzenia":
            manage_events()
            display_events()

        elif choice == "Wyloguj":
            logout()

if __name__ == "__main__":
    main()