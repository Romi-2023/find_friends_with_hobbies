import os
import time
import requests
import bcrypt
import sqlite3
import pandas as pd
import streamlit as st
import logging
from dotenv import load_dotenv
from geopy.geocoders import Nominatim

# Set up page configuration
st.set_page_config(page_title="Znajdz przyjaciół z hobby", layout="wide")

# Load environment variables
load_dotenv()

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MyAppLogger")

# Ensure media directory exists
if not os.path.exists('media'):
    os.makedirs('media')

# Global styles
st.markdown("""
    <style>
        .stTextInput, .stTextArea, .stSelectbox, .stCheckbox, .stButton {
            margin-bottom: 10px; /* Add spacing between elements */
        }
        .reportview-container {
            padding: 2rem;
        }
        .title {
            font-size: 2rem;
            text-align: center;
            color: #333;
        }
        .sidebar .sidebar-content {
            background: #f4f4f4;
        }
    </style>
""", unsafe_allow_html=True)

# Translation dictionary
translations = {
    'pl': {
        'title': '📌 Znajdz przyjaciół z hobby',
        'login': 'Logowanie',
        'register': 'Rejestracja',
        'admin': 'Panel Administracyjny',
        'username': 'Nazwa użytkownika',
        'password': 'Hasło',
        'city': 'Miasto',
        'accept_terms': 'Akceptuję regulamin aplikacji',
        'register_success': 'Rejestracja powiodła się!',
        'user_exists': 'Ten użytkownik już istnieje.',
        'weather': 'Pogoda',
        'members': 'Członkowie',
        'gallery': 'Galeria Klubowa',
        'logout': 'Wyloguj się',
        'user_profile': 'Profil użytkownika',
        'error_db_access': 'Błąd dostępu do bazy danych: {error}',
        'events': 'Wydarzenia',
        'upcoming_events': 'Nadchodzące Wydarzenia',
        'create_club': 'Utwórz Klub',
        'club_list': 'Lista klubów',
        'club_name': 'Nazwa Klubu',
        'club_description': 'Opis',
        'join_club': 'Dołącz do',
        'average_rating': 'Średnia ocena',
        'add_review': 'Dodaj recenzję',
        'new_message': 'Wyślij wiadomość',
        'send': 'Wyślij',
        'select_member': 'Wyszukaj członka klubu',
        'menu': 'Menu',
        'profile': 'Profil',
        'search_clubs': 'Wyszukaj kluby (według nazwy lub miasta)',
        'search': 'Szukaj',
        'language_prompt': 'Wybierz język | Choose language'
    },
    'en': {
        'title': '📌 Find friends with hobbies',
        'login': 'Login',
        'register': 'Register',
        'admin': 'Admin Panel',
        'username': 'Username',
        'password': 'Password',
        'city': 'City',
        'accept_terms': 'I accept the terms and conditions',
        'register_success': 'Registration successful!',
        'user_exists': 'This user already exists.',
        'weather': 'Weather',
        'members': 'Members',
        'gallery': 'Club Gallery',
        'logout': 'Logout',
        'user_profile': 'User Profile',
        'error_db_access': 'Database access error: {error}',
        'events': 'Events',
        'upcoming_events': 'Upcoming Events',
        'create_club': 'Create Club',
        'club_list': 'Club List',
        'club_name': 'Club Name',
        'club_description': 'Description',
        'join_club': 'Join',
        'average_rating': 'Average Rating',
        'add_review': 'Add Review',
        'new_message': 'New Message',
        'send': 'Send',
        'select_member': 'Search Club Member',
        'menu': 'Menu',
        'profile': 'Profile',
        'search_clubs': 'Search clubs (by name or city)',
        'search': 'Search',
        'language_prompt': 'Wybierz język | Choose language'
    }
}

# Function to get the current translation based on the session language
def get_translation(key):
    lang = st.session_state.get('language', 'pl')
    return translations[lang].get(key, key)

# Function to display language selection in the sidebar
def language_menu():
    st.sidebar.subheader(get_translation('language_prompt'))
    language = st.sidebar.radio("", ["Polski", "English"])
    st.session_state['language'] = 'pl' if language == "Polski" else 'en'

