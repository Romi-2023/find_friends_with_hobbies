import os
import streamlit as st
from deep_translator import GoogleTranslator
from functools import lru_cache
import time
import requests
import bcrypt
import psycopg2
import pandas as pd
import logging
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium

# Set up page configuration
st.set_page_config(page_title="Znajdź przyjaciół z hobby", layout="wide")

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
        margin-bottom: 10px;
        font-family: 'Arial', sans-serif;
        font-size: 16px;
    }
    .reportview-container {
        padding: 2rem;
    }
    .main .block-container {
        max-width: 800px;
        padding: 2rem;
        margin: auto;
        background-color: #f7f7f7;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .title {
        font-size: 2.5rem;
        text-align: center;
        color: #333;
        font-weight: 700;
    }
    .sidebar .sidebar-content {
        background: #f0f0f5;
        color: #5f5f5f;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        padding: 10px 20px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
</style>
""", unsafe_allow_html=True)

# Translation dictionary
translations = {
    'Find friends with hobbies': {
        'en': 'Find friends with hobbies',
        'pl': 'Znajdź przyjaciół z hobby'
    },
    'Login': {
        'en': 'Login',
        'pl': 'Zaloguj się'
    },
    'Register': {
        'en': 'Register',
        'pl': 'Zarejestruj się'
    },
    'Username': {
        'en': 'Username',
        'pl': 'Nazwa użytkownika'
    },
    'Password': {
        'en': 'Password',
        'pl': 'Hasło'
    },
    'City': {
        'en': 'City',
        'pl': 'Miasto'
    },
    'I accept the terms and conditions': {
        'en': 'I accept the terms and conditions',
        'pl': 'Akceptuję warunki i zasady'
    },
    'Registration successful!': {
        'en': 'Registration successful!',
        'pl': 'Rejestracja zakończona sukcesem!'
    },
    'This user already exists.': {
        'en': 'This user already exists.',
        'pl': 'Ten użytkownik już istnieje.'
    },
    'All fields must be filled.': {
        'en': 'All fields must be filled.',
        'pl': 'Wszystkie pola muszą być wypełnione.'
    },
    'Logged in successfully!': {
        'en': 'Logged in successfully!',
        'pl': 'Zalogowano pomyślnie!'
    },
    'Invalid username or password.': {
        'en': 'Invalid username or password.',
        'pl': 'Nieprawidłowa nazwa użytkownika lub hasło.'
    },
    'Logout': {
        'en': 'Logout',
        'pl': 'Wyloguj się'
    },
    'create_club': {
        'en': 'Create Club',
        'pl': 'Stwórz klub'
    },
    'club_name': {
        'en': 'Club Name',
        'pl': 'Nazwa klubu'
    },
    'club_description': {
        'en': 'Club Description',
        'pl': 'Opis klubu'
    },
    'club_list': {
        'en': 'Club List',
        'pl': 'Lista klubów'
    },
    'gallery': {
        'en': 'Gallery',
        'pl': 'Galeria'
    },
    'Clubs Map': {
        'en': 'Clubs Map',
        'pl': 'Mapa klubów'
    },
    'Messages': {
        'en': 'Messages',
        'pl': 'Wiadomości'
    },
    'upcoming_events': {
        'en': 'Upcoming Events',
        'pl': 'Nadchodzące wydarzenia'
    },
    'select_member': {
        'en': 'Select Member',
        'pl': 'Wybierz członka'
    },
    'Search by Hobby': {
        'en': 'Search by Hobby',
        'pl': 'Szukaj po hobby'
    },
    'User Recommendations': {
        'en': 'User Recommendations',
        'pl': 'Rekomendacje użytkowników'
    },
    'terms_of_service': {
        'en': 'Terms of Service',
        'pl': 'Warunki usługi'
    },
    'menu': {
        'en': 'Menu',
        'pl': 'Menu'
    },
    'profile': {
        'en': 'Profile',
        'pl': 'Profil'
    },
    'user_profile': {
        'en': 'User Profile',
        'pl': 'Profil użytkownika'
    },
    # Dodaj więcej tłumaczeń jeśli są potrzebne
}

def translate(key, dest_language):
    return translations.get(key, {}).get(dest_language, key)

# Cached translation using deep_translator
@lru_cache(maxsize=1024)
def cached_translate(text, dest_language):
    try:
        translated = GoogleTranslator(source='auto', target=dest_language).translate(text)
        return translated
    except Exception as e:
        st.error(f"Translation error: {e}")
        return text

def language_selector():
    if 'language' not in st.session_state:
        st.session_state['language'] = 'en'  # Set a default language, e.g., English

    languages = {'en': 'English', 'pl': 'Polski'}
    selected_language = st.sidebar.selectbox("Select Language / Wybierz język", options=languages.keys(), format_func=languages.get)

    logger.info(f"Selected language: {selected_language}")

    st.session_state['language'] = selected_language

def create_connection():
    # Ensure the language is set before use
    if 'language' not in st.session_state:
        st.session_state['language'] = 'en'  # Default to English

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT')
        )
        logger.info("Connected to database.")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        st.error(translate('Database access error: {error}', st.session_state['language']).format(error=e))
        return None

def initialize_db():
    conn = create_connection()
    if conn is None:
        return
    try:
        with conn:
            logger.info("Initializing database.")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    city TEXT NOT NULL,
                    profile_picture TEXT,
                    description TEXT DEFAULT ''
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hobbies (
                    username TEXT NOT NULL,
                    hobby TEXT NOT NULL,
                    PRIMARY KEY (username, hobby),
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clubs (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    city TEXT NOT NULL,
                    description TEXT,
                    members_count INTEGER DEFAULT 0,
                    latitude REAL,
                    longitude REAL
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS members (
                    username TEXT NOT NULL,
                    club_id INTEGER NOT NULL,
                    PRIMARY KEY (username, club_id),
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    club_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    review TEXT,
                    FOREIGN KEY (username) REFERENCES users(username),
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS media_gallery (
                    id SERIAL PRIMARY KEY,
                    club_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    media_path TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS private_messages (
                    id SERIAL PRIMARY KEY,
                    sender TEXT NOT NULL,
                    receiver TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender) REFERENCES users(username),
                    FOREIGN KEY (receiver) REFERENCES users(username)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_customizations (
                    username TEXT PRIMARY KEY,
                    background_color TEXT DEFAULT '#FFFFFF',
                    font_size TEXT DEFAULT 'medium',
                    font_family TEXT DEFAULT 'Arial',
                    theme TEXT DEFAULT 'light',
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS club_events (
                    id SERIAL PRIMARY KEY,
                    club_id INTEGER NOT NULL,
                    event_name TEXT NOT NULL,
                    event_date DATE NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (club_id) REFERENCES clubs(id)
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS forum_messages (
                    id SERIAL PRIMARY KEY,
                    club_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (club_id) REFERENCES clubs(id),
                    FOREIGN KEY (username) REFERENCES users(username)
                );
            ''')
            conn.commit()
            logger.info("Tables created successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
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
        response = requests.get(f"http://wttr.in/{city}?format=%t")
        response.raise_for_status()
        temp_c = response.text.strip()
        response_f = requests.get(f"http://wttr.in/{city}?format=%t&u")
        response_f.raise_for_status()
        temp_f = response_f.text.strip()
        duration = time.time() - start_time
        log_performance('get_weather', duration)
        if temp_c:
            return f"{temp_c} (C), {temp_f} (F)"
        return "Weather data retrieval failed."
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather data retrieval failed: {e}")
        st.error("Weather data retrieval failed. Please try again later.")
        return None

def geocode_city(city_name):
    geolocator = Nominatim(user_agent="club_app")
    location = geolocator.geocode(city_name)
    if location:
        return location.latitude, location.longitude
    else:
        st.warning(f"Could not locate city: {city_name}")
        return None, None

def register_user():
    st.subheader(translate('Register', st.session_state.get('language', 'en')))
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(translate('Username', st.session_state.get('language', 'en')))
        password = st.text_input(translate('Password', st.session_state.get('language', 'en')), type="password")
    with col2:
        city = st.text_input(translate('City', st.session_state.get('language', 'en')))

    # Dodanie unikalnego klucza do checkboxów
    show_terms = st.checkbox(translate("I accept the terms and conditions", st.session_state.get('language', 'en')), value=False, key='show_terms')

    if show_terms:
        show_terms_of_service()

    terms_accepted = st.checkbox(translate('I accept the terms and conditions', st.session_state.get('language', 'en')), disabled=not show_terms, key='terms_accepted')
    privacy_policy_accepted = st.checkbox(translate("I accept the privacy policy", st.session_state.get('language', 'en')), disabled=not show_terms, key='privacy_policy_accepted')

    if st.button(translate('Register', st.session_state.get('language', 'en'))):
        if username and password and city and terms_accepted and privacy_policy_accepted:
            hashed_pw = hash_password(password)
            with create_connection() as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password, city, description) VALUES (%s, %s, %s, '')",
                        (username, hashed_pw, city)
                    )
                    conn.commit()
                    st.success(translate('Registration successful!', st.session_state.get('language', 'en')))
                    logger.info(f"User {username} registered.")
                except psycopg2.IntegrityError:
                    st.error(translate('This user already exists.', st.session_state.get('language', 'en')))
                except Exception as e:
                    st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
                    logger.error(f"Database access error: {e}")
        else:
            st.warning(translate('All fields must be filled.', st.session_state.get('language', 'en')))

def show_terms_of_service():
    st.subheader(translate('terms_of_service', st.session_state.get('language', 'en')))
    st.markdown("""
    1. **General Provisions**  
       - These terms of service outline the rules for using the club app.  
       - Using the app implies acceptance of these terms.
    2. **Registration and User Account**  
       - Users must register an account using real information.  
       - Users are responsible for the security of their account and password.
    3. **App Usage Rules**  
       - Users agree to use the app in accordance with applicable law and good manners.  
       - Posting offensive, illegal, or socially unacceptable content is prohibited.
    4. **Privacy and Data Storage**  
       - The app stores user data for the proper functioning of services.  
       - User data will not be shared with third parties without user consent, except as required by law.
    5. **Liability**  
       - The app creators are not liable for any damages resulting from using the app.  
       - Users agree to take full responsibility for their actions in the app.
    6. **Changes to Terms**  
       - The terms may change. Users will be notified of any changes.  
       - Continued use of the app after changes implies acceptance of the new terms.
    7. **Contact and Technical Support**  
       - Direct all questions and concerns regarding app operation to: support@example.com.
    """)

def login_user():
    logger.debug("Entering login_user function")
    st.subheader(translate('Login', st.session_state.get('language', 'en')))
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input(translate('Username', st.session_state.get('language', 'en')))
    with col2:
        password = st.text_input(translate('Password', st.session_state.get('language', 'en')), type="password")
    if st.button(translate('Login', st.session_state.get('language', 'en'))):
        logger.debug("Login button clicked")
        with create_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and check_password(user[0], password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['active_page'] = "profile"
                    st.success(translate('Logged in successfully!', st.session_state.get('language', 'en')))
                    logger.info(f"User {username} logged in successfully.")
                    st.rerun()
                else:
                    st.error(translate('Invalid username or password.', st.session_state.get('language', 'en')))
            except Exception as e:
                logger.error(f"Error during login process: {e}")
                st.error("An error occurred while processing your request. Please try again.")

def logout():
    st.session_state['logged_in'] = False
    st.success(translate("Logged out successfully!", st.session_state.get('language', 'en')))
    st.rerun()

def set_user_customizations():
    st.subheader(translate('user_profile', st.session_state.get('language', 'en')))
    st.subheader(translate('Your Hobbies', st.session_state.get('language', 'en')))
    hobby_list = ["Reading", "Sports", "Traveling", "Cooking", "Music", "Others"]
    selected_hobbies = st.multiselect(translate('Select Your Hobbies', st.session_state.get('language', 'en')), hobby_list)
    new_hobby = st.text_input(translate('Or Add a New Hobby', st.session_state.get('language', 'en')))
    if st.button(translate('Save Hobbies', st.session_state.get('language', 'en'))):
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hobbies WHERE username = %s", (st.session_state['username'],))
            for hobby in selected_hobbies:
                cursor.execute("INSERT INTO hobbies (username, hobby) VALUES (%s, %s)", (st.session_state['username'], hobby))
            if new_hobby:
                cursor.execute("INSERT INTO hobbies (username, hobby) VALUES (%s, %s)", (st.session_state['username'], new_hobby))
            conn.commit()
            st.success(translate('Hobbies updated!', st.session_state.get('language', 'en')))
            logger.info(f"User {st.session_state['username']} updated hobbies.")

def apply_customizations():
    username = st.session_state.get('username')
    if not username:
        st.error("Error: No username in session.")
        return
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT background_color, font_size, font_family, theme FROM user_customizations WHERE username = %s", (username,))
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
            st.info(translate('No customization settings for this user.', st.session_state.get('language', 'en')))
            logger.warning("No customization settings found for user.")

def admin_dashboard():
    st.subheader(translate('admin', st.session_state.get('language', 'en')))
    analytics_choice = st.radio(translate("Select Analysis Type", st.session_state.get('language', 'en')), ("User Activity", "Club Statistics"))
    with create_connection() as conn:
        try:
            if analytics_choice == "Club Statistics":
                club_stats = pd.read_sql_query("SELECT name, members_count FROM clubs", conn)
                st.bar_chart(club_stats.set_index('name'))
            users = pd.read_sql_query("SELECT * FROM users", conn)
            clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
        except Exception as e:
            st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
            logger.error(f"Database access error: {e}")

    st.write(translate("User List:", st.session_state.get('language', 'en')))
    st.table(users)

    if not users.empty:
        user_to_delete = st.selectbox(translate("Select a user to delete", st.session_state.get('language', 'en')), users['username'])
        if st.button(translate("Delete selected user", st.session_state.get('language', 'en'))):
            with create_connection() as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM users WHERE username = %s", (user_to_delete,))
                    conn.commit()
                    st.success(translate(f"User {user_to_delete} deleted!", st.session_state.get('language', 'en')))
                    logger.info(f"Deleted user {user_to_delete}.")
                except Exception as e:
                    st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
                    logger.error(f"Database access error: {e}")

    st.write(translate("Club List:", st.session_state.get('language', 'en')))
    st.table(clubs)

    if not clubs.empty:
        club_to_delete = st.selectbox(translate("Select a club to delete", st.session_state.get('language', 'en')), clubs['name'])
        if st.button(translate("Delete selected club", st.session_state.get('language', 'en'))):
            with create_connection() as conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM clubs WHERE name = %s", (club_to_delete,))
                    conn.commit()
                    st.success(translate(f"Club {club_to_delete} deleted!", st.session_state.get('language', 'en')))
                    logger.info(f"Deleted club {club_to_delete}.")
                except Exception as e:
                    st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
                    logger.error(f"Database access error: {e}")

def create_club():
    st.subheader(translate('create_club', st.session_state.get('language', 'en')))
    club_name = st.text_input(translate('club_name', st.session_state.get('language', 'en')))
    city = st.text_input(translate('City', st.session_state.get('language', 'en')))
    description = st.text_area(translate('club_description', st.session_state.get('language', 'en')))
    if st.button(translate('create_club', st.session_state.get('language', 'en'))):
        lat, lon = geocode_city(city)
        if lat is None and lon is None:
            return
        with create_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO clubs (name, city, description, members_count, latitude, longitude) VALUES (%s, %s, %s, 0, %s, %s)",
                    (club_name, city, description, lat, lon)
                )
                conn.commit()
                st.success(translate(f"Club {club_name} created!", st.session_state.get('language', 'en')))
                logger.info(f"Club {club_name} successfully added.")
                show_osm_map()
            except psycopg2.Error as e:
                st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
                logger.error(f"Database access error: {e}")

def search_by_hobby():
    st.subheader(translate("Search by Hobby", st.session_state.get('language', 'en')))
    hobby_search = st.text_input(translate("Enter a hobby to find users", st.session_state.get('language', 'en')))
    if st.button(translate("Search", st.session_state.get('language', 'en'))):
        with create_connection() as conn:
            users_with_hobby = pd.read_sql_query(
                "SELECT users.username, users.city FROM hobbies INNER JOIN users ON hobbies.username = users.username WHERE hobby = %s",
                conn, params=(hobby_search,)
            )
            if users_with_hobby.empty:
                st.info(translate("No users found with this hobby.", st.session_state.get('language', 'en')))
            else:
                st.table(users_with_hobby)

def recommend_users():
    st.subheader(translate("User Recommendations", st.session_state.get('language', 'en')))
    username = st.session_state.get('username')
    if not username:
        st.warning(translate("You need to log in to get recommendations.", st.session_state.get('language', 'en')))
        return
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT h2.username, COUNT(h2.hobby) as shared_hobbies FROM hobbies h1 INNER JOIN hobbies h2 ON h1.hobby = h2.hobby WHERE h1.username = %s AND h2.username != %s GROUP BY h2.username ORDER BY shared_hobbies DESC LIMIT 5",
            (username, username)
        )
        recommendations = cursor.fetchall()
        if recommendations:
            for rec in recommendations:
                st.write(translate(f"User: {rec[0]}, Shared Hobbies: {rec[1]}", st.session_state.get('language', 'en')))
        else:
            st.info(translate("No recommendations available.", st.session_state.get('language', 'en')))

def view_clubs():
    st.subheader(translate('club_list', st.session_state.get('language', 'en')))
    search_term = st.text_input(translate('search_clubs', st.session_state.get('language', 'en')))

    # Nawiązywanie połączenia z bazą danych
    conn = create_connection()  
    if conn is None:
        st.error("Failed to establish a database connection.")
        return

    try:
        df = pd.read_sql_query("SELECT * FROM clubs", conn)
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) | df['city'].str.contains(search_term, case=False)]
        if df.empty:
            st.info(translate("No clubs to display.", st.session_state.get('language', 'en')))
            return
        for index, row in df.iterrows():
            st.markdown(f"### {row['name']} ({row['city']})")
            st.write(row['description'])
            weather = get_weather(row['city'])
            if weather:
                st.write(f"{translate('weather', st.session_state.get('language', 'en'))}: {weather}")
            else:
                st.warning(translate("Could not retrieve weather data for this city.", st.session_state.get('language', 'en')))
            st.write(f"{translate('members', st.session_state.get('language', 'en'))}: {row['members_count']}")
            rating = calculate_average_rating(row['id'])
            st.write(f"{translate('average_rating', st.session_state.get('language', 'en'))}: {rating}")

            username = st.session_state.get('username')
            is_member = False
            if username:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM members WHERE username = %s AND club_id = %s", (username, row['id']))
                is_member = cursor.fetchone() is not None

            if is_member:
                st.info(translate("You are a member of this club.", st.session_state.get('language', 'en')))
                club_forum(row['id'])

                with st.expander(translate("Add Event", st.session_state.get('language', 'en'))):
                    event_name = st.text_input("Event Name", key=f"event_name_{index}")
                    event_date = st.date_input("Event Date", key=f"event_date_{index}")
                    location = st.text_input("Event Location", key=f"event_location_{index}")
                    event_description = st.text_area("Event Description", key=f"event_description_{index}")

                    if st.button("Add Event", key=f"add_event_{index}"):
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO club_events (club_id, event_name, event_date, location, description) VALUES (%s, %s, %s, %s, %s)",
                            (row['id'], event_name, event_date, location, event_description)
                        )
                        conn.commit()
                        st.success(translate("Event added!", st.session_state.get('language', 'en')))
                        logger.info(f"Event {event_name} added to club {row['name']}.")
            else:
                st.button(f"{translate('join_club', st.session_state.get('language', 'en'))} {row['name']}", key=f"join_club_{index}", on_click=join_club, args=(row['id'],))

            with st.expander(translate("Ratings and Reviews", st.session_state.get('language', 'en'))):
                reviews = get_club_reviews(row['id'])
                for review in reviews:
                    st.write(f"**{review['username']}**: {review['rating']}/5 - {review['review']}")

                rating = st.slider(translate("Your rating", st.session_state.get('language', 'en')), 1, 5, 3, key=f"rating_slider_{index}")
                review_text = st.text_area(translate("Your review", st.session_state.get('language', 'en')), key=f"review_text_{index}")
                if st.button(translate('add_review', st.session_state.get('language', 'en')), key=f"review_{index}"):
                    add_review(row['id'], rating, review_text)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        logger.error(f"Error executing view_clubs: {e}")
    finally:
        conn.close()

def calculate_average_rating(club_id):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT AVG(rating) FROM reviews WHERE club_id = %s", (club_id,))
        result = cursor.fetchone()
        return result[0] if result else translate("No ratings", st.session_state.get('language', 'en'))

def join_club(club_id):
    username = st.session_state.get('username')
    with create_connection() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO members (username, club_id) VALUES (%s, %s)", (username, club_id))
            cursor.execute("UPDATE clubs SET members_count = members_count + 1 WHERE id = %s", (club_id,))
            conn.commit()
            st.success(translate("You have joined the club!", st.session_state.get('language', 'en')))
            st.info(translate("You can now participate in the club's forum.", st.session_state.get('language', 'en')))
            logger.info(f"User {username} joined club ID: {club_id}.")
        except psycopg2.Error as e:
            st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
            logger.error(f"Database access error: {e}")

def club_forum(club_id):
    st.subheader(translate("Club Forum", st.session_state.get('language', 'en')))
    with create_connection() as conn:
        try:
            messages = pd.read_sql_query(
                "SELECT username, message, timestamp FROM forum_messages WHERE club_id = %s ORDER BY timestamp DESC",
                conn, params=(club_id,)
            )
            for message in messages.itertuples():
                st.markdown(f"**{message.username}** at {message.timestamp}:")
                st.write(message.message)

            new_message = st.text_area(translate("Write a new message", st.session_state.get('language', 'en')))
            if st.button(translate("Send", st.session_state.get('language', 'en'))):
                if new_message.strip():
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO forum_messages (club_id, username, message) VALUES (%s, %s, %s)",
                        (club_id, st.session_state['username'], new_message)
                    )
                    conn.commit()
                    st.success(translate("Message sent!", st.session_state.get('language', 'en')))
                    logger.info(f"Message sent by {st.session_state['username']} to club ID: {club_id}.")
                    st.experimental_rerun()
                else:
                    st.warning(translate("You cannot send an empty message.", st.session_state.get('language', 'en')))
        except psycopg2.Error as e:
            st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
            logger.error(f"Database access error: {e}")

def get_club_reviews(club_id):
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, rating, review FROM reviews WHERE club_id = %s", (club_id,))
        reviews = cursor.fetchall()
        return [{'username': row[0], 'rating': row[1], 'review': row[2]} for row in reviews]

def add_review(club_id, rating, review_text):
    username = st.session_state.get('username')
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reviews (username, club_id, rating, review) VALUES (%s, %s, %s, %s)", (username, club_id, rating, review_text))
        conn.commit()
        st.success(translate("Review added!", st.session_state.get('language', 'en')))
        logger.info(f"Review added by {username} for club ID: {club_id}.")

def manage_gallery(club_id):
    st.subheader(translate('gallery', st.session_state.get('language', 'en')))
    uploaded_file = st.file_uploader(translate("Select an image or video", st.session_state.get('language', 'en')), type=['jpg', 'jpeg', 'png', 'mp4'])
    if uploaded_file:
        max_file_size = 10 * 1024 * 1024
        if uploaded_file.size > max_file_size:
            st.error(translate("File is too large! Maximum file size is 10 MB.", st.session_state.get('language', 'en')))
            return

        media_type = "video" if uploaded_file.type.startswith('video') else "image"
        file_path = os.path.join('media', f"{club_id}_{uploaded_file.name}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO media_gallery (club_id, media_type, media_path, uploaded_by) VALUES (%s, %s, %s, %s)",
                           (int(club_id), media_type, file_path, st.session_state['username']))
            conn.commit()
            st.success(translate("File added to the gallery!", st.session_state.get('language', 'en')))
            logger.info(f"File added to gallery for club ID: {club_id}.")

    with create_connection() as conn:
        media_files = pd.read_sql_query(
            "SELECT media_type, media_path FROM media_gallery WHERE club_id = %s", 
            conn,
            params=(int(club_id),))
        if not media_files.empty:
            for file in media_files.itertuples():
                if file.media_type == 'image':
                    st.image(file.media_path)
                elif file.media_type == 'video':
                    st.video(file.media_path)

def gallery():
    st.subheader(translate('gallery', st.session_state.get('language', 'en')))
    username = st.session_state.get('username')
    if not username:
        st.error(translate("User is not logged in.", st.session_state.get('language', 'en')))
        return

    with create_connection() as conn:
        query = '''
        SELECT clubs.id, clubs.name
        FROM clubs
        INNER JOIN members ON clubs.id = members.club_id
        WHERE members.username = %s
        '''
        clubs = pd.read_sql_query(query, conn, params=(username,))
        if clubs.empty:
            st.info(translate("You do not belong to any club. Become a member to manage the gallery.", st.session_state.get('language', 'en')))
            return

        club_names = clubs['name'].tolist()
        selected_club = st.selectbox(translate("Select a club", st.session_state.get('language', 'en')), club_names)

        if selected_club:
            club_id = clubs.loc[clubs['name'] == selected_club, 'id'].iloc[0]
            manage_gallery(club_id)

def show_messages():
    st.subheader(translate("Private Messages", st.session_state.get('language', 'en')))
    with create_connection() as conn:
        username = st.session_state['username']
        messages = pd.read_sql_query(
            "SELECT sender, content, timestamp FROM private_messages WHERE receiver = %s ORDER BY timestamp DESC",
            conn, params=(username,))
        if messages.empty:
            st.info(translate("No messages.", st.session_state.get('language', 'en')))
            logger.info("No messages for user.")
        else:
            for message in messages.itertuples():
                st.markdown(f"{translate('From', st.session_state.get('language', 'en'))}: {message.sender} - {message.timestamp}")
                st.write(message.content)

def send_message():
    st.subheader(translate('new_message', st.session_state.get('language', 'en')))
    receiver = st.text_input(translate("To:", st.session_state.get('language', 'en')))
    content = st.text_area(translate("Message content", st.session_state.get('language', 'en')))
    if st.button(translate('send', st.session_state.get('language', 'en'))):
        if receiver and content:
            sender = st.session_state['username']
            with create_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO private_messages (sender, receiver, content) VALUES (%s, %s, %s)", 
                             (sender, receiver, content))
                conn.commit()
                st.success(translate("Message sent!", st.session_state.get('language', 'en')))
                logger.info(f"Message sent from {sender} to {receiver}.")
        else:
            st.warning(translate("Both fields must be filled!", st.session_state.get('language', 'en')))

def manage_events():
    st.subheader(translate("Club Events", st.session_state.get('language', 'en')))
    with create_connection() as conn:
        try:
            clubs = pd.read_sql_query("SELECT * FROM clubs", conn)
            club_names = clubs['name'].unique()
            selected_club = st.selectbox(translate("Select a club", st.session_state.get('language', 'en')), club_names)
            if selected_club:
                event_name = st.text_input(translate("Event Name", st.session_state.get('language', 'en')))
                event_date = st.date_input(translate("Event Date", st.session_state.get('language', 'en')))
                location = st.text_input(translate("Event Location", st.session_state.get('language', 'en')))
                description = st.text_area(translate("Event Description", st.session_state.get('language', 'en')))
                if st.button(translate("Add Event", st.session_state.get('language', 'en'))):
                    club_id = clubs.loc[clubs['name'] == selected_club, 'id'].iloc[0]
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO club_events (club_id, event_name, event_date, location, description) VALUES (%s, %s, %s, %s, %s)",
                        (club_id, event_name, event_date, location, description))
                    conn.commit()
                    st.success(translate("Event added!", st.session_state.get('language', 'en')))
                    logger.info(f"Event {event_name} added to club {selected_club}.")
                    members = pd.read_sql_query(
                        "SELECT username FROM members WHERE club_id = %s", 
                        conn, params=(club_id,))
                    for member in members['username']:
                        cursor.execute(
                            "INSERT INTO notifications (username, message) VALUES (%s, %s)",
                            (member, f"New event: {event_name} on {event_date} at {location} for club {selected_club}.")
                        )
                    conn.commit()
        except Exception as e:
            st.error(translate('Database access error: {error}', st.session_state.get('language', 'en')).format(error=e))
            logger.error(f"Database access error: {e}")

def display_events():
    st.subheader(translate('upcoming_events', st.session_state.get('language', 'en')))
    with create_connection() as conn:
        events = pd.read_sql_query(
            '''
            SELECT 
                clubs.name AS club_name, 
                event_name, 
                event_date, 
                location, 
                club_events.description
            FROM club_events 
            JOIN clubs ON club_events.club_id = clubs.id
            ORDER BY event_date ASC
            ''',
            conn
        )
        events['event_date'] = pd.to_datetime(events['event_date'])

        if events.empty:
            st.info(translate("No upcoming events.", st.session_state.get('language', 'en')))
            logger.info("No upcoming events.")
        else:
            for event in events.itertuples():
                st.markdown(f"### {event.event_name} at club {event.club_name}")
                st.write(f"Date: {event.event_date}")
                st.write(f"Location: {event.location}")
                st.write(f"Description: {event.description}")

def show_osm_map():
    st.subheader(translate("Clubs Map", st.session_state.get('language', 'en')))
    with create_connection() as conn:
        df = pd.read_sql_query("SELECT name, latitude, longitude FROM clubs", conn)
        if df.empty:
            st.info(translate("No saved clubs to display on the map.", st.session_state.get('language', 'en')))
        else:
            avg_lat = df['latitude'].mean()
            avg_lon = df['longitude'].mean()
            m = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)

            for index, row in df.iterrows():
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=row['name'],
                    icon=folium.Icon(icon='flag')
                ).add_to(m)

            st_folium(m, width=700, height=500)

def search_member():
    st.subheader(translate('select_member', st.session_state.get('language', 'en')))
    member_name = st.text_input(translate('search', st.session_state.get('language', 'en')))
    if st.button(translate('search', st.session_state.get('language', 'en'))):
        with create_connection() as conn:
            members = pd.read_sql_query(
                "SELECT clubs.name AS club_name, members.username FROM members INNER JOIN clubs ON members.club_id = clubs.id WHERE members.username LIKE %s",
                conn, params=(f'%{member_name}%',)
            )
            if members.empty:
                st.info(translate("No results.", st.session_state.get('language', 'en')))
                logger.info("No search results for: " + member_name)
            else:
                st.table(members)
                logger.info(f"Search results for: {member_name}.")

def main():
    # Initialize session variables
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'active_page' not in st.session_state:
        st.session_state['active_page'] = 'login'
    if 'language' not in st.session_state:
        st.session_state['language'] = 'en'  # Default language

    language_selector()
    initialize_db()

    page_title_key = 'Find friends with hobbies'
    st.markdown(f'<h1 class="title">{translate(page_title_key, st.session_state["language"])}</h1>', unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        # Logic for non-logged-in users
        menu_options = [
            translate("Login", st.session_state['language']),
            translate("Register", st.session_state['language']),
            translate('terms_of_service', st.session_state['language'])
        ]
        menu_choice = st.sidebar.radio(translate("menu", st.session_state['language']), menu_options, key='menu_choice')

        if menu_choice == translate("Register", st.session_state['language']):
            register_user()
        elif menu_choice == translate("Login", st.session_state['language']):
            login_user()
        elif menu_choice == translate('terms_of_service', st.session_state['language']):
            show_terms_of_service()
    else:
        # Logic for logged-in users
        menu_options = [
            translate('profile', st.session_state['language']),
            translate("create_club", st.session_state['language']),
            translate("club_list", st.session_state['language']),
            translate("gallery", st.session_state['language']),
            translate("Clubs Map", st.session_state['language']),
            translate("Messages", st.session_state['language']),
            translate("upcoming_events", st.session_state['language']),
            translate("select_member", st.session_state['language']),
            translate("Search by Hobby", st.session_state['language']),
            translate("User Recommendations", st.session_state['language']),
            translate('terms_of_service', st.session_state['language'])
        ]
        menu_choice = st.sidebar.radio(translate("menu", st.session_state['language']), menu_options, key='menu_choice')

        if st.sidebar.button(translate('Logout', st.session_state['language'])):
            logout()

        if menu_choice == translate('profile', st.session_state['language']):
            apply_customizations()
            st.subheader(f"{translate('user_profile', st.session_state['language'])}: {st.session_state['username']}")
            set_user_customizations()
        elif menu_choice == translate("create_club", st.session_state['language']):
            create_club()
        elif menu_choice == translate("club_list", st.session_state['language']):
            view_clubs()
        elif menu_choice == translate("gallery", st.session_state['language']):
            gallery()
        elif menu_choice == translate("Clubs Map", st.session_state['language']):
            show_osm_map()
        elif menu_choice == translate("Messages", st.session_state['language']):
            show_messages()
            send_message()
        elif menu_choice == translate("upcoming_events", st.session_state['language']):
            display_events()
        elif menu_choice == translate("select_member", st.session_state['language']):
            search_member()
        elif menu_choice == translate("Search by Hobby", st.session_state['language']):
            search_by_hobby()
        elif menu_choice == translate("User Recommendations", st.session_state['language']):
            recommend_users()
        elif menu_choice == translate('terms_of_service', st.session_state['language']):
            show_terms_of_service()

if __name__ == "__main__":
    main()