# Helper functions
def create_connection():
    try:
        conn = sqlite3.connect("app.db", check_same_thread=False)
        logger.info("Połączenie z bazą danych utworzone.")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Błąd połączenia z bazą danych: {e}")
        st.error(get_translation('error_db_access').format(error=e))
        return None

def initialize_db():
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            logger.info("Inicjalizacja bazy danych.")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    city TEXT NOT NULL,
                    profile_picture TEXT,
                    description TEXT DEFAULT ''
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS clubs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    description TEXT,
                    members_count INTEGER DEFAULT 0,
                    latitude REAL,
                    longitude REAL
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    username TEXT NOT NULL,
                    club_id INTEGER NOT NULL,
                    PRIMARY KEY (username, club_id),
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    club_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    review TEXT,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS media_gallery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    club_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    media_path TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    read INTEGER DEFAULT 0,
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS private_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender) REFERENCES users(username),
                    FOREIGN KEY (receiver) REFERENCES users(username)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_customizations (
                    username TEXT PRIMARY KEY,
                    background_color TEXT DEFAULT '#FFFFFF',
                    font_size TEXT DEFAULT 'medium',
                    font_family TEXT DEFAULT 'Arial',
                    theme TEXT DEFAULT 'light',
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS club_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    club_id INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            logger.info("Tabele w bazie danych zostały utworzone.")
    except sqlite3.Error as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {e}")
    finally:
        conn.close()

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))

def log_performance(endpoint, duration):
    logger.info(f"Endpoint: {endpoint}, Duration: {duration:.2f} seconds")

def get_weather(city):
    try:
        start_time = time.time()
        response_c = requests.get(f"http://wttr.in/{city}?format=%t")
        response_f = requests.get(f"http://wttr.in/{city}?format=%t&u")

        response_c.raise_for_status()
        response_f.raise_for_status()

        duration = time.time() - start_time
        log_performance('get_weather', duration)

        temp_c = response_c.text.strip()
        temp_f = response_f.text.strip()

        return f"{temp_c} (C), {temp_f} (F)"
    except requests.exceptions.RequestException as err:
        logger.error(f"Nie udało się uzyskać danych pogodowych: {err}")
        st.error(f"Nie udało się uzyskać danych pogodowych: {err}")
        return None
    
def geocode_city(city_name):
    """Fetch geolocation for city using geopy."""
    geolocator = Nominatim(user_agent="club_app")
    location = geolocator.geocode(city_name)
    if location:
        return location.latitude, location.longitude
    else:
        st.warning(f"Nie udało się znaleźć lokalizacji dla miasta: {city_name}")
        return None, None

def register_user():
    st.subheader(get_translation('register'))
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(get_translation('username'))
        password = st.text_input(get_translation('password'), type="password")
    with col2:
        city = st.text_input(get_translation('city'))
        accept_terms = st.checkbox(get_translation('accept_terms'))

    if st.button(get_translation('register')):
        if username and password and city and accept_terms:
            hashed_pw = hash_password(password)
            try:
                with create_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password, city, description) VALUES (?, ?, ?, '')",
                        (username, hashed_pw, city)
                    )
                    st.success(get_translation('register_success'))
                    logger.info(f"Użytkownik {username} zarejestrowany.")
            except sqlite3.IntegrityError:
                st.error(get_translation('user_exists'))
                logger.warning(f"Użytkownik {username} już istnieje.")
            except sqlite3.Error as e:
                st.error(get_translation('error_db_access').format(error=e))
                logger.error(f"Błąd dostępu do bazy danych: {e}")
        elif not accept_terms:
            st.warning(get_translation('accept_terms'))
        else:
            st.warning("Wszystkie pola muszą być wypełnione.")

def login_user():
    st.subheader(get_translation('login'))
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(get_translation('username'))
    with col2:
        password = st.text_input(get_translation('password'), type="password")

    if st.button(get_translation('login')):
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
                        logger.info(f"Użytkownik {username} zalogowany.")
                    else:
                        st.error("Błędna nazwa użytkownika lub hasło.")
                        logger.warning(f"Błędne dane logowania dla użytkownika: {username}.")
            except sqlite3.Error as e:
                st.error(get_translation('error_db_access').format(error=e))
                logger.error(f"Błąd dostępu do bazy danych: {e}")
            finally:
                conn.close()
        else:
            st.warning("Wszystkie pola muszą być wypełnione.")

def logout():
    st.session_state.clear()
    st.session_state['logged_in'] = False
    st.success("Wylogowano pomyślnie!")

def set_user_customizations():
    st.subheader(get_translation('user_profile'))
    # Changed the label of the color picker to a more appropriate one
    background_color = st.color_picker("Background Color", "#FFFFFF")
    font_size = st.selectbox("Font Size", ['small', 'medium', 'large'])
    font_family = st.selectbox("Font Family", ['Arial', 'Courier New', 'Comic Sans MS', 'Georgia'])
    theme = st.selectbox("Theme", ['light', 'dark'])

    if st.button("Save Settings"):
        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO user_customizations (username, background_color, font_size, font_family, theme) VALUES (?, ?, ?, ?, ?)",
                    (st.session_state['username'], background_color, font_size, font_family, theme)
                )
            st.success("Settings saved!")
            logger.info("User customization settings saved.")
        except sqlite3.Error as e:
            st.error(get_translation('error_db_access').format(error=e))
            logger.error(f"Database access error: {e}")
        finally:
            conn.close()

def apply_customizations():
    username = st.session_state.get('username')
    if not username:
        st.error("Error: No username in session state")
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
                font_size = {'small': '12', 'medium': '16', 'large': '20'}.get(font_size, '16')
                st.markdown(f"""
                    <style>
                        .reportview-container {{
                            background-color: {bg_color};
                            font-size: {font_size}px;
                            font-family: {font_family};
                        }}
                    </style>
                """, unsafe_allow_html=True)
                logger.info("User customizations applied.")
            else:
                st.info("No customization settings for this user.")
                logger.warning("No customization settings found for user.")

    except sqlite3.Error as e:
        logger.error(get_translation('error_db_access').format(error=e))
        st.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def admin_dashboard():
    st.subheader(get_translation('admin'))
    analytics_choice = st.radio("Select Analysis Type", ("User Activity", "Club Statistics"))

    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            logger.info("Loading data for admin dashboard.")
            if analytics_choice == "Club Statistics":
                club_stats = pd.read_sql_query("SELECT name, members_count FROM clubs", conn)
                st.bar_chart(club_stats.set_index('name'))

            users = pd.read_sql_query("SELECT * FROM users", conn)
            clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

    st.write("User List:")
    st.table(users)

    if not users.empty:
        user_to_delete = st.selectbox("Select a user to delete", users['username'])
        if st.button("Delete selected user"):
            conn = create_connection()
            if conn is None:
                return
            try:
                with conn:
                    conn.execute("DELETE FROM users WHERE username = ?", (user_to_delete,))
                    st.success(f"User {user_to_delete} deleted!")
                    logger.info(f"Deleted user {user_to_delete}.")
            except sqlite3.Error as e:
                st.error(get_translation('error_db_access').format(error=e))
                logger.error(get_translation('error_db_access').format(error=e))
            finally:
                conn.close()

    st.write("Club List:")
    st.table(clubs)

    if not clubs.empty:
        club_to_delete = st.selectbox("Select a club to delete", clubs['name'])
        if st.button("Delete selected club"):
            conn = create_connection()
            if conn is None:
                return
            try:
                with conn:
                    conn.execute("DELETE FROM clubs WHERE name = ?", (club_to_delete,))
                    st.success(f"Club {club_to_delete} deleted!")
                    logger.info(f"Deleted club {club_to_delete}.")
            except sqlite3.Error as e:
                st.error(get_translation('error_db_access').format(error=e))
                logger.error(get_translation('error_db_access').format(error=e))
            finally:
                conn.close()

def create_club():
    st.subheader(get_translation('create_club'))
    club_name = st.text_input(get_translation('club_name'))
    city = st.text_input(get_translation('city'))
    description = st.text_area(get_translation('club_description'))
    if st.button(get_translation('create_club')):
        conn = create_connection()
        if conn is None:
            return
        try:
            lat, lon = geocode_city(city)
            if lat is None and lon is None:
                return

            with conn:
                conn.execute(
                    "INSERT INTO clubs (name, city, description, members_count, latitude, longitude) VALUES (?, ?, ?, 0, ?, ?)",
                    (club_name, city, description, lat, lon)
                )
                st.success(f"Club {club_name} created!")
                logger.info(f"Club {club_name} successfully added.")
                show_osm_map()
        except sqlite3.Error as e:
            st.error(get_translation('error_db_access').format(error=e))
            logger.error(get_translation('error_db_access').format(error=e))
        finally:
            conn.close()

def view_clubs():
    st.subheader(get_translation('club_list'))
    search_term = st.text_input(get_translation('search_clubs'))
    conn = create_connection()
    if conn is None:
        return
    try:
        df = pd.read_sql_query("SELECT * FROM clubs", conn)
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) | df['city'].str.contains(search_term, case=False)]

        if df.empty:
            st.info("No clubs to display.")
            return

        for index, row in df.iterrows():
            st.markdown(f"### {row['name']} ({row['city']})")
            st.write(row['description'])
            weather = get_weather(row['city'])
            if weather:
                st.write(f"{get_translation('weather')}: {weather}")
            st.write(f"{get_translation('members')}: {row['members_count']}")
            rating = calculate_average_rating(row['id'])
            st.write(f"{get_translation('average_rating')}: {rating}")
            st.button(f"{get_translation('join_club')} {row['name']}", key=f"join_club_{index}", on_click=join_club, args=(row['id'],))

            with st.expander("Ratings and Reviews"):
                reviews = get_club_reviews(row['id'])
                for review in reviews:
                    st.write(f"**{review['username']}**: {review['rating']}/5 - {review['review']}")

                rating = st.slider("Your rating", 1, 5, 3, key=f"rating_slider_{index}")
                review_text = st.text_area("Your review", key=f"review_text_{index}")
                if st.button(get_translation('add_review'), key=f"review_{index}"):
                    add_review(row['id'], rating, review_text)

    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def calculate_average_rating(club_id):
    conn = create_connection()
    if conn is None:
        return "No ratings"
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(rating) FROM reviews WHERE club_id = ?", (club_id,))
        return cursor.fetchone()[0] or "No ratings"
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
        return "No ratings"
    finally:
        conn.close()

def join_club(club_id):
    username = st.session_state.get('username')
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO members (username, club_id) VALUES (?, ?)", (username, club_id))
            conn.execute("UPDATE clubs SET members_count = members_count + 1 WHERE id = ?", (club_id,))
            st.success("You have joined the club!")
            logger.info(f"User {username} joined club ID: {club_id}.")
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def get_club_reviews(club_id):
    conn = create_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, rating, review FROM reviews WHERE club_id = ?", (club_id,))
        reviews = cursor.fetchall()
        return [{'username': row[0], 'rating': row[1], 'review': row[2]} for row in reviews]
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
        return []
    finally:
        conn.close()

def add_review(club_id, rating, review_text):
    username = st.session_state.get('username')
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("INSERT INTO reviews (username, club_id, rating, review) VALUES (?, ?, ?, ?)", (username, club_id, rating, review_text))
        st.success("Review added!")
        logger.info(f"Review added by {username} for club ID: {club_id}.")
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def manage_gallery(club_id):
    st.subheader(get_translation('gallery'))
    uploaded_file = st.file_uploader("Select an image or video", type=['jpg', 'jpeg', 'png', 'mp4'])
    if uploaded_file:
        max_file_size = 10 * 1024 * 1024

        if uploaded_file.size > max_file_size:
            st.error("File is too large! Maximum file size is 10 MB.")
            return

        media_type = "video" if uploaded_file.type.startswith('video') else "image"
        file_path = os.path.join('media', f"{club_id}_{uploaded_file.name}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        conn = create_connection()
        if conn is None:
            return
        try:
            with conn:
                conn.execute("INSERT INTO media_gallery (club_id, media_type, media_path, uploaded_by) VALUES (?, ?, ?, ?)",
                             (club_id, media_type, file_path, st.session_state['username']))
            st.success("File added to the gallery!")
            logger.info(f"File added to gallery for club ID: {club_id}.")
        except sqlite3.Error as e:
            st.error(get_translation('error_db_access').format(error=e))
            logger.error(get_translation('error_db_access').format(error=e))
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
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def gallery():
    st.subheader(get_translation('gallery'))

    username = st.session_state.get('username')
    if not username:
        st.error("User is not logged in.")
        return

    conn = create_connection()
    if conn is None:
        return
    try:
        query = '''
        SELECT clubs.id, clubs.name
        FROM clubs
        INNER JOIN members ON clubs.id = members.club_id
        WHERE members.username = ?
        '''
        clubs = pd.read_sql_query(query, conn, params=(username,))

        if clubs.empty:
            st.info("You do not belong to any club. Become a member to manage the gallery.")
            return

        club_names = clubs['name'].tolist()
        selected_club = st.selectbox("Select a club", club_names)

        if selected_club:
            club_id = clubs.loc[clubs['name'] == selected_club, 'id'].iloc[0]
            manage_gallery(club_id)

    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def show_messages():
    st.subheader("Private Messages")
    conn = create_connection()
    if conn is None:
        return
    try:
        username = st.session_state['username']
        messages = pd.read_sql_query(
            "SELECT sender, content, timestamp FROM private_messages WHERE receiver = ? ORDER BY timestamp DESC",
            conn, params=(username,))
        if messages.empty:
            st.info("No messages.")
            logger.info("No messages for user.")
        else:
            for message in messages.itertuples():
                st.markdown(f"From: {message.sender} - {message.timestamp}")
                st.write(message.content)
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def send_message():
    st.subheader(get_translation('new_message'))
    receiver = st.text_input("To:")
    content = st.text_area("Message content")
    if st.button(get_translation('send')):
        if receiver and content:
            sender = st.session_state['username']
            conn = create_connection()
            if conn is None:
                return
            try:
                with conn:
                    conn.execute("INSERT INTO private_messages (sender, receiver, content) VALUES (?, ?, ?)", 
                                 (sender, receiver, content))
                st.success("Message sent!")
                logger.info(f"Message sent from {sender} to {receiver}.")
            except sqlite3.Error as e:
                st.error(get_translation('error_db_access').format(error=e))
                logger.error(get_translation('error_db_access').format(error=e))
            finally:
                conn.close()
        else:
            st.warning("Both fields must be filled!")

def show_notifications():
    st.subheader("Notifications")
    conn = create_connection()
    if conn is None:
        return
    try:
        username = st.session_state['username']
        notifications = pd.read_sql_query(
            "SELECT message, timestamp FROM notifications WHERE username = ? AND read = 0", 
            conn, params=(username,))
        if notifications.empty:
            st.info("No new notifications.")
            logger.info("No new notifications for user.")
        else:
            for notification in notifications.itertuples():
                st.write(f"{notification.timestamp} - {notification.message}")

        with conn:
            conn.execute("UPDATE notifications SET read = 1 WHERE username = ? AND read = 0", (username,))
            logger.info("Marked notifications as read.")
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def manage_events():
    st.subheader("Club Events")
    conn = create_connection()
    if conn is None:
        return
    try:
        clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
        club_names = clubs['name'].unique()
        selected_club = st.selectbox("Select a club", club_names)
        if selected_club:
            event_name = st.text_input("Event Name")
            event_date = st.date_input("Event Date")
            location = st.text_input("Event Location")
            description = st.text_area("Event Description")
            if st.button("Add Event"):
                club_id = clubs.loc[clubs['name'] == selected_club, 'id'].iloc[0]
                try:
                    with conn:
                        conn.execute(
                            "INSERT INTO club_events (club_id, event_name, event_date, location, description) VALUES (?, ?, ?, ?, ?)",
                            (club_id, event_name, event_date, location, description))
                    st.success("Event added!")
                    logger.info(f"Event {event_name} added to club {selected_club}.")
                except sqlite3.Error as e:
                    st.error(get_translation('error_db_access').format(error=e))
                    logger.error(get_translation('error_db_access').format(error=e))
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def display_events():
    st.subheader(get_translation('upcoming_events'))
    conn = create_connection()
    if conn is None:
        return
    try:
        events = pd.read_sql_query(
            '''
            SELECT 
                clubs.name, 
                event_name, 
                event_date, 
                location, 
                club_events.description
            FROM club_events 
            JOIN clubs ON club_events.club_id = clubs.id
            ''',
            conn
        )
        if events.empty:
            st.info("No upcoming events.")
            logger.info("No upcoming events.")
        else:
            for event in events.itertuples():
                st.markdown(f"### {event.event_name} at club {event.name}")
                st.write(f"Date: {event.event_date}")
                st.write(f"Location: {event.location}")
                st.write(f"Description: {event.description}")
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def show_osm_map():
    st.subheader("Clubs Map")
    conn = create_connection()
    if conn is None:
        return
    try:
        df = pd.read_sql_query("SELECT name, latitude, longitude FROM clubs", conn)
        if df.empty:
            st.info("No saved clubs to display on the map.")
        else:
            df = df[['latitude', 'longitude']]
            st.map(df)
            for index, row in df.iterrows():
                st.write(f"**{row.name}**: ({row.latitude}, {row.longitude})")
    except sqlite3.Error as e:
        st.error(get_translation('error_db_access').format(error=e))
        logger.error(get_translation('error_db_access').format(error=e))
    finally:
        conn.close()

def search_member():
    st.subheader(get_translation('select_member'))
    member_name = st.text_input(get_translation('search'))

    if st.button(get_translation('search')):
        conn = create_connection()
        if conn is None:
            return
        try:
            members = pd.read_sql_query(
                "SELECT clubs.name AS club_name, members.username FROM members INNER JOIN clubs ON members.club_id = clubs.id WHERE members.username LIKE ?",
                conn, params=(f'%{member_name}%',)
            )

            if members.empty:
                st.info("No results.")
                logger.info("No search results for: " + member_name)
            else:
                st.table(members)
                logger.info(f"Search results for: {member_name}.")
        except sqlite3.Error as e:
            st.error(get_translation('error_db_access').format(error=e))
            logger.error(get_translation('error_db_access').format(error=e))
        finally:
            conn.close()

# Main application
def main():
    initialize_db()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    language_menu()

    st.markdown(f'<h1 class="title">{get_translation("title")}</h1>', unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        menu = [get_translation("login"), get_translation("register"), get_translation("admin")]
        choice = st.sidebar.selectbox(get_translation("menu"), menu)

        if choice == get_translation("register"):
            register_user()
        elif choice == get_translation("login"):
            login_user()
        elif choice == get_translation("admin"):
            admin_dashboard()
    else:
        apply_customizations()
        menu = [get_translation("profile"), get_translation("create_club"), get_translation("club_list"), get_translation("gallery"),
                "Mapa Klubów", "Wiadomości", "Powiadomienia", get_translation("events"), get_translation("select_member"), get_translation("logout")]
        choice = st.sidebar.selectbox(get_translation("menu"), menu)

        if choice == get_translation("profile"):
            st.subheader(f"{get_translation('user_profile')}: {st.session_state['username']}")
            set_user_customizations()
        elif choice == get_translation("create_club"):
            create_club()
        elif choice == get_translation("club_list"):
            view_clubs()
        elif choice == get_translation("gallery"):
            gallery()
        elif choice == "Mapa Klubów":
            show_osm_map()
        elif choice == "Wiadomości":
            show_messages()
            send_message()
        elif choice == "Powiadomienia":
            show_notifications()
        elif choice == get_translation("events"):
            manage_events()
            display_events()
        elif choice == get_translation("select_member"):
            search_member()
        elif choice == get_translation("logout"):
            logout()

if __name__ == "__main__":
    main()