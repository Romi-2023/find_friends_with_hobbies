import html
import os
from PIL import Image
import re
import time
import uuid
import json
import mimetypes
import pathlib
import logging
import requests
import pyotp
import io
import qrcode
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import bcrypt
import psycopg2
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple

# --- Konfiguracja i moduły warstwy danych ---
import config
from config import (
    get_env, MEDIA_DIR, APP_PUBLIC_URL, ADMIN_TOTP_SECRET,
    EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_PORT, EMAIL_FROM,
    init_logging, get_logger, is_db_configured,
)
import db as _db
from db import get_connection, get_pool, db_release, initialize_db as db_initialize_db
import geo_weather
from geo_weather import get_weather_by_coords
import email_service
import uploads
from banned_words import BANNED_WORDS, all_banned_words_cached

# Inicjalizacja logowania (przed użyciem loggera)
init_logging()
logger = get_logger()

# ==============================
# Language detection
# ==============================

def detect_language_from_ip():
    try:
        import requests

        ip = requests.get("https://api.ipify.org").text
        geo = requests.get(f"https://ipapi.co/{ip}/json/").json()
        country = geo.get("country_code", "").lower()

        if country == "pl":
            return "pl"
        else:
            return "en"

    except Exception:
        return "en"

logger = logging.getLogger(__name__)

# =========================
# i18n
# =========================
translations = {
    # === APP / MENU ===
    "app_title": {"en": "Find friends with hobbies", "pl": "Znajdź przyjaciół z hobby"},
    "menu": {"en": "Menu", "pl": "Menu"},
    "dashboard_menu": {"pl": "Co w mieście", "en": "What's happening"},
    "events_menu": {"pl": "Wydarzenia", "en": "Events"},
    "friends_menu": {"pl": "Znajomi", "en": "Friends"},
    "recommendations_menu": {"pl": "Rekomendacje", "en": "Recommendations"},
    "admin_panel_menu": {"pl": "Panel admina", "en": "Admin panel"},
    "choose_view": {"pl": "Wybierz widok:", "en": "Choose a view:"},
    "contact_support": {
        "pl": "Kontakt & Wsparcie",
        "en": "Contact & Support",
    },

    # === AUTH / ACCOUNT ===
    "login": {"en": "Login", "pl": "Zaloguj się"},
    "register": {"en": "Register", "pl": "Zarejestruj się"},
    "logout": {"en": "Logout", "pl": "Wyloguj się"},
    "username": {"en": "Username", "pl": "Nazwa użytkownika"},
    "password": {"en": "Password", "pl": "Hasło"},
    "city": {"en": "City", "pl": "Miasto"},
    "login_success": {"en": "Logged in successfully!", "pl": "Zalogowano pomyślnie!"},
    "login_invalid": {
        "en": "Invalid username or password.",
        "pl": "Nieprawidłowa nazwa użytkownika lub hasło.",
    },
    "logged_out": {"en": "Logged out successfully!", "pl": "Pomyślnie wylogowano!"},
    "all_fields_required": {
        "en": "All fields must be filled.",
        "pl": "Wszystkie pola muszą być wypełnione.",
    },
    "user_exists": {"en": "This user already exists.", "pl": "Ten użytkownik już istnieje."},
    "register_success": {
        "en": "Registration successful!",
        "pl": "Rejestracja zakończona sukcesem!",
    },

    "accept_tos": {
        "en": "I accept the terms and conditions",
        "pl": "Akceptuję warunki i zasady",
    },
    "accept_privacy": {
        "en": "I accept the privacy policy",
        "pl": "Akceptuję politykę prywatności",
    },
    "accept_age": {
        "en": "I am at least 16 years old and a parent or guardian helped me create this account.",
        "pl": "Ukończyłem 16 lat i rodzic lub opiekun pomógł mi założyć to konto.",
    },

    "terms_of_service": {"en": "Terms of Service", "pl": "Warunki usługi"},
        "club_name_city_required": {
        "pl": "Podaj nazwę klubu i miasto.",
        "en": "Please provide club name and city.",
    },
    "club_location_not_found": {
        "pl": "Nie można ustalić lokalizacji miasta – klub zostanie zapisany bez pinezki na mapie.",
        "en": "Could not determine city location – the club will be saved without a map pin.",
    },

    # --- DASHBOARD ---
    "dashboard_title": {
        "pl": "Co się dzieje w Twoim mieście ({city})",
        "en": "What's happening in your city ({city})"
    },
    "dashboard_caption": {
        "pl": "Podgląd wydarzeń i klubów powiązanych z Twoim miastem.",
        "en": "Overview of events and clubs related to your city."
    },
        "dashboard_greeting": {
        "pl": "Cześć {username}!",
        "en": "Hi {username}!",
    },
    "dashboard_greeting_sub": {
        "pl": "Miło Cię znowu widzieć. Zobacz, co nowego w Twoim mieście i klubach.",
        "en": "Good to see you back. Check what's new in your city and clubs.",
    },

    "dashboard_feed_header": {
        "pl": "Co nowego w Twoim mieście i klubach",
        "en": "What's new in your city and clubs"
    },
    "dashboard_no_feed": {
        "pl": "Na razie brak aktywności. Dołącz do klubów albo stwórz pierwsze wydarzenie! 🙂",
        "en": "No activity yet. Join some clubs or create the first event! 🙂"
    },
    "dashboard_events_header": {
        "pl": "Nadchodzące wydarzenia (TOP 5)",
        "en": "Upcoming events (TOP 5)"
    },
    "dashboard_no_events": {
        "pl": "Brak nadchodzących wydarzeń w Twoim mieście.",
        "en": "No upcoming events in your city."
    },
    "dashboard_all_events_btn": {
        "pl": "➡️ Wszystkie wydarzenia",
        "en": "➡️ All events"
    },
    "dashboard_new_clubs_header": {
        "pl": "Nowe kluby w Twoim mieście (TOP 5)",
        "en": "New clubs in your city (TOP 5)"
    },
    "dashboard_no_new_clubs": {
        "pl": "Brak nowych klubów w Twoim mieście.",
        "en": "No new clubs in your city."
    },
    "dashboard_show_all_clubs_btn": {
        "pl": "➡️ Pokaż wszystkie kluby",
        "en": "➡️ Show all clubs"
    },
    "dashboard_your_clubs_header": {
        "pl": "Twoje kluby",
        "en": "Your clubs"
    },
    "dashboard_no_clubs": {
        "pl": "Nie należysz jeszcze do żadnych klubów.",
        "en": "You don't belong to any clubs yet."
    },
    "dashboard_recommended_header": {
        "pl": "Proponowane kluby (TOP 5)",
        "en": "Recommended clubs (TOP 5)"
    },
    "dashboard_no_recommended": {
        "pl": "Na razie brak propozycji – sprawdź listę klubów.",
        "en": "No recommendations yet – check the club list."
    },
    "dashboard_join_btn": {"pl": "Dołącz do klubu", "en": "Join club"
    },
    "dashboard_join_success": {"pl": "Dołączono do klubu 🎉", "en": "You joined the club 🎉"},
    "dashboard_create_club_in_profile": {
        "pl": "Załóż klub w sekcji Profil (menu po lewej).",
        "en": "Create a club in the Profile section (left menu).",
    },
    "dashboard_suggested_caption": {
        "pl": "Propozycje klubów na podstawie Twoich zainteresowań – załóż jeden z nich:",
        "en": "Club suggestions based on your interests – create one of them:",
    },
    "for_you_header": {
        "pl": "Dla Ciebie",
        "en": "For you",
    },
    "for_you_subtitle": {
        "pl": "Kluby i wydarzenia dopasowane do Twoich zainteresowań",
        "en": "Clubs and events matched to your interests",
    },
    "for_you_clubs": {"pl": "Kluby dla Ciebie", "en": "Clubs for you"},
    "for_you_events": {"pl": "Wydarzenia dla Ciebie", "en": "Events for you"},
    "for_you_no_hobbies": {
        "pl": "Dodaj zainteresowania w profilu, żeby zobaczyć rekomendacje.",
        "en": "Add interests in your profile to see recommendations.",
    },
    "for_you_no_clubs": {
        "pl": "Brak klubów dopasowanych do Twoich hobby w tym mieście.",
        "en": "No clubs matching your hobbies in this city.",
    },
    "for_you_no_events": {
        "pl": "Brak wydarzeń w klubach dopasowanych do Twoich hobby.",
        "en": "No events in clubs matching your hobbies.",
    },
        "events_back_to_dashboard": {
        "pl": "⬅ Wróć do „Co w mieście”",
        "en": "⬅ Back to city dashboard",
    },
    "clubs_back_to_dashboard": {
        "pl": "⬅ Wróć do „Co w mieście”",
        "en": "⬅ Back to city dashboard",
    },

    # --- PROFILE / ABOUT ---
    "profile_about_too_long": {
        "pl": "Opis jest za długi – skróć go do około 600 znaków.",
        "en": "The description is too long – please shorten it to about 600 characters."
    },
        "user_recommendations": {
        "pl": "Polecani użytkownicy",
        "en": "Recommended users",
    },
        "reset_password_title": {
        "pl": "Ustaw nowe hasło",
        "en": "Set a new password",
    },
    "new_password_label": {
        "pl": "Nowe hasło",
        "en": "New password",
    },
    "repeat_new_password_label": {
        "pl": "Powtórz nowe hasło",
        "en": "Repeat new password",
    },
    "fill_both_passwords": {
        "pl": "Wpisz oba pola z hasłem.",
        "en": "Please fill in both password fields.",
    },
    "passwords_not_same": {
        "pl": "Hasła nie są takie same.",
        "en": "Passwords do not match.",
    },
    "password_reset_success": {
        "pl": "Hasło zostało zmienione. Możesz się zalogować.",
        "en": "Password has been changed. You can log in now.",
    },
        "password_too_short": {
        "pl": "Hasło musi mieć co najmniej 8 znaków.",
        "en": "Password must be at least 8 characters long.",
    },
    "password_need_upper": {
        "pl": "Hasło musi zawierać co najmniej jedną wielką literę.",
        "en": "Password must contain at least one uppercase letter.",
    },
    "password_need_lower": {
        "pl": "Hasło musi zawierać co najmniej jedną małą literę.",
        "en": "Password must contain at least one lowercase letter.",
    },
    "password_need_digit": {
        "pl": "Hasło musi zawierać co najmniej jedną cyfrę.",
        "en": "Password must contain at least one digit.",
    },
        "onboarding_title": {
        "pl": "👋 Witaj! Skonfiguruj swój profil",
        "en": "👋 Welcome! Set up your profile",
    },
    "onboarding_subtitle": {
        "pl": "To zajmie mniej niż minutę.",
        "en": "This will take less than a minute.",
    },
    "onboarding_hobbies_label": {
        "pl": "Twoje hobby",
        "en": "Your hobbies",
    },
    "onboarding_submit": {
        "pl": "✅ Zapisz i przejdź dalej",
        "en": "✅ Save and continue",
    },
    "onboarding_warning": {
        "pl": "Uzupełnij miasto i wybierz co najmniej 3 zainteresowania.",
        "en": "Fill in the city and choose at least 3 interests.",
    },
    "onboarding_success": {
        "pl": "Profil uzupełniony! 🎉",
        "en": "Profile completed! 🎉",
    },
    "onboarding_step_title": {
        "pl": "Dodaj 3 zainteresowania",
        "en": "Add 3 interests",
    },
    "onboarding_step_subtitle": {
        "pl": "Dzięki temu dopasujemy kluby i wydarzenia do Ciebie.",
        "en": "We'll match clubs and events to your interests.",
    },
    "onboarding_step_min": {
        "pl": "Wybierz co najmniej 3 zainteresowania.",
        "en": "Please select at least 3 interests.",
    },
    "onboarding_step_btn": {
        "pl": "Dalej",
        "en": "Continue",
    },

    # --- PROFILE / AVATAR ---
    "profile_avatar_cannot_load": {
        "pl": "Nie można wczytać zdjęcia.",
        "en": "Could not load the picture."
    },
    "profile_avatar_upload_label": {
        "pl": "Wgraj nowe zdjęcie (JPG / PNG)",
        "en": "Upload a new picture (JPG / PNG)"
    },
    "profile_avatar_saved": {
        "pl": "Zdjęcie zapisane ✅",
        "en": "Picture saved ✅"
    },
    "profile_avatar_error": {
        "pl": "Błąd zapisu zdjęcia.",
        "en": "Error while saving the picture."
    },
    "email_not_verified": {
    "pl": "Musisz potwierdzić adres e-mail przed zalogowaniem.",
    "en": "You must verify your e-mail address before logging in.",
    },

    # --- PROFILE / HOBBIES ---
    "hobbies_add_header": {
        "pl": "Dodaj nowe hobby",
        "en": "Add a new hobby"
    },
    "hobbies_new_label": {
        "pl": "Nowe hobby",
        "en": "New hobby"
    },
    "hobby_required": {
        "pl": "Wpisz nazwę hobby.",
        "en": "Enter a hobby name."
    },
    "hobby_added": {
        "pl": "Hobby dodane 🎉",
        "en": "Hobby added 🎉"
    },
    "hobby_add_error": {
        "pl": "Nie udało się dodać hobby.",
        "en": "Could not add the hobby."
    },
    "hobby_save_button": {
        "pl": "Zapisz hobby",
        "en": "Save hobby"
    },

    # --- PROFILE / CLUBS ---
    "profile_clubs_header": {
        "pl": "Twoje kluby",
        "en": "Your clubs"
    },
    "profile_no_clubs": {
        "pl": "Nie należysz jeszcze do żadnego klubu.",
        "en": "You don't belong to any clubs yet."
    },

    # --- PROFILE / PASSWORD ---
    "profile_change_pw_header": {
        "pl": "Zmień hasło",
        "en": "Change password"
    },
    "profile_old_pw_label": {
        "pl": "Stare hasło",
        "en": "Current password"
    },
    "profile_new_pw_label": {
        "pl": "Nowe hasło",
        "en": "New password"
    },
    "profile_new_pw2_label": {
        "pl": "Powtórz nowe hasło",
        "en": "Repeat new password"
    },
    "profile_change_pw_btn": {
        "pl": "Zmień hasło",
        "en": "Change password"
    },
    "profile_fill_all_fields": {
        "pl": "Uzupełnij wszystkie pola.",
        "en": "Fill in all fields."
    },
    "profile_pw_not_same": {
        "pl": "Nowe hasła nie są takie same.",
        "en": "New passwords are not the same."
    },
    "club_location_not_found": {
        "pl": "Nie można ustalić lokalizacji miasta – klub zostanie zapisany bez pinezki na mapie.",
        "en": "Could not determine city location – the club will be saved without a map pin.",
    },
    "club_forum": {"pl": "Forum klubu", "en": "Club forum"},
    "no_results": {"pl": "Brak wyników.", "en": "No results."
    },

    # --- PROFILE / ACHIEVEMENTS ---
    "profile_achievements_header": {
        "pl": "Twoje odznaki",
        "en": "Your achievements",
    },
    "profile_achievements_caption": {
        "pl": "Zdobywaj odznaki, dołączając do klubów i organizując wydarzenia.",
        "en": "Earn badges by joining clubs and organizing events.",
    },
    "profile_no_achievements": {
        "pl": "Nie masz jeszcze odznak. Dołącz do klubu, żeby zdobyć pierwszą! 🏅",
        "en": "You don't have any achievements yet. Join a club to earn your first one! 🏅"
    },
    "profile_achievement_unlocked_at": {
        "pl": "Zdobyto: {date}",
        "en": "Unlocked: {date}"
    },

    # --- PUBLIC VIEWS ---
    "user_not_found": {
        "pl": "Nie znaleziono użytkownika.",
        "en": "User not found."
    },
    "club_not_found": {
        "pl": "Nie znaleziono klubu.",
        "en": "Club not found."
    },
    "public_user_profile_title": {
        "pl": "Publiczny profil użytkownika",
        "en": "Public user profile"
    },
    "public_club_view_title": {
        "pl": "Publiczny widok klubu",
        "en": "Public club view"
    },
    "hobbies_title": {
        "pl": "Hobby i zainteresowania",
        "en": "Hobbies and interests"
    },
    "no_data": {
        "pl": "Brak danych.",
        "en": "No data."
    },
    "no_description": {
        "pl": "Brak opisu.",
        "en": "No description."
    },
    "no_description_yet": {"pl": "Brak opisu.", "en": "No description yet."},
    "filters_header": {"pl": "Filtry", "en": "Filters"},
    "sort_by": {"pl": "Sortowanie", "en": "Sort by"},
    "sort_newest": {"pl": "Najnowsze", "en": "Newest"},
    "sort_popular": {"pl": "Najpopularniejsze", "en": "Most popular"},
    "no_clubs_for_filters": {"pl": "Brak klubów dla wybranych filtrów.", "en": "No clubs for the selected filters."},
    "club_list_quick_select": {"pl": "Szybki wybór klubu", "en": "Quick club selection"},
    "club_list_choose_placeholder": {"pl": "— Wybierz klub —", "en": "— Choose club —"},
    "club_list_go_to_club": {"pl": "Przejdź do klubu", "en": "Go to club"},
    "status_you_are_member": {"pl": "Jesteś członkiem", "en": "You are a member"},
    "status_not_member": {"pl": "Nie należysz", "en": "You are not a member"},
    "manage_membership_hint": {"pl": "Kliknij, aby zarządzać członkostwem", "en": "Click to manage membership"},
    "details": {"pl": "Szczegóły", "en": "Details"},
    "people_count": {"pl": "osób", "en": "people"},
    "back_to_club_list": {"pl": "Wróć do listy klubów", "en": "Back to club list"},
    "no_events_organize_first": {"pl": "Brak wydarzeń dla tego klubu. Bądź pierwszą osobą, która coś zorganizuje! 😊", "en": "No events for this club yet. Be the first to organize something! 😊"},
    "no_clubs_on_map": {"pl": "Brak klubów do wyświetlenia na mapie.", "en": "No clubs to display on the map."},
    "no_upcoming_events": {"pl": "Brak nadchodzących wydarzeń.", "en": "No upcoming events."},
    "date_label": {"pl": "Data", "en": "Date"},
    "location_label": {"pl": "Miejsce", "en": "Location"},
    "description_label": {"pl": "Opis", "en": "Description"},
    "event_name_label": {"pl": "Nazwa wydarzenia", "en": "Event name"},
    "event_date_label": {"pl": "Data wydarzenia", "en": "Event date"},
    "event_time_label": {"pl": "Godzina wydarzenia", "en": "Event time"},
    "event_place_label": {"pl": "Miejsce", "en": "Location"},
    "event_desc_optional": {"pl": "Opis (opcjonalnie)", "en": "Description (optional)"},
    "event_location_label": {"pl": "Miejsce wydarzenia", "en": "Event location"},
    "event_desc_label": {"pl": "Opis wydarzenia", "en": "Event description"},
    "event_name_required": {"pl": "Podaj nazwę wydarzenia.", "en": "Please provide event name."},
    "events_my_header": {"pl": "Wydarzenia klubowe", "en": "Club events"},
    "no_clubs_join_to_add_events": {"pl": "Nie należysz jeszcze do żadnego klubu. Dołącz do klubów w zakładce „Lista klubów”, aby móc dodawać wydarzenia.", "en": "You are not a member of any club yet. Join some clubs in the “Club list” view to create events."},
    "only_members_can_add_events": {"pl": "Tylko członkowie klubu mogą dodawać wydarzenia. Dołącz do klubu, aby coś zorganizować 🙂", "en": "Only club members can create events. Join the club to organize something 🙂"},
    "stats_label": {"pl": "Statystyki", "en": "Stats"},
    "moderation_reports_label": {"pl": "Moderacja / zgłoszenia", "en": "Moderation / reports"},
    "gallery_empty": {"pl": "Brak plików w galerii – serwer jeszcze oddycha spokojnie 😎", "en": "No gallery files yet – the server disk is still chilling 😎"},
    "no_city_data": {"pl": "Brak danych o miastach.", "en": "No city data."},
    "no_clubs_short": {"pl": "Brak klubów.", "en": "No clubs."},
    "show_user_profile_btn": {"pl": "Pokaż profil użytkownika", "en": "Show user profile"},
    "no_reports_angel": {"pl": "Brak zgłoszeń – społeczność anielska 😇", "en": "No reports – angelic community 😇"},
    "report_close": {"pl": "Oznacz jako zamknięte", "en": "Mark as closed"},
    "report_reopen": {"pl": "Otwórz ponownie", "en": "Reopen"},
    "report_warn_user": {"pl": "Wyślij ostrzeżenie do użytkownika", "en": "Send warning to user"},
    "report_hide_club": {"pl": "Ukryj klub", "en": "Hide club"},
    "report_unhide_club": {"pl": "Pokaż klub", "en": "Unhide club"},
    "report_status_updated": {"pl": "Status zgłoszenia zaktualizowany.", "en": "Report status updated."},
    "report_warning_sent": {"pl": "Ostrzeżenie wysłane do użytkownika.", "en": "Warning sent to user."},
    "report_club_hidden": {"pl": "Klub ukryty.", "en": "Club hidden."},
    "report_club_unhidden": {"pl": "Klub znów widoczny.", "en": "Club visible again."},
    "notification_warning_from_admin": {"en": "You have received a warning from the administration regarding a report. Please follow the rules.", "pl": "Otrzymałeś ostrzeżenie od administracji w związku ze zgłoszeniem. Prosimy o przestrzeganie zasad."},
    "notification_join_approved": {"en": "Your request to join \"{club_name}\" was approved.", "pl": "Twoja prośba o dołączenie do klubu \"{club_name}\" została zaakceptowana."},
    "follow_btn": {"pl": "Obserwuj", "en": "Follow"},
    "message_btn": {"pl": "Wiadomość", "en": "Message"},
    "tab_same_city": {"pl": "To samo miasto", "en": "Same city"},
    "tab_online": {"pl": "Online", "en": "Online"},
    "tab_other_cities": {"pl": "Inne miasta", "en": "Other cities"},
    "unfollow_btn": {"pl": "Przestań obserwować", "en": "Unfollow"},
    "you_follow_label": {"pl": "✔ Obserwujesz", "en": "✔ You follow"},
    "db_connection_error": {"pl": "Brak połączenia z bazą.", "en": "Database connection error."},
    "language_label": {"pl": "Język", "en": "Language"},
    "admin_totp_code_label": {"pl": "Kod z aplikacji (6 cyfr)", "en": "Code from app (6 digits)"},
    "admin_totp_confirm": {"pl": "Potwierdź", "en": "Confirm"},
    "admin_totp_success": {"pl": "Kod poprawny ✅ – panel administratora odblokowany.", "en": "Code correct ✅ – admin panel unlocked."},
    "admin_totp_warning": {"pl": "🔐 Podaj 6-cyfrowy kod z aplikacji, aby wejść do panelu administratora.", "en": "🔐 Enter the 6-digit code from the app to access the admin panel."},
    "admin_totp_type_code": {"pl": "Wpisz kod.", "en": "Enter the code."},
    "admin_totp_invalid": {"pl": "Nieprawidłowy kod. Spróbuj ponownie.", "en": "Invalid code. Try again."},
    "admin_totp_verify_error": {"pl": "Błąd weryfikacji kodu.", "en": "Code verification error."},
    "admin_totp_qr_failed": {"pl": "Nie udało się wygenerować kodu QR – jeśli Twoja aplikacja pozwala, możesz skonfigurować konto ręcznie.", "en": "Failed to generate QR code – if your app allows it, you can set up the account manually."},
    "admin_exit_btn": {"pl": "Wyjdź z panelu administratora", "en": "Exit admin panel"},
    "admin_missing_config": {"pl": "Brak konfiguracji ADMIN_TOTP_SECRET – ustaw w .env.", "en": "ADMIN_TOTP_SECRET not configured – set it in .env."},

    # przycisk na logowaniu
    "forgot_password_btn": {
        "pl": "🔑 Zapomniałem hasła",
        "en": "🔑 I forgot my password",
    },

    # === PASSWORD RESET (nowe klucze) ===
    "reset_password_heading": {
        "pl": "🔑 Reset hasła",
        "en": "🔑 Password reset",
    },
    "enter_username": {
        "pl": "Podaj nazwę użytkownika",
        "en": "Enter your username",
    },
    "send_reset_link": {
        "pl": "Wyślij link resetujący",
        "en": "Send reset link",
    },
    "username_not_found_or_no_email": {
        "pl": "Nie znaleziono użytkownika lub brak przypisanego e-maila.",
        "en": "User not found or no e-mail assigned.",
    },
    "password_reset_error": {
        "pl": "Błąd generowania tokenu resetującego.",
        "en": "Error while generating reset token.",
    },
    "password_reset_email_subject": {
        "pl": "Reset hasła – Hobby App",
        "en": "Password reset – Hobby App",
    },
    "password_reset_email_body": {
        "pl": (
            "Cześć {username},\n\n"
            "Aby zresetować hasło, kliknij w link:\n\n"
            "{reset_link}\n\n"
            "Link jest ważny 30 minut.\n\n"
            "Jeśli to nie Ty – zignoruj tę wiadomość."
        ),
        "en": (
            "Hi {username},\n\n"
            "To reset your password, click this link:\n\n"
            "{reset_link}\n\n"
            "The link is valid for 30 minutes.\n\n"
            "If it wasn't you – just ignore this message."
        ),
    },
    "password_reset_email_sent": {
        "pl": "Wysłaliśmy do Ciebie maila z linkiem resetującym.",
        "en": "We have sent you an e-mail with a reset link.",
    },
    "password_reset_email_failed": {
        "pl": "Błąd przy wysyłaniu maila.",
        "en": "Error while sending the e-mail.",
    },

    # przyciski w routerze widoków (landing/login/register/reset)
    "back_to_login": {
        "pl": "🔙 Powrót do logowania",
        "en": "🔙 Back to login",
    },
    "have_account_btn": {
        "pl": "🔐 Mam już konto",
        "en": "🔐 I already have an account",
    },
    "no_account_btn": {
        "pl": "📝 Nie mam jeszcze konta",
        "en": "📝 I don't have an account yet",
    },
        "write_new_message": {
        "pl": "Napisz nową wiadomość",
        "en": "Write a new message",
    },
    "send": {
        "pl": "Wyślij",
        "en": "Send",
    },
        "content_not_allowed": {
        "pl": "W treści znalazły się słowa, których nie akceptujemy. Popraw tekst i spróbuj ponownie.",
        "en": "Your text contains words we don't allow. Please edit it and try again.",
    },

    # === TERMS & PRIVACY ===
    "terms_title": {"en": "Terms of Service", "pl": "Regulamin"},
    "privacy_title": {"en": "Privacy Policy", "pl": "Polityka prywatności"},

    "terms_text": {
        "pl": """REGULAMIN KORZYSTANIA Z APLIKACJI

1. Postanowienia ogólne

    1.1. Niniejszy regulamin określa zasady korzystania z aplikacji umożliwiającej użytkownikom odnajdywanie się, komunikację, tworzenie klubów zainteresowań oraz organizowanie spotkań.
    1.2. Administratorem aplikacji jest właściciel platformy.
    1.3. Korzystanie z aplikacji oznacza pełną akceptację niniejszego regulaminu.

2. Wiek użytkownika

    2.1. Aplikacja przeznaczona jest wyłącznie dla osób, które ukończyły 16 lat.
    2.2. Rejestrując konto, użytkownik oświadcza, że spełnia wymóg wiekowy.

3. Rejestracja i konto

    3.1. Rejestracja jest wymagana w celu korzystania z pełnej funkcjonalności aplikacji.
    3.2. Użytkownik zobowiązuje się do podania prawdziwych danych.
    3.3. Użytkownik ponosi pełną odpowiedzialność za bezpieczeństwo swojego konta i hasła.

4. Zasady korzystania z aplikacji

    4.1. Zabrania się:
    - publikowania treści niezgodnych z prawem,
    - obrażania innych użytkowników,
    - podszywania się pod inne osoby,
    - rozsyłania spamu,
    - prób włamań i obchodzenia zabezpieczeń.

5. Treści użytkowników

    5.1. Użytkownik ponosi pełną odpowiedzialność za publikowane przez siebie treści.
    5.2. Administrator nie ponosi odpowiedzialności za treści zamieszczane przez użytkowników.

6. Spotkania użytkowników

    6.1. Spotkania organizowane są na odpowiedzialność użytkowników.
    6.2. Administrator nie ponosi odpowiedzialności za szkody, wypadki ani roszczenia związane ze spotkaniami.

7. Usuwanie konta

    7.1. Użytkownik ma prawo usunąć konto w dowolnym momencie.
    7.2. Administrator ma prawo zablokować konto w przypadku naruszenia regulaminu.

8. Zmiany regulaminu

    Administrator zastrzega sobie prawo do zmiany regulaminu.

9. Prawo właściwe

    Regulamin podlega prawu kraju, w którym zarejestrowany jest administrator.
""",
        "en": """TERMS OF SERVICE

1. General provisions

    1.1. These Terms define the rules for using the application that allows users to connect, communicate, create interest clubs and organize meetings.
    1.2. The Administrator is the owner of the platform.
    1.3. Using the application means full acceptance of these Terms.

2. User age

    2.1. The application is intended only for users aged 16 or older.
    2.2. By registering, the user declares meeting the age requirement.

3. Registration and account

    3.1. Registration is required to use the full functionality.
    3.2. The user must provide truthful information.
    3.3. The user is responsible for securing their account and password.

4. Rules of use

    It is forbidden to:
    - publish illegal content,
    - harass other users,
    - impersonate others,
    - spam,
    - attempt hacking or bypassing security.

5. User content

    5.1. Users are fully responsible for the content they publish.
    5.2. The Administrator is not responsible for user-generated content.

6. Meetings

    6.1. Meetings are organized at users’ own responsibility.
    6.2. The Administrator bears no responsibility for damages or incidents.

7. Account deletion

    7.1. Users may delete their account at any time.
    7.2. The Administrator may block an account in case of violations.

8. Changes to the Terms

    The Administrator reserves the right to modify these Terms.

9. Applicable law

    These Terms are governed by the law of the country where the Administrator is registered.
""",
    },

    "privacy_text": {
        "pl": """POLITYKA PRYWATNOŚCI

1. Zakres danych

    Przetwarzane dane:

    - nazwa użytkownika,
    - hasło (szyfrowane),
    - miasto,
    - dane techniczne (logi).

2. Cel przetwarzania

    Dane są przetwarzane w celu działania aplikacji, komunikacji użytkowników i tworzenia klubów.

3. Podstawa prawna

    Dane przetwarzane są na podstawie zgody użytkownika.

4. Przechowywanie danych

    Dane przechowywane są do momentu usunięcia konta.

5. Prawa użytkownika

    Użytkownik ma prawo do wglądu, poprawiania i usunięcia danych.

6. Udostępnianie danych

    Dane nie są przekazywane podmiotom trzecim.

7. Bezpieczeństwo

    Administrator stosuje środki techniczne chroniące dane.
""",
        "en": """PRIVACY POLICY

1. Scope of data

    Processed data:

    - username,
    - encrypted password,
    - city,
    - technical logs.

2. Purpose of processing

    Data is processed to operate the application and enable communication.

3. Legal basis

    Data is processed based on user consent.

4. Data storage

    Data is stored until the account is deleted.

5. User rights

    Users have the right to access, modify and delete their data.

6. Data sharing

    Data is not shared with third parties.

7. Security

    The Administrator applies technical safeguards to protect the data.
""",
    },

    # === PROFILE / GLOBAL ===
    "profile": {"en": "Profile", "pl": "Profil"},
    "save": {"pl": "Zapisz", "en": "Save"},
    "cancel": {"pl": "Anuluj", "en": "Cancel"},
    "back": {"pl": "Wróć", "en": "Back"},
    "loading": {"pl": "Ładowanie...", "en": "Loading..."},

    "profile_about": {
        "pl": "Krótki opis o Tobie",
        "en": "Short description about you",
    },
    "profile_about_saved": {
        "pl": "Opis zapisany ✅",
        "en": "Description saved ✅",
    },
    "profile_about_error": {
        "pl": "Nie udało się zapisać opisu.",
        "en": "Could not save the description.",
    },
    "profile_avatar": {"pl": "Zdjęcie profilowe", "en": "Profile picture"},
    "profile_no_avatar": {
        "pl": "Brak zdjęcia profilowego.",
        "en": "No profile picture yet.",
    },
        "email_label_reset": {
        "pl": "E-mail (do resetu hasła)",
        "en": "E-mail (for password reset)",
    },
    "password_policy_hint": {
        "pl": "Hasło: min. 8 znaków, wielka i mała litera oraz cyfra.",
        "en": "Password: min. 8 characters, upper and lower case and digit.",
    },
    "username_too_short": {
        "pl": "Login musi mieć co najmniej 7 znaków.",
        "en": "Username must be at least 7 characters long.",
    },
    "username_not_allowed": {
        "pl": "Login nie może zawierać niedozwolonych słów.",
        "en": "Username must not contain disallowed words.",
    },
    "email_invalid": {
        "pl": "Podaj poprawny adres e-mail.",
        "en": "Enter a valid e-mail address.",
    },
    "rate_limit_register": {
        "pl": "Zbyt wiele prób rejestracji. Spróbuj za ok. 15 minut.",
        "en": "Too many registration attempts. Try again in about 15 minutes.",
    },
    "rate_limit_message": {
        "pl": "Zbyt wiele wiadomości. Poczekaj chwilę przed wysłaniem kolejnych.",
        "en": "Too many messages. Wait a moment before sending more.",
    },
    "register_created_info": {
        "pl": "Konto zostało utworzone. Teraz możesz się zalogować.",
        "en": "Your account has been created. You can log in now.",
    },
    "email_verification_subject": {
    "pl": "Potwierdź swój adres e-mail",
    "en": "Verify your e-mail address",
    },
    "email_verification_body": {
        "pl": (
            "Cześć {username},\n\n"
            "Aby aktywować swoje konto, kliknij w link:\n\n"
            "{verify_link}\n\n"
            "Jeśli to nie Ty – zignoruj tę wiadomość."
        ),
        "en": (
            "Hi {username},\n\n"
            "To activate your account, click this link:\n\n"
            "{verify_link}\n\n"
            "If this wasn't you – just ignore this message."
        ),
    },
    "verify_email_info": {
        "pl": "Na Twój adres e-mail został wysłany link aktywacyjny.",
        "en": "An activation link has been sent to your e-mail address.",
    },

    # === HOBBIES ===
    "hobbies_header": {"pl": "Twoje hobby", "en": "Your hobbies"},
    "hobby_add": {"pl": "Dodaj hobby", "en": "Add hobby"},
    "hobby_empty": {
        "pl": "Nie masz jeszcze hobby.",
        "en": "You don’t have any hobbies yet.",
    },
        "hobbies_suggestions_label": {
        "pl": "Proponowane hobby",
        "en": "Suggested hobbies",
    },

    # === CLUBS / EVENTS / REVIEWS ===
    "clubs_header": {"pl": "Kluby", "en": "Clubs"},
    "create_club": {"en": "Create Club", "pl": "Stwórz klub"},
    "club_list": {"en": "Club List", "pl": "Lista klubów"},
    "club_name": {"en": "Club Name", "pl": "Nazwa klubu"},
    "club_description": {"en": "Club Description", "pl": "Opis klubu"},
    "club_created": {
        "en": "Club {name} created!",
        "pl": "Klub {name} utworzony!",
    },
        "club_name_label": {
        "en": "Club name",
        "pl": "Nazwa klubu",
    },
    "club_city_label": {
        "en": "City",
        "pl": "Miasto",
    },
    "create_club_btn": {
        "en": "Create Club",
        "pl": "Stwórz klub",
    },
        # === CLUB PRIVACY / ROLES ===
    "club_privacy_label": {
        "en": "Club privacy",
        "pl": "Prywatność klubu",
    },
    "club_deputy_label": {
        "en": "Deputy manager (optional)",
        "pl": "Zastępca zarządcy (opcjonalnie)",
    },
    "club_deputy_hint": {
        "en": "Username of a person who can take over if you leave or become inactive.",
        "pl": "Nazwa użytkownika osoby, która może przejąć klub, gdy odejdziesz lub będziesz nieaktywny.",
    },
    "club_deputy_invalid": {
        "en": "Deputy must be an existing user and cannot be you.",
        "pl": "Zastępca musi być istniejącym użytkownikiem i nie może być Tobą.",
    },
    "club_settings_expander": {"pl": "⚙️ Ustawienia klubu", "en": "⚙️ Club settings"},
    "club_settings_deputy_caption": {"pl": "Zarządca i zastępca – zastępca może przejąć klub, gdy zarządca odejdzie.", "en": "Manager and deputy – the deputy can take over if the manager leaves."},
    "club_owner_label": {"pl": "Zarządca", "en": "Manager"},
    "club_deputy_display": {"pl": "Zastępca zarządcy", "en": "Deputy manager"},
    "club_deputy_saved": {"pl": "Zastępca zapisany.", "en": "Deputy saved."},
    "club_privacy_public": {
        "en": "Public – visible and open to everyone",
        "pl": "Publiczny – widoczny i otwarty dla wszystkich",
    },
    "club_privacy_private_request": {
        "en": "Private – visible, join via approval",
        "pl": "Prywatny – widoczny, dołączenie po akceptacji",
    },
    "club_privacy_secret": {
        "en": "Secret – hidden, only by invitation",
        "pl": "Tajny – ukryty, tylko na zaproszenie",
    },
    "club_join_request_sent": {
        "en": "Join request has been sent to club moderators.",
        "pl": "Prośba o dołączenie została wysłana do moderatorów klubu.",
    },
    "club_join_request_exists": {
        "en": "You already have a pending join request for this club.",
        "pl": "Masz już oczekującą prośbę o dołączenie do tego klubu.",
    },
    "club_is_secret": {
        "en": "This club is secret. You can only join by invitation.",
        "pl": "Ten klub jest tajny. Możesz dołączyć tylko na zaproszenie.",
    },
    "club_pending_requests": {
        "en": "Join requests",
        "pl": "Prośby o dołączenie",
    },
    "club_no_pending_requests": {
        "en": "No pending requests.",
        "pl": "Brak oczekujących próśb.",
    },
    "approve": {"en": "Approve", "pl": "Zatwierdź"},
    "reject": {"en": "Reject", "pl": "Odrzuć"},
    "club_members_section": {"en": "Club members", "pl": "Członkowie klubu"},
    "club_member_role_owner": {"en": "Owner", "pl": "Właściciel"},
    "club_member_role_moderator": {"en": "Moderator", "pl": "Moderator"},
    "club_member_role_member": {"en": "Member", "pl": "Członek"},
    "club_add_moderator": {
        "en": "Add moderator (username)",
        "pl": "Dodaj moderatora (nazwa użytkownika)",
    },
    "club_add_member_secret": {
        "en": "Invite/add member to secret club (username)",
        "pl": "Zaproś/dodaj członka do tajnego klubu (nazwa użytkownika)",
    },
    "club_action_success": {
        "en": "Action completed.",
        "pl": "Operacja zakończona.",
    },
    "club_action_error": {
        "en": "Could not perform this action.",
        "pl": "Nie udało się wykonać operacji.",
    },
    "join_club": {"en": "Join club", "pl": "Dołącz do klubu"},
    "club_join": {"pl": "Dołącz do klubu", "en": "Join club"},
    "club_leave": {"pl": "Opuść klub", "en": "Leave club"},
    "club_members": {"pl": "członków", "en": "members"},
    "club_no_events": {
        "pl": "Brak wydarzeń dla tego klubu.",
        "en": "No events for this club.",
    },
    "you_are_member": {
        "en": "You are a member of this club.",
        "pl": "Jesteś członkiem tego klubu.",
    },
        "no_permissions": {
        "en": "You do not have permission to manage this club.",
        "pl": "Nie masz uprawnień do zarządzania tym klubem.",
    },
    "username_required": {
        "en": "Username is required.",
        "pl": "Nazwa użytkownika jest wymagana.",
    },

    "members": {"en": "Members", "pl": "Członkowie"},
    "average_rating": {"en": "Average rating", "pl": "Średnia ocena"},

    "add_event": {"en": "Add Event", "pl": "Dodaj wydarzenie"},
    "event_added": {"en": "Event added!", "pl": "Wydarzenie dodane!"},
    "events_header": {"pl": "Wydarzenia", "en": "Events"},
    "event_no_upcoming": {
        "pl": "Brak nadchodzących wydarzeń.",
        "en": "No upcoming events.",
    },
        "events_back_to_dashboard": {
        "pl": "⬅ Wróć do \"Co w mieście\"",
        "en": "⬅ Back to city dashboard",
    },
        "club_name_suggestion_label": {
        "pl": "💡 Propozycje nazw (opcjonalnie)",
        "en": "💡 Name suggestions (optional)",
    },
    "club_name_suggestion_placeholder": {
        "pl": "Wybierz propozycję lub wpisz własną...",
        "en": "Pick a suggestion or type your own...",
    },

    "no_results": {
    "pl": "Brak wyników do wyświetlenia.",
    "en": "No results to display.",
    },

    "no_clubs": {"en": "No clubs to display.", "pl": "Brak klubów do wyświetlenia."},
    "search_clubs": {"en": "Search clubs", "pl": "Szukaj klubów"},
    "select_club": {"en": "Select a club", "pl": "Wybierz klub"},

    "ratings_reviews": {"en": "Ratings and Reviews", "pl": "Oceny i opinie"},
    "your_rating": {"en": "Your rating", "pl": "Twoja ocena"},
    "your_review": {"en": "Your review", "pl": "Twoja opinia"},
    "add_review": {"en": "Add review", "pl": "Dodaj opinię"},
    "review_added": {"en": "Review added!", "pl": "Opinia dodana!"},
    "no_ratings": {"en": "No ratings", "pl": "Brak ocen"},

    "upcoming_events": {"en": "Upcoming Events", "pl": "Nadchodzące wydarzenia"},

    # === WEATHER ===
    "weather": {"en": "Weather", "pl": "Pogoda"},
    "no_weather": {
        "en": "Could not retrieve weather data for this city.",
        "pl": "Nie udało się pobrać pogody dla tego miasta.",
    },

    # === GALLERY / MEDIA ===
    "gallery": {"en": "Gallery", "pl": "Galeria"},
    "clubs_map": {"en": "Clubs Map", "pl": "Mapa klubów"},
    "select_file": {"en": "Select an image or video", "pl": "Wybierz obraz lub wideo"},
    "file_too_large": {
        "en": "File is too large! Maximum file size is 10 MB.",
        "pl": "Plik za duży! Maksymalnie 10 MB.",
    },
    "file_added": {
        "en": "File added to the gallery!",
        "pl": "Plik dodany do galerii!",
    },
    "no_media": {"en": "No media yet.", "pl": "Brak mediów."},

    "not_logged_in": {"en": "User is not logged in.", "pl": "Użytkownik nie jest zalogowany."},
    "no_club_membership": {
        "en": "You do not belong to any club. Become a member to manage the gallery.",
        "pl": "Nie należysz do żadnego klubu. Dołącz, aby zarządzać galerią.",
    },

    # === PRIVATE MESSAGES ===
    "messages": {"en": "Messages", "pl": "Wiadomości"},
    "private_messages": {"en": "Private Messages", "pl": "Prywatne wiadomości"},
    "no_messages": {"en": "No messages.", "pl": "Brak wiadomości."},
    "from": {"en": "From", "pl": "Od"},
    "new_message": {"en": "New message", "pl": "Nowa wiadomość"},
    "to": {"en": "To:", "pl": "Do:"},
    "message_content": {"en": "Message content", "pl": "Treść wiadomości"},
    "both_fields": {
        "en": "Both fields must be filled!",
        "pl": "Oba pola muszą być wypełnione!",
    },
        "content_blocked": {
        "en": "This message contains disallowed words. Please rephrase.",
        "pl": "Wiadomość zawiera niedozwolone słowa. Spróbuj napisać to inaczej.",
    },
    "blocked_cannot_message": {
        "en": "You cannot send messages to this user.",
        "pl": "Nie możesz wysyłać wiadomości do tego użytkownika.",
    },

    # === MODERATION / REPORTS ===
    "report_button": {"en": "Report", "pl": "Zgłoś"},
    "report_user_title": {"en": "Report user", "pl": "Zgłoś użytkownika"},
    "report_club_title": {"en": "Report club", "pl": "Zgłoś klub"},
    "report_message_title": {"en": "Report message", "pl": "Zgłoś wiadomość"},
    "report_reason_placeholder": {
        "en": "Describe what is wrong...",
        "pl": "Opisz, co jest nie tak...",
    },
    "report_sent": {
        "en": "Report has been sent. Thank you.",
        "pl": "Zgłoszenie zostało wysłane. Dziękujemy.",
    },
    "report_error": {
        "en": "Could not save the report.",
        "pl": "Nie udało się zapisać zgłoszenia.",
    },

    # === BLOCKS ===
    "block_user": {"en": "Block user", "pl": "Zablokuj użytkownika"},
    "unblock_user": {"en": "Unblock user", "pl": "Odblokuj użytkownika"},
    "user_blocked_success": {
        "en": "User has been blocked.",
        "pl": "Użytkownik został zablokowany.",
    },
    "user_unblocked_success": {
        "en": "User has been unblocked.",
        "pl": "Użytkownik został odblokowany.",
    },
    "blocked_users_section": {
        "en": "Blocked users",
        "pl": "Zablokowani użytkownicy",
    },
    "no_blocked_users": {
        "en": "You have no blocked users.",
        "pl": "Nie masz zablokowanych użytkowników.",
    },

        # === NOTIFICATIONS ===
    "notifications_menu": {
        "en": "Notifications",
        "pl": "Powiadomienia",
    },
    "notifications_title": {
        "en": "Notifications",
        "pl": "Powiadomienia",
    },
    "notifications_empty": {
        "en": "No notifications yet.",
        "pl": "Brak powiadomień.",
    },
    "notifications_mark_read": {
        "en": "Mark as read",
        "pl": "Oznacz jako przeczytane",
    },
    "notifications_bell_label": {
        "en": "Notifications",
        "pl": "Powiadomienia",
    },
    "notification_new_message": {
        "en": "New message from {sender}",
        "pl": "Nowa wiadomość od {sender}",
    },
    "notification_new_event": {
        "en": "New event \"{event_name}\" in your club",
        "pl": "Nowe wydarzenie \"{event_name}\" w Twoim klubie",
    },

    # === FRIENDS / FOLLOW ===
    "friends_list": {"en": "Friends / Following", "pl": "Znajomi / Obserwowani"},
    "following": {"en": "Following", "pl": "Obserwowani"},
    "followers": {"en": "Followers", "pl": "Obserwujący"},
    "online": {"en": "online", "pl": "online"},
    "offline": {"en": "offline", "pl": "offline"},
    "last_activity": {"en": "Last activity", "pl": "Ostatnia aktywność"},
        "no_permissions": {
        "pl": "Brak uprawnień.",
        "en": "Insufficient permissions.",
    },

    # === ADMIN ===
    "choose_action": {"en": "Choose action", "pl": "Wybierz akcję"},
    "manage_users": {"en": "Manage Users", "pl": "Zarządzaj użytkownikami"},
    "manage_clubs": {"en": "Manage Clubs", "pl": "Zarządzaj klubami"},
    "select_user_delete": {
        "en": "Select a user to delete",
        "pl": "Wybierz użytkownika do usunięcia",
    },
    "delete_user": {"en": "Delete selected user", "pl": "Usuń wybranego użytkownika"},
    "user_deleted": {"en": "User {u} deleted!", "pl": "Użytkownik {u} usunięty!"},
    "no_users_manage": {"en": "No users to manage", "pl": "Brak użytkowników do zarządzania"},
    "select_club_delete": {
        "en": "Select a club to delete",
        "pl": "Wybierz klub do usunięcia",
    },
    "delete_club": {"en": "Delete selected club", "pl": "Usuń wybrany klub"},
    "club_deleted": {"en": "Club {c} deleted!", "pl": "Klub {c} usunięty!"},
    "no_clubs_manage": {"en": "No clubs to manage", "pl": "Brak klubów do zarządzania"},
    "admin_club_manage_expander": {"en": "Manage club (set owner / deputy)", "pl": "Zarządzaj klubem (ustaw zarządcę / zastępcę)"},
    "admin_save_club_manage": {"en": "Save owner and deputy", "pl": "Zapisz zarządcę i zastępcę"},

    "administrative_panel": {
        "en": "Administrative Panel",
        "pl": "Panel Administracyjny",
    },
    "db_error": {"en": "Database access error.", "pl": "Błąd dostępu do bazy."},
    "db_not_configured": {
        "en": "Database is not connected (demo mode). Full functionality will be available after deployment.",
        "pl": "Baza danych nie jest podłączona (tryb demonstracyjny). Pełna funkcjonalność będzie dostępna po wdrożeniu.",
    },
        "file_type_not_allowed": {
        "pl": "Niedozwolony typ pliku.",
        "en": "File type not allowed.",
    },

    # === LANDING PAGE ===
    "landing_title": {
        "pl": "Znajdź ludzi z takim samym hobby w Twoim mieście",
        "en": "Find people with the same hobby in your city",
    },
    "landing_subtitle": {
        "pl": "Dołącz do klubów, twórz wydarzenia, poznawaj ludzi i spotykaj się offline. Wszystko w jednym miejscu.",
        "en": "Join clubs, create events, meet people and hang out offline. Everything in one place.",
    },
    "landing_tile_1_title": {"pl": "Dołącz do klubów", "en": "Join clubs"},
    "landing_tile_1_desc": {"pl": "Poznawaj ludzi z Twojego miasta", "en": "Meet people from your city"},
    "landing_tile_2_title": {"pl": "Twórz wydarzenia", "en": "Create events"},
    "landing_tile_2_desc": {"pl": "Umawiaj spotkania i wypady", "en": "Plan meetings and hangouts"},
    "landing_tile_3_title": {"pl": "Odkrywaj lokalnie", "en": "Discover locally"},
    "landing_tile_3_desc": {"pl": "Sprawdzaj co dzieje się w okolicy", "en": "See what's happening nearby"},
    "landing_tile_4_title": {"pl": "Buduj społeczność", "en": "Build a community"},
    "landing_tile_4_desc": {"pl": "Twórz własne kluby", "en": "Create your own clubs"},
    "landing_cta": {"pl": "Załóż darmowe konto", "en": "Create a free account"},
    "landing_extra_header": {
        "pl": "Jak działa Find Friends with Hobbies?",
        "en": "How does Find Friends with Hobbies work?",
    },
    "landing_extra_point_1": {
        "pl": "1. Zakładasz darmowe konto, wybierasz swoje hobby i miasto.",
        "en": "1. Create a free account, choose your hobbies and city.",
    },
    "landing_extra_point_2": {
        "pl": "2. Aplikacja pokazuje Ci kluby i ludzi z Twojej okolicy z podobnymi zainteresowaniami.",
        "en": "2. The app shows you clubs and people nearby who share your interests.",
    },
    "landing_extra_point_3": {
        "pl": "3. Dołączasz do klubów, tworzysz wydarzenia i umawiasz spotkania offline lub na żywo.",
        "en": "3. You join clubs, create events and meet people offline or live mettings.",
    },

    # === INTRO / STRONA TYTUŁOWA (przed wejściem do apki) ===
    "intro_title": {
        "pl": "Znajdź przyjaciół z hobby",
        "en": "Find friends with hobbies",
    },
    "intro_tagline": {
        "pl": "Jedno miejsce. Twoje zainteresowania. Prawdziwi ludzie w Twoim mieście.",
        "en": "One place. Your interests. Real people in your city.",
    },
    "intro_benefit_1": {
        "pl": "Kluby zainteresowań – od biegania po planszówki",
        "en": "Interest clubs – from running to board games",
    },
    "intro_benefit_2": {
        "pl": "Wydarzenia i spotkania na żywo",
        "en": "Events and real-life meetups",
    },
    "intro_benefit_3": {
        "pl": "Wiadomości, galerie, mapa klubów",
        "en": "Messages, galleries, club map",
    },
    "intro_benefit_4": {
        "pl": "Za darmo i bez spamu",
        "en": "Free and no spam",
    },
    "intro_cta": {
        "pl": "Wchodzę",
        "en": "Let me in",
    },
    "intro_sub": {
        "pl": "Zarejestrujesz się w minutę. Bez zobowiązań.",
        "en": "Sign up in a minute. No commitment.",
    },

    # === START (ekran po intro – bez sidebara) ===
    "start_choose": {
        "pl": "Wybierz opcję",
        "en": "Choose an option",
    },
    "start_how_it_works": {
        "pl": "Jak to działa?",
        "en": "How does it work?",
    },
    "start_why_join": {
        "pl": "Dlaczego warto dołączyć?",
        "en": "Why join?",
    },
    "start_more_about": {
        "pl": "Więcej o aplikacji",
        "en": "More about the app",
    },
    "start_demo_btn": {
        "pl": "Wejdź w trybie demo (test bez bazy)",
        "en": "Enter demo mode (test without database)",
    },
    "demo_mode_notice": {
        "pl": "Tryb demo – baza niepodłączona. Dane są puste.",
        "en": "Demo mode – database not connected. Data is empty.",
    },
    "map_no_db_info": {
        "pl": "Baza danych nie jest skonfigurowana. Mapa jest pusta.",
        "en": "Database is not configured. Map is empty.",
    },
    "referral_invite_banner": {
        "pl": "Zaproszenie od **{ref}**. Zarejestruj się, żeby dołączyć.",
        "en": "Invited by **{ref}**. Register to join.",
    },
    "referral_thankyou": {
        "pl": "Zostałeś zaproszony przez **{ref}**. Cieszę się, że jesteś! 🎉",
        "en": "You were invited by **{ref}**. Glad you're here! 🎉",
    },
    "invite_copy_hint": {
        "pl": "Skopiuj link (Ctrl+C) i udostępnij znajomym – kto zarejestruje się z linku, będzie miał Ciebie jako polecającego.",
        "en": "Copy the link (Ctrl+C) and share with friends – anyone who registers from this link will have you as referrer.",
    },
    "invite_header": {
        "pl": "Zaproś znajomych",
        "en": "Invite friends",
    },
    "invite_text": {
        "pl": "Udostępnij ten link znajomym, aby dołączyli dzięki Tobie:",
        "en": "Share this link with your friends so they can join thanks to you:",
    },
    "invite_no_referrals": {
        "pl": "Na razie nikt nie dołączył z Twojego linku. Podziel się nim! 🙂",
        "en": "So far nobody has joined using your link. Share it! 🙂",
    },
    "invite_one_referral": {
        "pl": "1 osoba dołączyła z Twojego linku 👏",
        "en": "1 person joined using your link 👏",
    },
    "invite_many_referrals": {
        "pl": "{count} osób dołączyło z Twojego linku 🔥",
        "en": "{count} people joined using your link 🔥",
    },
    "dark_theme_dark": {"pl": "Zbalansowany (ciemne menu)", "en": "Balanced (dark menu)"},
    "dark_theme_light": {"pl": "Jasny motyw", "en": "Light theme"},
    "sidebar_expand_hint": {
        "pl": "💡 Strzałka ◀ u góry zwinie lub rozwinie to menu.",
        "en": "💡 The ◀ arrow at the top collapses or expands this menu.",
    },
    "sidebar_collapsed_hint": {
        "pl": "📂 **Menu nawigacji** jest po lewej stronie – kliknij strzałkę **▶**, aby je rozwinąć.",
        "en": "📂 **Navigation menu** is on the left – click the **▶** arrow to expand it.",
    },
    "sidebar_collapsed_ok": {"pl": "OK, rozumiem", "en": "Got it"},
    "about_menu": {"pl": "O nas", "en": "About us"},
    "about_title": {"pl": "Jak to działa?", "en": "How it works?"},
    "about_subtitle": {"pl": "Łączymy ludzi przez wspólne zainteresowania", "en": "We connect people through shared interests"},
    "about_body": {
        "pl": """
**Find Friends with Hobbies** to miejsce, w którym możesz:
- **Dołączyć do klubów** – znajdź ludzi z Twojego miasta o podobnych hobby
- **Organizować wydarzenia** – spotykaj się na żywo, nie tylko online
- **Wysyłać wiadomości** – buduj znajomości w klubach
- **Zdobywać odznaki** – za aktywność i zaangażowanie

Załóż konto, dodaj 3 zainteresowania i zobacz, co dzieje się w Twoim mieście. To zajmuje minutę.
        """,
        "en": """
**Find Friends with Hobbies** is where you can:
- **Join clubs** – find people from your city with similar hobbies
- **Organize events** – meet in person, not just online
- **Send messages** – build connections in clubs
- **Earn badges** – for activity and engagement

Create an account, add 3 interests, and see what's happening in your city. It takes a minute.
        """,
    },
    "about_cta_register": {"pl": "Zarejestruj się", "en": "Sign up"},
    "about_cta_clubs": {"pl": "Zobacz kluby", "en": "Browse clubs"},
    "partners_section_header": {"pl": "Kluby partnerskie", "en": "Partner clubs"},
    "partner_badge": {"pl": "🤝 Partner:", "en": "🤝 Partner:"},
    "partners_none": {"pl": "Brak klubów partnerskich.", "en": "No partner clubs yet."},
    "partners_show_club": {"pl": "Pokaż klub", "en": "Show club"},
    "partners_pending_invites": {"pl": "Zaproszenia do partnerstwa", "en": "Partnership invitations"},
    "partners_invited_you": {"pl": "zaprasza do partnerstwa", "en": "invites you to partner"},
    "partners_accepted": {"pl": "Partnerstwo zaakceptowane.", "en": "Partnership accepted."},
    "partners_invite_section": {"pl": "Zaproponuj partnerstwo", "en": "Invite a club to partner"},
    "partners_choose_club": {"pl": "Wybierz klub", "en": "Choose club"},
    "partners_send_invite": {"pl": "Wyślij zaproszenie", "en": "Send invitation"},
    "partners_invite_sent": {"pl": "Zaproszenie wysłane.", "en": "Invitation sent."},
    "partners_on_map_popup": {"pl": "Kluby partnerskie", "en": "Partner clubs"},

}

# =========================
# Empty state – ikony SVG (inline)
# =========================
EMPTY_STATE_SVG = {
    "calendar": '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>''',
    "club": '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>''',
    "feed": '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg>''',
    "home": '''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>''',
}


def empty_state_html(icon_type: str, message: str) -> str:
    """Zwraca HTML bloku empty state z ikoną SVG i tekstem."""
    svg = EMPTY_STATE_SVG.get(icon_type, EMPTY_STATE_SVG["feed"])
    escaped = html.escape(message)
    return f'<div class="empty-state"><div class="empty-state-icon">{svg}</div><div class="empty-state-text">{escaped}</div></div>'


# =========================
# Default Hobbies (PL / EN)
# =========================

DEFAULT_HOBBIES = {
    "pl": [
        "Bieganie",
        "Siłownia",
        "Planszówki",
        "Szachy",
        "Programowanie",
        "Fotografia",
        "Podróże",
        "Gotowanie",
        "Taniec",
        "Joga",
        "Muzyka",
        "Gra na gitarze",
        "Majsterkowanie",
        "Motoryzacja",
        "Rower",
        "Wędrówki górskie",
        "Książki",
        "Film",
        "Gry komputerowe",
        "Sztuczna inteligencja",
    ],
    "en": [
        "Running",
        "Gym",
        "Board games",
        "Chess",
        "Programming",
        "Photography",
        "Travel",
        "Cooking",
        "Dancing",
        "Yoga",
        "Music",
        "Guitar",
        "DIY",
        "Cars",
        "Cycling",
        "Hiking",
        "Books",
        "Movies",
        "Video games",
        "Artificial Intelligence",
    ],
}

# =========================
# Default Club Suggestions
# =========================

DEFAULT_CLUB_SUGGESTIONS = {
    "pl": [
        "Poranne Bieganie",
        "Planszówki & Piwo",
        "Szachowi Wojownicy",
        "Kodowanie Po Godzinach",
        "Fotografia Miejska",
        "Podróżnicy Weekendowi",
        "Gotowanie Świata",
        "Joga na Trawie",
        "Wieczory Filmowe",
        "Grupa Rowerowa",
        "Miłośnicy Gór",
        "Klub Książki",
        "Muzyczne Jam Session",
        "Gitarzyści Amatorzy",
        "Motoryzacyjne Spotkania",
        "Entuzjaści AI",
        "Gaming Nights",
        "Startup & Biznes",
        "Zdrowy Styl Życia",
        "Klub Medytacji",
    ],
    "en": [
        "Morning Runners",
        "Board Games & Beer",
        "Chess Warriors",
        "After Hours Coding",
        "Urban Photography",
        "Weekend Travelers",
        "World Cooking",
        "Yoga on the Grass",
        "Movie Nights",
        "Cycling Crew",
        "Mountain Lovers",
        "Book Club",
        "Music Jam Session",
        "Amateur Guitarists",
        "Car Meetups",
        "AI Enthusiasts",
        "Gaming Nights",
        "Startup & Business",
        "Healthy Lifestyle",
        "Meditation Club",
    ],
}

def t(key: str, **kwargs) -> str:
    """Pobiera tłumaczenie dla bieżącego języka z fallbackiem do EN."""
    lang = st.session_state.get("language", "pl")

    entry = translations.get(key)
    if entry is None:
        logger.warning("Missing translation key: %s", key)
        return key  # pokaż kod zamiast pustego stringa

    text = entry.get(lang) or entry.get("en") or next(iter(entry.values()))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            logger.warning("Format error for key %s with kwargs %s", key, kwargs)
    return text

# =========================
# Page / Globals
# =========================

st.set_page_config(
    page_title=t("app_title"),
    layout="wide",
    initial_sidebar_state="auto",  # na mobile sidebar domyślnie zwinięty
)

# Boksy informacyjne – zawsze czytelny tekst (ciemny na jasnym tle), niezależnie od motywu i CSS
def _alert_box(message: str, kind: str = "info") -> None:
    """Wyświetla boks info/warning/error/success z inline stylami – tekst zawsze czytelny."""
    if not message:
        return
    msg = str(message).strip()
    if not msg:
        return
    colors = {
        "info": ("#e0f2f1", "#0d9488", "#0f172a"),
        "warning": ("#fef3c7", "#d97706", "#1e293b"),
        "error": ("#fee2e2", "#dc2626", "#1e293b"),
        "success": ("#d1fae5", "#059669", "#1e293b"),
    }
    bg, border, text_color = colors.get(kind, colors["info"])
    safe = html.escape(msg)
    msg_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe).replace("\n", "<br>")
    st.markdown(
        f'<div style="background-color:{bg};border:1px solid {border};border-radius:8px;padding:1rem 1.25rem;color:{text_color};margin-bottom:0.5rem;">{msg_html}</div>',
        unsafe_allow_html=True,
    )


def _info_box(msg):  # noqa: D103
    _alert_box(msg, "info")


def _warning_box(msg):  # noqa: D103
    _alert_box(msg, "warning")


def _error_box(msg):  # noqa: D103
    _alert_box(msg, "error")


def _success_box(msg):  # noqa: D103
    _alert_box(msg, "success")


# Responsywność: jeden układ na telefon, tablet i komputer (bez rozjeżdżania)
def _inject_responsive_css():
    css_path = pathlib.Path(__file__).parent / ".streamlit" / "responsive.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _inject_dark_theme_css():
    """Motyw zbalansowany na CAŁĄ aplikację: ciemny sidebar (menu, przyciski), jasna treść (wszystkie zakładki), zakładki, expandery – wszystko w jednym motywie."""
    st.markdown("""
    <style>
    /* === CAŁA APLIKACJA: tło główne jasne === */
    [data-testid="stAppViewContainer"] { background-color: #f1f5f9 !important; }
    .main, .main .block-container, [data-testid="stAppViewContainer"] > div {
        background-color: #f8fafc !important;
        background: #f8fafc !important;
    }
    /* === SIDEBAR (menu boczne) – cały ciemny, wszędzie ten sam motyw === */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] [class],
    section[data-testid="stSidebar"] [class] {
        background-color: #0f172a !important;
        background: #0f172a !important;
    }
    section[data-testid="stSidebar"] *,
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] label {
        color: #f1f5f9 !important;
    }
    /* Cały tekst w głównej treści – CIEMNY na jasnym tle (pełna czytelność) */
    .main p, .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main span, .main .stMarkdown, .main label, .main li, .main td, .main th,
    .main [data-testid="stTextInput"] label, .main [data-testid="stTextArea"] label,
    .main .stRadio label, .main .stRadio span, .main .stRadio div,
    .main .stSelectbox label, .main .stCaptionContainer, .main .stCaptionContainer *,
    .main [data-testid="stCaptionContainer"], .main [data-testid="stCaptionContainer"] *,
    .main small, .main a { color: #1e293b !important; }
    .main a:hover { color: #0d9488 !important; }
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) p,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h1,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h2,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h3,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h4,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h5,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) h6,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) span,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stMarkdown,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stMarkdown *,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) label,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) li,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) td,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) th,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stTextInput"] label,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stTextArea"] label,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stRadio label,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stRadio span,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stRadio div,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stSelectbox label,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stCaptionContainer,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stCaptionContainer *,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stCaptionContainer"],
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stCaptionContainer"] *,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) small,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) a,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) div[data-testid="stMarkdown"] *,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="element-container"] {
        color: #1e293b !important;
    }
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) a:hover { color: #0d9488 !important; }
    [data-testid="stAppViewContainer"] .block-container p,
    [data-testid="stAppViewContainer"] .block-container h1, .block-container h2, .block-container h3,
    [data-testid="stAppViewContainer"] .block-container h4, .block-container h5, .block-container h6,
    [data-testid="stAppViewContainer"] .block-container span, .block-container .stMarkdown,
    [data-testid="stAppViewContainer"] .block-container .stMarkdown *, .block-container label,
    [data-testid="stAppViewContainer"] .block-container li, .block-container small, .block-container a,
    [data-testid="stAppViewContainer"] .block-container [data-testid="stCaptionContainer"],
    [data-testid="stAppViewContainer"] .block-container [data-testid="stCaptionContainer"] *,
    [data-testid="stAppViewContainer"] .block-container [data-testid="element-container"] {
        color: #1e293b !important;
    }
    [data-testid="stAppViewContainer"] .block-container a:hover { color: #0d9488 !important; }
    /* Zakładki (tabs) – w całej aplikacji jasne tło, ciemny tekst */
    [data-testid="stTabs"], [data-testid="stTabs"] > div,
    [data-testid="stTabs"] [role="tablist"], [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background-color: #f8fafc !important;
        border-color: #e2e8f0 !important;
    }
    [data-testid="stTabs"] button, [data-testid="stTabs"] [role="tab"],
    [data-testid="stTabs"] .stMarkdown, [data-testid="stTabs"] p, [data-testid="stTabs"] span, [data-testid="stTabs"] label {
        color: #1e293b !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #0d9488 !important;
    }
    /* Expandery – w całej aplikacji jasne tło, ciemny tekst */
    [data-testid="stExpander"], [data-testid="stExpander"] > div {
        background-color: #f8fafc !important;
        border-color: #e2e8f0 !important;
    }
    .main input, .main textarea,
    [data-testid="stAppViewContainer"] .block-container input,
    [data-testid="stAppViewContainer"] .block-container textarea,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) input,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) textarea {
        color: #1e293b !important;
        background-color: #ffffff !important;
    }
    /* Wszystkie teksty w sidebarze – wyraźny jasny kolor (Menu, Wybierz widok, pozycje menu) */
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio span,
    section[data-testid="stSidebar"] .stRadio div,
    section[data-testid="stSidebar"] .stRadio *,
    section[data-testid="stSidebar"] [role="radiogroup"],
    section[data-testid="stSidebar"] [role="radiogroup"] *,
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stCaptionContainer,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] small {
        color: #f1f5f9 !important;
    }
    /* Przyciski w sidebarze – ciemne tło i jasny tekst (w ciemnym motywie Streamlit daje jasne tło, stąd słaby kontrast) */
    section[data-testid="stSidebar"] .stButton > button,
    section[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid #475569 !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover,
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #334155 !important;
        color: #f1f5f9 !important;
        border-color: #64748b !important;
    }
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button span,
    section[data-testid="stSidebar"] .stButton > button label {
        color: #e2e8f0 !important;
    }
    /* Selectbox w sidebarze – etykieta jasna, rozwijana lista może być domyślna */
    section[data-testid="stSidebar"] .stSelectbox label {
        color: #cbd5e1 !important;
    }
    /* Przyciski w głównej treści – na jasnym tle: primary zielony, secondary/domyślne czytelne */
    [data-testid="stAppViewContainer"] .block-container .stButton > button:not([kind="primary"]):not([kind="tertiary"]),
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stButton > button:not([kind="primary"]):not([kind="tertiary"]),
    [data-testid="stAppViewContainer"] .main form .stButton > button:not([kind="primary"]):not([kind="tertiary"]) {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1 !important;
    }
    [data-testid="stAppViewContainer"] .block-container .stButton > button:not([kind="primary"]):not([kind="tertiary"]) *,
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stButton > button:not([kind="primary"]):not([kind="tertiary"]) *,
    [data-testid="stAppViewContainer"] .main form .stButton > button:not([kind="primary"]):not([kind="tertiary"]) * {
        color: #1e293b !important;
    }
    /* Primary – teal, tekst biały */
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) .stButton > button[kind="primary"],
    [data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) form .stButton > button[kind="primary"],
    [data-testid="stAppViewContainer"] .main .stButton > button[kind="primary"],
    [data-testid="stAppViewContainer"] .main form .stButton > button[kind="primary"] {
        background-color: #0d9488 !important;
        background: #0d9488 !important;
        color: #ffffff !important;
        border-color: #0f766e !important;
    }
    [data-testid="stAppViewContainer"] .main .stButton > button[kind="primary"] *,
    [data-testid="stAppViewContainer"] .main form .stButton > button[kind="primary"] * {
        color: #ffffff !important;
    }
    /* Secondary – na jasnym tle: szare tło, ciemny tekst (wstecz, anuluj, szczegóły) */
    [data-testid="stAppViewContainer"] .stButton > button[kind="secondary"],
    [data-testid="stAppViewContainer"] form .stButton > button[kind="secondary"] {
        background-color: #e2e8f0 !important;
        background: #e2e8f0 !important;
        color: #1e293b !important;
        border: 1px solid #cbd5e1 !important;
    }
    [data-testid="stAppViewContainer"] .stButton > button[kind="secondary"] *,
    [data-testid="stAppViewContainer"] form .stButton > button[kind="secondary"] * {
        color: #1e293b !important;
    }
    [data-testid="stAppViewContainer"] .stButton > button[kind="secondary"]:hover,
    [data-testid="stAppViewContainer"] form .stButton > button[kind="secondary"]:hover {
        background-color: #cbd5e1 !important;
        background: #cbd5e1 !important;
    }
    /* Tertiary – akcje „redukujące” (opuść, odrzuć, usuń, przestań obserwować) – delikatny czerwony */
    [data-testid="stAppViewContainer"] .stButton > button[kind="tertiary"],
    [data-testid="stAppViewContainer"] form .stButton > button[kind="tertiary"] {
        background-color: #b91c1c !important;
        background: #b91c1c !important;
        color: #ffffff !important;
        border-color: #991b1b !important;
    }
    [data-testid="stAppViewContainer"] .stButton > button[kind="tertiary"] *,
    [data-testid="stAppViewContainer"] form .stButton > button[kind="tertiary"] * {
        color: #ffffff !important;
    }
    [data-testid="stAppViewContainer"] .stButton > button[kind="tertiary"]:hover,
    [data-testid="stAppViewContainer"] form .stButton > button[kind="tertiary"]:hover {
        background-color: #dc2626 !important;
        background: #dc2626 !important;
    }
    /* Karty z ramką – jasne tło, ciemny tekst (na zbalansowanym motywie) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #f1f5f9 !important;
        border-color: #e2e8f0 !important;
        padding: 0.6rem 0.9rem !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] .stMarkdown,
    [data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p,
    [data-testid="stVerticalBlockBorderWrapper"] .stMarkdown span,
    [data-testid="stVerticalBlockBorderWrapper"] .stMarkdown strong,
    [data-testid="stVerticalBlockBorderWrapper"] p,
    [data-testid="stVerticalBlockBorderWrapper"] span,
    [data-testid="stVerticalBlockBorderWrapper"] label,
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"],
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] * {
        color: #1e293b !important;
    }
    .stExpander summary, [data-testid="stExpander"] summary,
    .main .stExpander summary, .main [data-testid="stExpander"] summary,
    .main .stExpander p, .main .stExpander span, .main .stExpander label {
        color: #1e293b !important;
    }
    .empty-state {
        background: #e0f2f1 !important;
        border-color: #0d9488 !important;
    }
    .empty-state .empty-state-text { color: #0f172a !important; }
    /* Przyciski w formularzach: secondary – szary z ciemnym tekstem; primary/tertiary – bez zmian poniżej */
    [data-testid="stAppViewContainer"] form .stButton > button:not([kind="primary"]):not([kind="tertiary"]),
    [data-testid="stAppViewContainer"] form .stButton > button:not([kind="primary"]):not([kind="tertiary"]) * {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
    }
    [data-testid="stAppViewContainer"] form .stButton > button[kind="primary"],
    [data-testid="stAppViewContainer"] form .stButton > button[data-testid="baseButton-primary"] {
        background-color: #059669 !important;
        background: #059669 !important;
        color: #ffffff !important;
        border-color: #047857 !important;
    }
    [data-testid="stAppViewContainer"] form .stButton > button[kind="primary"] *,
    [data-testid="stAppViewContainer"] form .stButton > button[data-testid="baseButton-primary"] * {
        color: #ffffff !important;
    }
    /* === BOKSY INFO/WARNING/ERROR/SUCCESS – na końcu, żeby wygrać z ogólnymi regułami tekstu === */
    /* Ciemny, czytelny tekst na jasnym tle we wszystkich alertach (Menu nawigacji…, Brak wiadomości, Brak odznak, itd.) */
    [data-testid="stAppViewContainer"] [data-testid="stAlert"],
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] *,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] p,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] span,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] div,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] .stMarkdown,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] .stMarkdown *,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] [data-testid="element-container"],
    [data-testid="stAppViewContainer"] [data-testid="stAlert"] [data-testid="element-container"] *,
    [data-testid="stAppViewContainer"] div[data-testid="stAlert"],
    [data-testid="stAppViewContainer"] div[data-testid="stAlert"] * {
        color: #0f172a !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stAlert"],
    [data-testid="stAppViewContainer"] div[data-testid="stAlert"],
    .main [data-testid="stAlert"] {
        background-color: #e0f2f1 !important;
        background: #e0f2f1 !important;
        border-color: #0d9488 !important;
    }
    /* File uploader – „Drag and drop file here”, „Limit 50MB” – ciemny tekst na jasnym tle */
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"],
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] *,
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] .stMarkdown,
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] .stMarkdown *,
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] span,
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] small {
        color: #1e293b !important;
    }
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] [data-testid="stDropzoneInput"],
    [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] [data-testid="stDropzoneInput"] * {
        color: #1e293b !important;
        background-color: #f1f5f9 !important;
    }
    </style>
    """, unsafe_allow_html=True)


_inject_responsive_css()
load_dotenv()

query_params = st.query_params
reset_token = query_params.get("reset_token")
verify_token = query_params.get("verify_email")

# referral z URL, np. /?ref=Roman
ref_username = query_params.get("ref")
if ref_username:
    st.session_state["referrer_username"] = ref_username

# Wejście do panelu admina przez URL (bez przycisku na landingu): ?admin=1
if query_params.get("admin") == "1":
    st.session_state["admin_portal"] = True
    st.session_state.pop("admin_totp_ok", None)

os.makedirs(MEDIA_DIR, exist_ok=True)

# =========================
# Language selector
# =========================
def language_selector():
    # 1️⃣ Zachowanie języka przy wylogowaniu (np. _force_language z logout)
    forced = st.session_state.pop("_force_language", None)
    if forced:
        st.session_state["language"] = forced

    # 2️⃣ Brak języka w sesji: zalogowany → z bazy; niezalogowany → wykryj z IP
    if "language" not in st.session_state:
        username = st.session_state.get("username")
        if username:
            st.session_state["language"] = get_user_language(username) or "en"
        else:
            st.session_state["language"] = detect_language_from_ip()

    current_lang = st.session_state.get("language", "pl")
    languages = {"en": "English", "pl": "Polski"}
    lang_keys = list(languages.keys())
    default_index = lang_keys.index(current_lang) if current_lang in lang_keys else 0

    # 3️⃣ Widget – osobny key, żeby zmiana języka działała od pierwszego kliknięcia
    selected = st.sidebar.selectbox(
        t("language_label"),
        options=lang_keys,
        format_func=languages.get,
        key="sidebar_lang_select",
        index=default_index,
    )
    if selected != current_lang:
        st.session_state["language"] = selected
        st.rerun()

    # 4️⃣ Zapis wyboru do bazy (ciągłość przy następnej wizycie)
    username = st.session_state.get("username")
    if username and st.session_state.get("language"):
        _save_user_language(username, st.session_state["language"])

    # --- Przycisk Panelu administratora (zawsze aktywny) ---
    st.sidebar.markdown("")  # mała przerwa

    if st.sidebar.button("🛠 " + t("admin_panel_menu"), key="admin_panel_btn"):
        # wchodzimy w tryb panelu admina, niezależnie od logowania
        st.session_state["admin_portal"] = True
        # opcjonalnie reset TOTP, żeby za każdym wejściem prosił o kod
        st.session_state.pop("admin_totp_ok", None)
        st.rerun()


def reset_password_view(token: str):
    st.subheader("🔑 " + t("reset_password_title"))

    new_pw = st.text_input(t("new_password_label"), type="password")
    new_pw2 = st.text_input(t("repeat_new_password_label"), type="password")

    if st.button(t("save"), type="primary"):
        if not new_pw or not new_pw2:
            _warning_box(t("fill_both_passwords"))
            return

        if new_pw != new_pw2:
            _error_box(t("passwords_not_same"))
            return

        ok, msg = reset_password_with_token(token, new_pw)
        if ok:
            _success_box(t("password_reset_success"))
            st.query_params.clear()
        else:
            _error_box(msg)


def verify_email_view(token: str):
    """Weryfikacja e-maila po kliknięciu linku z maila (?verify_email=...)."""
    conn = db_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT username FROM email_verifications WHERE token = %s AND used = FALSE",
            (token,),
        )
        row = cur.fetchone()
        if not row:
            _warning_box("Link wygasł lub został już użyty.")
            return
        username = row[0]
        cur.execute("UPDATE email_verifications SET used = TRUE WHERE token = %s", (token,))
        cur.execute("UPDATE users SET is_verified = TRUE WHERE username = %s", (username,))
        conn.commit()
        _success_box("E-mail zweryfikowany. Możesz się zalogować.")
    except Exception as e:
        logger.error("verify_email_view error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


# =========================
# DB (PostgreSQL) – wrapper z obsługą błędów UI
# =========================
def db_conn():
    """Pobiera połączenie z poolu; przy braku bazy zwraca None (w trybie demo bez spamu komunikatów)."""
    c = _db.db_conn()
    if c is None and is_db_configured():
        _error_box(t("db_error"))
    return c


def initialize_db():
    """Inicjalizuje schemat bazy tylko gdy baza jest włączona (nie SKIP_DB)."""
    if not is_db_configured():
        return
    if not db_initialize_db():
        _error_box(t("db_error"))


# =========================
# Auth utils
# =========================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def change_user_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Zmienia hasło użytkownika po sprawdzeniu starego.
    Zwraca (ok, message).
    """
    conn = db_conn()
    if not conn:
        return False, t("db_error")

    try:
        with conn:
            cur = conn.cursor()
            # pobierz aktualne hasło
            cur.execute(
                "SELECT password FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            if not row:
                return False, "Użytkownik nie istnieje."

            current_hashed = row[0]

            # weryfikacja starego hasła
            if not check_password(current_hashed, old_password):
                return False, "Stare hasło jest nieprawidłowe."

            # walidacja nowego hasła
            ok, msg = validate_password(new_password)
            if not ok:
                return False, msg

            # zapis nowego hasła
            new_hashed = hash_password(new_password)
            cur.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (new_hashed, username),
            )

        logger.info("Password changed for user: %s", username)
        return True, "Hasło zostało zmienione."
    except Exception as e:
        logger.error("change_user_password error: %s", e)
        return False, t("db_error")
    finally:
        db_release(conn)

def create_password_reset_token(username: str) -> str | None:
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=30)

    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()

            # dezaktywujemy stare tokeny
            cur.execute(
                "UPDATE password_resets SET used = TRUE WHERE username = %s",
                (username,)
            )

            cur.execute(
                """
                INSERT INTO password_resets (username, token, expires_at)
                VALUES (%s, %s, %s)
                """,
                (username, token, expires_at),
            )

        logger.info("Password reset token created for user: %s", username)
        return token
    except Exception as e:
        logger.error("create_password_reset_token error: %s", e)
        return None
    finally:
        db_release(conn)

def verify_password_reset_token(token: str) -> str | None:
    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, expires_at, used
                FROM password_resets
                WHERE token = %s
                """,
                (token,),
            )
            row = cur.fetchone()

            if not row:
                return None

            username, expires_at, used = row

            if used:
                return None

            if datetime.utcnow() > expires_at:
                return None

            return username
    except Exception as e:
        logger.error("verify_password_reset_token error: %s", e)
        return None
    finally:
        db_release(conn)

def reset_password_with_token(token: str, new_password: str) -> tuple[bool, str]:
    username = verify_password_reset_token(token)
    if not username:
        return False, "Token niepoprawny lub wygasł."

    ok, msg = validate_password(new_password)
    if not ok:
        return False, msg

    new_hashed = hash_password(new_password)

    conn = db_conn()
    if not conn:
        return False, t("db_error")

    try:
        with conn:
            cur = conn.cursor()

            cur.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (new_hashed, username),
            )

            cur.execute(
                "UPDATE password_resets SET used = TRUE WHERE token = %s",
                (token,),
            )

        logger.info("Password reset via token for user: %s", username)
        return True, "Hasło zostało zresetowane."
    except Exception as e:
        logger.error("reset_password_with_token error: %s", e)
        return False, t("db_error")
    finally:
        db_release(conn)


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, t("password_too_short")

    if not re.search(r"[A-Z]", password):
        return False, t("password_need_upper")

    if not re.search(r"[a-z]", password):
        return False, t("password_need_lower")

    if not re.search(r"\d", password):
        return False, t("password_need_digit")

    return True, ""

# =========================
# Filtr treści i loginu – baza wykluczonych słów (BANNED_WORDS z banned_words)
# =========================

# Minimalna długość loginu (nazwy użytkownika)
USERNAME_MIN_LEN = 7

def is_username_allowed(username: str) -> tuple[bool, str]:
    """
    Sprawdza login: min. 7 znaków oraz brak wykluczonych słów.
    Zwraca (True, "") jeśli OK, (False, komunikat_błędu) w przeciwnym razie.
    """
    if not username:
        return False, "username_required"
    if len(username) < USERNAME_MIN_LEN:
        return False, "username_too_short"
    text_lower = username.lower()
    for w in all_banned_words_cached():
        if len(w) >= 2 and w in text_lower:
            return False, "username_not_allowed"
    return True, ""

def is_content_allowed(text: str) -> bool:
    """
    Bardzo prosty filtr treści: sprawdza, czy w tekście
    nie ma żadnego z zakazanych słów (substring match).
    """
    if not text:
        return True

    lang = st.session_state.get("language", "pl")
    text_lower = text.lower()

    words = []
    words.extend(BANNED_WORDS.get(lang, []))
    words.extend(BANNED_WORDS.get("common", []))

    for w in words:
        if w and w in text_lower:
            return False
    return True


def check_password(hashed_password: str, user_password: str) -> bool:
    try:
        return bcrypt.checkpw(user_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def password_policy_ok(pw: str) -> bool:
    return len(pw) >= 8 and any(c.isdigit() for c in pw) and any(c.isalpha() for c in pw)

def rate_limit_login_ok() -> bool:
    now = time.time()
    data = st.session_state.setdefault("_login_rl", {"fail_times": []})
    data["fail_times"] = [t for t in data["fail_times"] if now - t < 900]
    return len(data["fail_times"]) < 5

def register_failed_login():
    now = time.time()
    data = st.session_state.setdefault("_login_rl", {"fail_times": []})
    data["fail_times"].append(now)
    delay = min(len(data["fail_times"]), 5)
    time.sleep(delay)


def rate_limit_register_ok() -> bool:
    """Max 3 próby rejestracji na 15 min (po sesji)."""
    now = time.time()
    data = st.session_state.setdefault("_register_rl", [])
    data[:] = [t for t in data if now - t < 900]
    return len(data) < 3


def register_register_attempt():
    """Zapisuje próbę rejestracji (wywołać przy submit)."""
    st.session_state.setdefault("_register_rl", []).append(time.time())


def rate_limit_message_ok(username: str) -> bool:
    """Max 30 wiadomości na 5 min na użytkownika."""
    if not username:
        return True
    now = time.time()
    key = "_message_rl"
    if key not in st.session_state:
        st.session_state[key] = {}
    data = st.session_state[key].setdefault(username, [])
    data[:] = [t for t in data if now - t < 300]
    return len(data) < 30


def register_message_sent(username: str):
    """Zapisuje wysłanie wiadomości (wywołać po udanym INSERT)."""
    if not username:
        return
    st.session_state.setdefault("_message_rl", {}).setdefault(username, []).append(time.time())


def require_admin():
    uname = st.session_state.get("username")
    if not uname:
        st.stop()
    conn = db_conn()
    if not conn:
        st.stop()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT is_admin FROM users WHERE username=%s", (uname,))
            row = cur.fetchone()
        if not row or not row[0]:
            _error_box(t("no_permissions"))
            st.stop()
    finally:
        db_release(conn)

def ensure_admin_totp() -> bool:
    """
    Drugi etap logowania do panelu admina – kod z Google / Microsoft Authenticator.
    Działa tylko dla administratora (bo require_admin() już to sprawdził).
    Pokazuje też kod QR do skonfigurowania aplikacji.
    """
    # jeśli już zweryfikowany w tej sesji – nie męczymy drugi raz
    if st.session_state.get("admin_totp_ok"):
        return True

    if not ADMIN_TOTP_SECRET:
        _error_box(t("admin_missing_config"))
        return False

    try:
        totp = pyotp.TOTP(ADMIN_TOTP_SECRET)
    except Exception as e:
        logger.error("TOTP init error: %s", e)
        _error_box("Błąd konfiguracji TOTP (Google Authenticator).")
        return False

    # --- QR CODE do skonfigurowania aplikacji 2FA ---
    try:
        username = st.session_state.get("username", "admin")
        issuer = "FindFriendsWithHobbies"
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)

        # generujemy obraz QR w pamięci
        qr_img = qrcode.make(uri)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)

        _info_box(
            "1️⃣ Zeskanuj ten kod QR w aplikacji Google/Microsoft Authenticator.\n\n"
            "2️⃣ Po dodaniu konta przepisz poniżej aktualny 6-cyfrowy kod."
        )
        st.image(buf.getvalue(), caption="Zeskanuj w aplikacji uwierzytelniającej")
    except Exception as e:
        logger.error("QR code generate error: %s", e)
        _warning_box(t("admin_totp_qr_failed"))

    # --- Formularz wprowadzenia kodu ---
    _warning_box(t("admin_totp_warning"))

    with st.form("admin_totp_form"):
        code = st.text_input(t("admin_totp_code_label"), type="password", max_chars=6)
        submit = st.form_submit_button(t("admin_totp_confirm"), type="primary")

    if submit:
        code = (code or "").strip()
        if not code:
            _error_box(t("admin_totp_type_code"))
            return False

        try:
            if totp.verify(code, valid_window=1):
                st.session_state["admin_totp_ok"] = True
                _success_box(t("admin_totp_success"))
                st.rerun()
            else:
                _error_box(t("admin_totp_invalid"))
        except Exception as e:
            logger.error("TOTP verify error: %s", e)
            _error_box(t("admin_totp_verify_error"))
        return False

    # jeszcze nic nie zatwierdzono
    return False


        
def update_last_activity():
    """
    Aktualizuje znacznik ostatniej aktywności zalogowanego użytkownika,
    ale nie częściej niż raz na minutę (Streamlit lubi rerunować).
    """
    username = st.session_state.get("username")
    if not username:
        return

    now = time.time()
    last = st.session_state.get("_last_activity_update", 0.0)
    if now - last < 60:
        return

    conn = db_conn()
    if not conn:
        return
    # SQLite nie ma NOW() – używamy datetime('now')
    now_expr = "datetime('now')" if config.USE_SQLITE else "NOW()"
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE users SET last_activity = {now_expr} WHERE username=%s",
                (username,),
            )
        st.session_state["_last_activity_update"] = now
    except Exception as e:
        logger.error("update_last_activity error: %s", e)
    finally:
        db_release(conn)


def is_blocked_between(user_a: str, user_b: str) -> bool:
    """
    True jeśli którykolwiek z użytkowników zablokował drugiego.
    """
    if not user_a or not user_b:
        return False

    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT 1
                FROM blocks
                WHERE (blocker = %s AND blocked = %s)
                   OR (blocker = %s AND blocked = %s)
                LIMIT 1
                """,
                (user_a, user_b, user_b, user_a),
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.error("is_blocked_between error: %s", e)
        return False
    finally:
        db_release(conn)


def block_user(blocker: str, blocked: str) -> bool:
    if not blocker or not blocked or blocker == blocked:
        return False

    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO blocks (blocker, blocked)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (blocker, blocked),
            )
        return True
    except Exception as e:
        logger.error("block_user error: %s", e)
        return False
    finally:
        db_release(conn)


def unblock_user(blocker: str, blocked: str) -> bool:
    if not blocker or not blocked:
        return False

    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM blocks WHERE blocker = %s AND blocked = %s",
                (blocker, blocked),
            )
        return True
    except Exception as e:
        logger.error("unblock_user error: %s", e)
        return False
    finally:
        db_release(conn)


def get_blocked_users(blocker: str) -> list[str]:
    if not blocker:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT blocked FROM blocks WHERE blocker = %s ORDER BY blocked",
                (blocker,),
            )
            return [r[0] for r in cur.fetchall()]
    except Exception as e:
        logger.error("get_blocked_users error: %s", e)
        return []
    finally:
        db_release(conn)


def create_report(
    reporter: str,
    reported_user: str | None = None,
    reported_club: int | None = None,
    reported_message_id: int | None = None,
    reported_message_type: str | None = None,
    reason: str = "",
) -> bool:
    """
    Dodaje wpis do tabeli reports.
    """
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO reports
                    (reporter, reported_user, reported_club,
                     reported_message_id, reported_message_type, reason)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    reporter,
                    reported_user,
                    reported_club,
                    reported_message_id,
                    reported_message_type,
                    reason.strip() or "(no reason)",
                ),
            )
        return True
    except Exception as e:
        logger.error("create_report error: %s", e)
        return False
    finally:
        db_release(conn)


def update_report_status(report_id: int, status: str) -> bool:
    """Ustawia status zgłoszenia (open / closed)."""
    if status not in ("open", "closed"):
        return False
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE reports SET status = %s WHERE id = %s", (status, report_id))
        return True
    except Exception as e:
        logger.error("update_report_status error: %s", e)
        return False
    finally:
        db_release(conn)


def set_club_hidden(club_id: int, hidden: bool) -> bool:
    """Ukrywa lub pokazuje klub (dla admina po zgłoszeniu)."""
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE clubs SET is_hidden = %s WHERE id = %s", (1 if hidden else 0, club_id))
        return True
    except Exception as e:
        logger.error("set_club_hidden error: %s", e)
        return False
    finally:
        db_release(conn)


# =========================
# Geokodowanie i pogoda (moduł geo_weather)
# =========================
def resolve_city_coordinates(city: str):
    """Alias dla geo_weather.resolve_city_coordinates."""
    return geo_weather.resolve_city_coordinates(city)


def get_weather(city: str) -> str | None:
    """Pogoda dla miasta; język z sesji."""
    lang = st.session_state.get("language", "pl")
    return geo_weather.get_weather(city, lang)


# =========================
# Uploads (moduł uploads) – wrapper z komunikatami
# =========================
def save_upload(file, club_id: int):
    """Zapis pliku; przy błędzie wyświetla st.error i zwraca (None, None)."""
    path, media_type = uploads.save_upload(file, club_id)
    if path is None and file:
        if file.type not in uploads.ALLOWED_TYPES:
            _error_box(t("file_type_not_allowed"))
        elif file.size > uploads.MAX_FILE_SIZE:
            _error_box(t("file_too_large"))
    return path, media_type


# =========================
# E-mail (moduł email_service)
# =========================
def send_email(to_addr: str, subject: str, body: str) -> bool:
    return email_service.send_email(to_addr, subject, body)


def apply_customizations():
    username = st.session_state.get("username")
    if not username:
        return
    conn = db_conn()
    if not conn: return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT background_color, font_size, font_family, theme FROM user_customizations WHERE username=%s", (username,))
            row = cur.fetchone()
        if row:
            bg_color, font_size, font_family, theme = row
            font_px = {"small":"12","medium":"16","large":"20"}.get(font_size, "16")
            st.markdown(f"""
                <style>
                    .reportview-container {{
                        background-color: {bg_color};
                        font-size: {font_px}px;
                        font-family: {font_family};
                    }}
                </style>
            """, unsafe_allow_html=True)
    finally:
        db_release(conn)


def set_user_customizations():
    lang = st.session_state.get("language", "pl")
    st.header("👤 " + t("profile"))

    username = st.session_state["username"]

    # ===== O MNIE / ABOUT ME =====
    current_description = ""
    conn = db_conn()
    if conn:
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT description FROM users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    current_description = row[0]
        except Exception as e:
            logger.error("load user description error: %s", e)
        finally:
            db_release(conn)

    st.subheader("📝 " + t("profile_about"))

    with st.form(f"profile_about_form_{username}"):
        about_text = st.text_area(
            t("profile_about"),
            value=current_description,
            height=120,
        )
        submitted_about = st.form_submit_button(t("save"), type="primary")

    if submitted_about:
        new_desc = (about_text or "").strip()
        if len(new_desc) > 600:
            _warning_box(t("profile_about_too_long"))
        else:
            conn = db_conn()
            if conn:
                try:
                    with conn:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE users SET description = %s WHERE username = %s",
                            (new_desc, username),
                        )
                    _success_box(t("profile_about_saved"))
                    st.rerun()
                except Exception as e:
                    logger.error("save user description error: %s", e)
                    _error_box(t("profile_about_error"))
                finally:
                    db_release(conn)

    st.markdown("---")

    # ===== AVATAR / ZDJĘCIE PROFILOWE =====
    st.subheader("📸 " + t("profile_avatar"))

    no_avatar_msg = t("profile_no_avatar")
    cannot_load_avatar_msg = t("profile_avatar_cannot_load")
    upload_label = t("profile_avatar_upload_label")
    avatar_saved_msg = t("profile_avatar_saved")
    avatar_error_msg = t("profile_avatar_error")

    conn = db_conn()
    current_avatar = None
    if conn:
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT profile_picture FROM users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    current_avatar = row[0]
        except Exception as e:
            logger.error("load avatar error: %s", e)
        finally:
            db_release(conn)

    cols = st.columns([1, 2])

    with cols[0]:
        if current_avatar:
            try:
                st.image(current_avatar, width=150)
            except Exception:
                st.write(cannot_load_avatar_msg)
        else:
            _info_box(no_avatar_msg)

    with cols[1]:
        uploaded_avatar = st.file_uploader(
            upload_label,
            type=["jpg", "jpeg", "png"],
            key="avatar_uploader",
        )

        if uploaded_avatar:
            avatar_path = save_avatar(uploaded_avatar, username)

            if avatar_path:
                conn = db_conn()
                if conn:
                    try:
                        with conn:
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE users SET profile_picture = %s WHERE username = %s",
                                (avatar_path, username),
                            )
                        _success_box(avatar_saved_msg)
                        st.rerun()
                    except Exception as e:
                        logger.error("save avatar db error: %s", e)
                        _error_box(avatar_error_msg)
                    finally:
                        db_release(conn)

    st.markdown("---")

    # ===== HOBBY =====
    st.subheader("🎯 " + t("hobbies_header"))

    hobbies = get_user_hobbies(username)
    if hobbies:
        for hobby in hobbies:
            st.markdown(f"• {hobby}")
    else:
        _info_box(t("hobby_empty"))

    st.markdown("### ➕ " + t("hobbies_add_header"))

    # 1) Ręczne wpisanie hobby
    new_hobby_input = st.text_input(
        t("hobbies_new_label"),
        key=f"profile_new_hobby_{username}_profile",
    ).strip()

    # 2) Proponowane hobby zależne od języka
    lang = st.session_state.get("language", "pl")
    suggested_hobbies = DEFAULT_HOBBIES.get(lang, DEFAULT_HOBBIES["pl"])

    suggested = st.selectbox(
        t("hobbies_suggestions_label"),
        [""] + suggested_hobbies,
        index=0,
        key=f"profile_hobby_suggestion_{username}",
    )

    if st.button(
        t("hobby_save_button"),
        key=f"profile_save_hobby_btn_{username}_profile",
        type="primary",
    ):
        # jeśli użytkownik coś wpisał, to to ma pierwszeństwo,
        # inaczej bierzemy wybraną propozycję z listy
        final_hobby = new_hobby_input or suggested

        if not final_hobby:
            _warning_box(t("hobby_required"))
        else:
            success = add_user_hobby(username, final_hobby)
            if success:
                _success_box(t("hobby_added"))
                st.rerun()
            else:
                _error_box(t("hobby_add_error"))

    st.markdown("---")

    # ===== KLUBY =====
    st.subheader("🏡 " + t("profile_clubs_header"))

    clubs = get_user_clubs(username)

    if clubs:
        for name, city in clubs:
            st.markdown(f"🏷️ **{name}** — {city}")
    else:
        _info_box(t("profile_no_clubs"))

    st.markdown("---")

    # ===== STWÓRZ KLUB =====
    create_club()

    st.markdown("---")

    # ===== ZMIANA HASŁA =====
    st.subheader("🔐 " + t("profile_change_pw_header"))

    with st.form(f"profile_change_password_form_{username}"):

        old_pw = st.text_input(
            t("profile_old_pw_label"),
            type="password",
            key=f"profile_old_pw_{username}",
        )
        new_pw = st.text_input(
            t("profile_new_pw_label"),
            type="password",
            key=f"profile_new_pw_{username}",
        )
        new_pw2 = st.text_input(
            t("profile_new_pw2_label"),
            type="password",
            key=f"profile_new_pw2_{username}",
        )

        submitted = st.form_submit_button(t("profile_change_pw_btn"), type="primary")

    if submitted:
        if not old_pw or not new_pw or not new_pw2:
            _warning_box(t("profile_fill_all_fields"))
        elif new_pw != new_pw2:
            _error_box(t("profile_pw_not_same"))
        else:
            ok, msg = change_user_password(username, old_pw, new_pw)
            # msg jest jeszcze po PL, ale to już temat na osobną refaktoryzację
            if ok:
                _success_box(msg)
            else:
                _error_box(msg)

    st.markdown("---")

    # ===== ODZNAKI / ACHIEVEMENTS =====
    st.subheader("🎖️ " + t("profile_achievements_header"))
    st.caption(t("profile_achievements_caption"))

    achievements = get_user_achievements(username)
    ACHIEVEMENT_EMOJI = {
        "first_club": "🏅",
        "three_clubs": "🎯",
        "five_clubs": "🌟",
        "first_event_created": "📅",
    }

    if not achievements:
        _info_box(t("profile_no_achievements"))
    else:
        n_cols = max(2, min(len(achievements), 4))
        cols = st.columns(n_cols)
        for i, (code, title, description, unlocked_at) in enumerate(achievements):
            with cols[i % n_cols]:
                emoji = ACHIEVEMENT_EMOJI.get(code, "🏆")
                with st.container(border=True):
                    st.markdown(f"**{emoji} {title}**")
                    if description:
                        st.caption(description)
                    if isinstance(unlocked_at, datetime):
                        date_str = unlocked_at.strftime("%Y-%m-%d")
                        st.caption(t("profile_achievement_unlocked_at", date=date_str))

    st.markdown("---")


    # ===== ZAPROŚ ZNAJOMYCH / INVITE FRIENDS =====
    st.subheader("📣 " + t("invite_header"))
    st.write(t("invite_text"))
    invite_link = f"{APP_PUBLIC_URL}?ref={username}"
    st.code(invite_link, language="text")
    st.caption(t("invite_copy_hint"))

    referrals_count = get_referral_stats(username)
    if referrals_count == 0:
        st.caption(t("invite_no_referrals"))
    elif referrals_count == 1:
        st.caption(t("invite_one_referral"))
    else:
        st.caption(t("invite_many_referrals", count=referrals_count))

    # ===== PUBLICZNY PROFIL / PUBLIC PROFILE =====
    public_profile_header = (
        "### 🌍 Twój publiczny profil"
        if lang == "pl"
        else "### 🌍 Your public profile"
    )
    public_profile_text = (
        "Ten link prowadzi do Twojego publicznego profilu. "
        "Możesz go wkleić na Messengerze, WhatsAppie, w mailu itd.:"
        if lang == "pl"
        else "This link leads to your public profile. "
             "You can share it on Messenger, WhatsApp, email, etc.:"
    )
    public_profile_caption = (
        "Kto wejdzie w ten link i założy konto, będzie miał już przypisanego Ciebie "
        "jako osobę polecającą. 💌"
        if lang == "pl"
        else "Anyone who opens this link and creates an account will have you set "
             "as the referrer. 💌"
    )

    st.markdown(public_profile_header)

    public_profile_url = f"{APP_PUBLIC_URL}?user={username}&ref={username}"

    st.write(public_profile_text)
    st.code(public_profile_url, language="text")
    st.caption(public_profile_caption)


def user_needs_onboarding(username: str) -> bool:
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM hobbies WHERE username=%s LIMIT 1",
                (username,)
            )
            row = cur.fetchone()
            return row is None
    finally:
        db_release(conn)


def onboarding_view():
    st.markdown("## " + t("onboarding_title"))
    st.caption(t("onboarding_subtitle"))

    username = st.session_state["username"]

    conn = db_conn()
    if not conn:
        st.stop()

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT city FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        current_city = row[0] if row else ""

    db_release(conn)

    lang = st.session_state.get("language", "pl")

    # domyślne hobby zależne od języka
    if lang == "pl":
        hobby_options = [
            "Bieganie", "Planszówki", "Programowanie", "Fotografia",
            "Podróże", "Gotowanie", "Fitness", "Muzyka", "Inne"
        ]
    else:
        hobby_options = [
            "Running", "Board games", "Programming", "Photography",
            "Travel", "Cooking", "Fitness", "Music", "Other"
        ]

    with st.form("onboarding_form"):
        city = st.text_input(
            t("city"),
            value=current_city,
            key="onboarding_city",
        )

        lang = st.session_state.get("language", "pl")

        hobbies = st.multiselect(
            t("onboarding_hobbies_label"),
            DEFAULT_HOBBIES.get(lang, DEFAULT_HOBBIES["pl"])
        )

        submit = st.form_submit_button(t("onboarding_submit"), type="primary")

    if submit:
        if not city or len(hobbies) < 3:
            _warning_box(t("onboarding_warning"))
            return

        conn = db_conn()
        if not conn:
            return

        try:
            with conn:
                cur = conn.cursor()

                cur.execute(
                    "UPDATE users SET city=%s WHERE username=%s",
                    (city, username)
                )

                cur.execute("DELETE FROM hobbies WHERE username=%s", (username,))
                for h in hobbies:
                    cur.execute(
                        "INSERT INTO hobbies (username, hobby) VALUES (%s,%s)",
                        (username, h)
                    )

            _success_box(t("onboarding_success"))
            st.session_state["onboarding_done"] = True
            st.rerun()

        except Exception as e:
            logger.error("Onboarding error: %s", e)
            _error_box(t("db_error"))
        finally:
            db_release(conn)


def add_activity(activity_type: str,
                 actor: str,
                 city: str | None = None,
                 club_id: int | None = None,
                 payload: str | None = None):
    """
    Zapisuje pojedynczą aktywność do feedu.
    activity_type: 'club_created', 'event_created', 'joined_club' itd.
    payload: np. nazwa klubu / wydarzenia.
    """
    if not actor:
        return

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO feed_activities (activity_type, actor, city, club_id, payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (activity_type, actor, city, club_id, payload),
            )
    except Exception as e:
        logger.error("add_activity error: %s", e)
    finally:
        db_release(conn)

def create_email_verification_token(username: str) -> str | None:
    token = str(uuid.uuid4())

    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()

            cur.execute(
                "UPDATE email_verifications SET used = TRUE WHERE username = %s",
                (username,),
            )

            cur.execute(
                """
                INSERT INTO email_verifications (username, token)
                VALUES (%s, %s)
                """,
                (username, token),
            )

        return token
    except Exception as e:
        logger.error("email verification token error: %s", e)
        return None
    finally:
        db_release(conn)


def get_feed_for_user(username: str, limit: int = 30):
    """
    Zwraca listę aktywności:
    - z miasta użytkownika
    - ORAZ z klubów, do których należy (hybryda)
    """
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                WITH user_info AS (
                    SELECT city FROM users WHERE username = %s
                ),
                user_clubs AS (
                    SELECT club_id FROM members WHERE username = %s
                )
                SELECT
                    a.activity_type,
                    a.actor,
                    a.city,
                    a.club_id,
                    a.payload,
                    a.created_at,
                    c.name AS club_name
                FROM feed_activities a
                LEFT JOIN clubs c ON c.id = a.club_id,
                     user_info ui
                WHERE
                    (ui.city IS NOT NULL AND a.city ILIKE ui.city)
                    OR a.club_id IN (SELECT club_id FROM user_clubs)
                ORDER BY a.created_at DESC
                LIMIT %s
                """,
                (username, username, limit),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error("get_feed_for_user error: %s", e)
        return []
    finally:
        db_release(conn)


def format_activity_row(activity_type: str,
                        actor: str,
                        city: str | None,
                        club_name: str | None,
                        payload: str | None) -> str:
    """
    Zwraca gotowy tekst do wyświetlenia w feedzie.
    """
    club_label = club_name or payload or ""
    city_label = f" ({city})" if city else ""

    if activity_type == "club_created":
        # np. Roman założył nowy klub Gwiazdy (Frombork).
        return f"**{actor}** założył nowy klub **{club_label}**{city_label}."
    elif activity_type == "event_created":
        # np. Roman dodał wydarzenie Nocne obserwacje w klubie Gwiazdy (Frombork).
        return f"**{actor}** dodał wydarzenie **{payload}** w klubie **{club_label}**{city_label}."
    elif activity_type == "joined_club":
        # np. Roman dołączył do klubu Gwiazdy (Frombork).
        return f"**{actor}** dołączył do klubu **{club_label}**{city_label}."
    else:
        return f"**{actor}**: {payload or ''}"

def get_user_language(username: str) -> str:
    """
    Zwraca język użytkownika zapisany w tabeli users.language,
    albo 'en' jeśli nie udało się odczytać.
    """
    conn = db_conn()
    if not conn:
        return "en"

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT language FROM users WHERE username=%s",
                (username,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0]
            return "en"
    except Exception as e:
        logger.error("get_user_language error: %s", e)
        return "en"
    finally:
        db_release(conn)


def _save_user_language(username: str, lang: str) -> None:
    """Zapisuje wybrany język użytkownika w bazie (ciągłość między sesjami)."""
    if not username or not lang:
        return
    conn = db_conn()
    if not conn:
        return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET language = %s WHERE username = %s",
                (lang, username),
            )
    except Exception as e:
        logger.error("_save_user_language error: %s", e)
    finally:
        db_release(conn)

def get_user_city(username: str) -> str | None:
    """
    Zwraca miasto użytkownika albo None.
    """
    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT city FROM users WHERE username=%s", (username,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        db_release(conn)

def create_notification_for_user(username: str, template_key: str, **kwargs):
    """
    Tworzy powiadomienie dla konkretnego usera na podstawie klucza z translations.
    """
    # wybieramy język odbiorcy
    lang = get_user_language(username)

    # bierzemy szablon bezpośrednio z translations, z pominięciem st.session_state['language']
    entry = translations.get(template_key, {})
    text = entry.get(lang) or entry.get("en") or template_key

    try:
        message = text.format(**kwargs) if kwargs else text
    except Exception:
        message = text  # jak coś pójdzie nie tak z formatowaniem

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notifications (username, message) VALUES (%s, %s)",
                (username, message),
            )
    except Exception as e:
        logger.error("create_notification_for_user error: %s", e)
    finally:
        db_release(conn)

def get_unread_notifications_count(username: str) -> int:
    """
    Zwraca liczbę nieprzeczytanych powiadomień.
    """
    conn = db_conn()
    if not conn:
        return 0

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE username=%s AND read = 0",
                (username,),
            )
            row = cur.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error("get_unread_notifications_count error: %s", e)
        return 0
    finally:
        db_release(conn)


def get_user_hobbies(username: str):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT hobby FROM hobbies WHERE username=%s",
                (username,)
            )
            rows = cur.fetchall()
            return [r[0] for r in rows]
    finally:
        db_release(conn)

def get_suggested_clubs_for_user(username: str, limit: int = 5) -> list[str]:
    """
    Zwraca listę nazw proponowanych klubów na bazie hobby użytkownika
    + domyślnej listy.

    Zasada:
    - w polskim UI: możemy użyć hobby użytkownika (+ domyślna lista PL)
    - w angielskim UI: tylko domyślne propozycje EN (bez miksu języków)
    """
    ui_lang = st.session_state.get("language") or "en"
    user_lang = get_user_language(username)
    lang = ui_lang or user_lang or "en"

    user_hobbies = set(get_user_hobbies(username))
    suggestions: list[str] = []

    # 1️⃣ Na podstawie hobby – tylko w polskim UI i gdy język konta = UI
    if lang == user_lang and lang == "pl" and user_hobbies:
        for hobby in user_hobbies:
            hobby_clean = (hobby or "").strip().title()
            if not hobby_clean:
                continue
            suggestions.append(f"Klub {hobby_clean}")

    # 2️⃣ Domyślne propozycje wg języka UI
    for club in DEFAULT_CLUB_SUGGESTIONS.get(lang, []):
        club_name = club.strip()
        if club_name and club_name not in suggestions:
            suggestions.append(club_name)

    return suggestions[:limit]


def get_suggested_club_names_for_user(username: str, limit: int = 5) -> list[str]:
    """
    Wrapper dla starej nazwy funkcji – używany w dashboard_view.
    """
    return get_suggested_clubs_for_user(username, limit)


def get_user_clubs(username: str):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.name, c.city
                FROM members m
                JOIN clubs c ON m.club_id = c.id
                WHERE m.username = %s
            """, (username,))
            return cur.fetchall()
    finally:
        db_release(conn)

def get_referral_stats(username: str) -> int:
    """
    Zwraca liczbę użytkowników, którzy zarejestrowali się z referrerem = username.
    """
    conn = db_conn()
    if not conn:
        return 0

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE referrer = %s",
                (username,),
            )
            row = cur.fetchone()
            return row[0] if row else 0
    except Exception as e:
        logger.error("get_referral_stats error: %s", e)
        return 0
    finally:
        db_release(conn)


def get_user_referrer(username: str) -> Optional[str]:
    """Zwraca nazwę użytkownika, który zaprosił danego użytkownika (referrer), lub None."""
    if not username:
        return None
    conn = db_conn()
    if not conn:
        return None
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT referrer FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            return (row[0] if row and row[0] else None)
    except Exception as e:
        logger.error("get_user_referrer error: %s", e)
        return None
    finally:
        db_release(conn)


def get_upcoming_events_in_city(city: str, limit: int = 10):
    """
    Nadchodzące wydarzenia w klubach z danego miasta
    (albo takich, które w location mają nazwę miasta).
    """
    city = (city or "").strip()
    if not city:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    e.event_name,
                    e.event_date,
                    e.location,
                    c.name AS club_name
                FROM club_events e
                JOIN clubs c ON e.club_id = c.id
                WHERE (c.city ILIKE %s OR e.location ILIKE %s)
                  AND (COALESCE(c.is_hidden, 0) = 0)
                ORDER BY e.event_date ASC
                LIMIT %s
            """, (f"%{city}%", f"%{city}%", limit))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_new_clubs_in_city(city: str, limit: int = 5):
    """
    Najnowsze kluby w mieście (po id).
    """
    city = (city or "").strip()
    if not city:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, description
                FROM clubs
                WHERE city ILIKE %s AND (COALESCE(is_hidden, 0) = 0)
                ORDER BY id DESC
                LIMIT %s
            """, (f"%{city}%", limit))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_recommended_clubs_for_user(username: str, city: str, limit: int = 5):
    """
    Kluby w tym samym mieście, do których user jeszcze nie należy.
    """
    city = (city or "").strip()
    if not city:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    c.id,
                    c.name,
                    c.description
                FROM clubs c
                LEFT JOIN members m
                    ON m.club_id = c.id AND m.username = %s
                WHERE c.city ILIKE %s
                  AND m.username IS NULL
                  AND (COALESCE(c.is_hidden, 0) = 0)
                ORDER BY c.id DESC
                LIMIT %s
            """, (username, f"%{city}%", limit))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_clubs_for_you(username: str, city: str, limit: int = 5):
    """
    Kluby w mieście użytkownika dopasowane do jego hobby (nazwa lub opis klubu),
    do których jeszcze nie należy.
    """
    city = (city or "").strip()
    hobbies = get_user_hobbies(username)
    if not city or not hobbies:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            # Warunek: (c.name ILIKE %h% OR c.description ILIKE %h%) dla któregoś hobby
            hobby_conds = " OR ".join(
                ["(c.name LIKE %s OR c.description LIKE %s)"] * len(hobbies)
            )
            params = [username, f"%{city}%"]
            for h in hobbies:
                params.append(f"%{h}%")
                params.append(f"%{h}%")
            params.append(limit)
            cur.execute(
                """
                SELECT c.id, c.name, c.description
                FROM clubs c
                LEFT JOIN members m ON m.club_id = c.id AND m.username = %s
                WHERE m.username IS NULL
                  AND c.city LIKE %s
                  AND ("""
                + hobby_conds
                + """)
                ORDER BY c.id DESC
                LIMIT %s
                """,
                tuple(params),
            )
            return cur.fetchall()
    finally:
        db_release(conn)


def get_events_for_you(username: str, city: str, limit: int = 5):
    """
    Nadchodzące wydarzenia w klubach z miasta użytkownika,
    których nazwa lub opis pasuje do hobby użytkownika.
    """
    city = (city or "").strip()
    hobbies = get_user_hobbies(username)
    if not city or not hobbies:
        return []

    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            hobby_conds = " OR ".join(
                ["(c.name LIKE %s OR c.description LIKE %s)"] * len(hobbies)
            )
            params = [f"%{city}%", f"%{city}%"]
            for h in hobbies:
                params.append(f"%{h}%")
                params.append(f"%{h}%")
            params.append(limit)
            cur.execute(
                """
                SELECT e.event_name, e.event_date, e.location, c.name AS club_name
                FROM club_events e
                JOIN clubs c ON e.club_id = c.id
                WHERE (c.city LIKE %s OR e.location LIKE %s)
                  AND ("""
                + hobby_conds
                + """)
                ORDER BY e.event_date ASC
                LIMIT %s
                """,
                tuple(params),
            )
            return cur.fetchall()
    finally:
        db_release(conn)


def dashboard_view():
    """
    Główny widok 'Co się dzieje w moim mieście' – wersja kompaktowa, dobra też na telefon.
    """
    username = st.session_state.get("username")
    if not username:
        st.stop()

    # Jednorazowy komunikat „Zostałeś zaproszony przez X” po pierwszym wejściu
    if not st.session_state.get("referrer_thankyou_shown"):
        referrer = get_user_referrer(username)
        if referrer:
            _success_box(t("referral_thankyou", ref=referrer))
            st.session_state["referrer_thankyou_shown"] = True

    city = get_user_city(username) or "?"
        # 👋 Powitanie użytkownika
    st.markdown(f"### 👋 {t('dashboard_greeting', username=username)}")
    st.caption(t("dashboard_greeting_sub"))


    # Tytuł + opis
    title_text = t("dashboard_title", city=city)
    st.markdown(f"## 🏙️ {title_text}")
    st.caption(t("dashboard_caption"))

    # 🎯 DLA CIEBIE – kluby i wydarzenia po hobby + miasto
    user_hobbies = get_user_hobbies(username)
    for_you_clubs = get_clubs_for_you(username, city, limit=5)
    for_you_events = get_events_for_you(username, city, limit=5)
    with st.expander(f"🎯 **{t('for_you_header')}** — {t('for_you_subtitle')}", expanded=True):
        if not user_hobbies:
            _info_box(t("for_you_no_hobbies"))
        else:
            col_fc, col_fe = st.columns(2)
            with col_fc:
                st.markdown(f"**{t('for_you_clubs')}**")
                if not for_you_clubs:
                    st.caption(t("for_you_no_clubs"))
                else:
                    for club_id, name, desc in for_you_clubs:
                        with st.container(border=True):
                            st.markdown(f"**{name}**")
                            if desc:
                                short = (desc or "")[:100] + ("…" if len(desc or "") > 100 else "")
                                st.caption(short)
                            if st.button(
                                t("dashboard_join_btn"),
                                key=f"for_you_join_{club_id}",
                                type="primary",
                            ):
                                join_club(club_id)
                                st.rerun()
            with col_fe:
                st.markdown(f"**{t('for_you_events')}**")
                if not for_you_events:
                    st.caption(t("for_you_no_events"))
                else:
                    for event_name, event_date, location, club_name in for_you_events:
                        with st.container(border=True):
                            st.markdown(f"**{event_name}**")
                            st.caption(f"{event_date} • {club_name} • {location}")

    # 📢 FEED AKTYWNOŚCI – hybryda miasto + Twoje kluby
    feed_rows = get_feed_for_user(username, limit=20)

    feed_header = "📰 " + t("dashboard_feed_header")
    no_feed_msg = t("dashboard_no_feed")

    with st.expander(feed_header, expanded=True):
        if not feed_rows:
            st.markdown(empty_state_html("feed", no_feed_msg), unsafe_allow_html=True)
        else:
            for (
                activity_type,
                actor,
                city_row,
                club_id,
                payload,
                created_at,
                club_name,
            ) in feed_rows:
                text = format_activity_row(
                    activity_type=activity_type,
                    actor=actor,
                    city=city_row,
                    club_name=club_name,
                    payload=payload,
                )
                with st.container(border=True):
                    st.markdown(text)
                    if isinstance(created_at, datetime):
                        st.caption(created_at.strftime("%Y-%m-%d %H:%M"))
                    else:
                        st.caption(str(created_at))

    # TOP 5, żeby nie zalać użytkownika
    events = get_upcoming_events_in_city(city, limit=5)
    new_clubs = get_new_clubs_in_city(city, limit=5)
    user_clubs = get_user_clubs(username)
    recommended = get_recommended_clubs_for_user(username, city, limit=5)

    # 💡 propozycje nazw klubów na podstawie hobby użytkownika
    suggested_club_names = get_suggested_club_names_for_user(username, limit=5)

    col1, col2 = st.columns(2)

    # LEWA – wydarzenia + nowe kluby
    with col1:
        events_header = "📅 " + t("dashboard_events_header")
        no_events_msg = t("dashboard_no_events")
        all_events_btn = t("dashboard_all_events_btn")

        new_clubs_header = "🆕 " + t("dashboard_new_clubs_header")
        no_new_clubs_msg = t("dashboard_no_new_clubs")
        show_all_clubs_btn = t("dashboard_show_all_clubs_btn")

        with st.expander(events_header, expanded=True):
            if not events:
                st.markdown(empty_state_html("calendar", no_events_msg), unsafe_allow_html=True)
            else:
                for event_name, event_date, location, club_name in events:
                    with st.container(border=True):
                        st.markdown(f"**{event_name}**")
                        st.caption(f"{event_date} • {club_name} • {location}")

            if st.button(all_events_btn, key="dash_all_events", type="secondary"):
                st.session_state["menu_override"] = "events_menu"
                st.rerun()

        with st.expander(new_clubs_header, expanded=True):
            if not new_clubs:
                st.markdown(empty_state_html("club", no_new_clubs_msg), unsafe_allow_html=True)
            else:
                for club_id, name, desc in new_clubs:
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        if desc:
                            short = desc[:140] + ("…" if len(desc) > 140 else "")
                            st.caption(short)

            if st.button(show_all_clubs_btn, key="dash_all_clubs", type="secondary"):
                st.session_state["menu_override"] = "club_list"
                st.rerun()

    # PRAWA – Twoje kluby + rekomendacje / tworzenie klubu
    with col2:
        your_clubs_header = "🏡 " + t("dashboard_your_clubs_header")
        no_clubs_msg = t("dashboard_no_clubs")
        recommended_header = "✨ " + t("dashboard_recommended_header")
        no_recommended_msg = t("dashboard_no_recommended")
        join_btn_label = t("dashboard_join_btn")
        join_success_msg = t("dashboard_join_success")

        with st.expander(your_clubs_header, expanded=True):
            if not user_clubs:
                st.markdown(empty_state_html("home", no_clubs_msg), unsafe_allow_html=True)
            else:
                for name, club_city in user_clubs:
                    st.write(f"• {name} ({club_city})")

        with st.expander(recommended_header, expanded=True):
            # 1️⃣ Najpierw „prawdziwe” rekomendowane kluby z bazy
            if recommended:
                for club_id, name, desc in recommended:
                    with st.container(border=True):
                        st.markdown(f"**{name}**")
                        if desc:
                            short = desc[:140] + ("…" if len(desc) > 140 else "")
                            st.caption(short)
                        if st.button(
                            join_btn_label,
                            key=f"dash_join_{club_id}",
                            type="primary",
                        ):
                            join_club(club_id)
                            maybe_grant_membership_achievements(username)
                            _success_box(join_success_msg)
                            st.rerun()

            # 2️⃣ Jeśli nie ma rekomendacji z bazy, a są hobby – pokaż pomysły + link do tworzenia klubu w Profilu
            elif suggested_club_names:
                st.caption("✨ " + t("dashboard_suggested_caption"))
                for name in suggested_club_names:
                    with st.container(border=True):
                        st.markdown(f"💡 **{name}**")

                st.caption(t("dashboard_create_club_in_profile"))
                if st.button("👤 " + t("profile") + " → " + t("create_club"), key="dash_go_create_club", type="secondary"):
                    st.session_state["menu_override"] = "profile"
                    st.rerun()

            else:
                _info_box(no_recommended_msg)


def add_user_hobby(username: str, hobby: str):
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO hobbies (username, hobby) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (username, hobby),
            )
        return True
    except Exception as e:
        logger.error("Add hobby error: %s", e)
        return False
    finally:
        db_release(conn)


def grant_achievement(username: str,
                      code: str,
                      title: str,
                      description: str = ""):
    """
    Nadaje odznakę użytkownikowi, jeśli jeszcze jej nie ma.
    """
    if not username:
        return

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO user_achievements (username, code, title, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username, code) DO NOTHING
                """,
                (username, code, title, description),
            )
            if cur.rowcount > 0:
                logger.info("Achievement '%s' granted to %s", code, username)
    except Exception as e:
        logger.error("grant_achievement error: %s", e)
    finally:
        db_release(conn)

def get_user_achievements(username: str):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT code, title, description, unlocked_at
                FROM user_achievements
                WHERE username = %s
                ORDER BY unlocked_at ASC
                """,
                (username,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error("get_user_achievements error: %s", e)
        return []
    finally:
        db_release(conn)

def save_avatar(uploaded_file, username: str) -> str:
    """
    Zapisuje avatar użytkownika jako JPG/PNG w media/avatars
    i zwraca ścieżkę do zapisu w DB.
    """
    if not uploaded_file:
        return ""

    ext = uploaded_file.name.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png"]:
        return ""

    # bezpieczna unikalna nazwa
    filename = f"{username}_{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join("media", "avatars", filename)

    try:
        image = Image.open(uploaded_file)
        image = image.convert("RGB")
        image.thumbnail((512, 512))
        image.save(save_path, format="JPEG", quality=85)
        return save_path
    except Exception as e:
        logger.error("save_avatar error: %s", e)
        return ""
    

def maybe_grant_membership_achievements(username: str):
    """
    Sprawdza, do ilu klubów należy użytkownik
    i ewentualnie przyznaje odznaki za 1, 3, 5 klubów.
    """
    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM members WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            total = row[0] if row else 0

        # 📌 Tu definiujemy progi odznak
        if total == 1:
            grant_achievement(
                username,
                code="first_club",
                title="Pierwszy klub",
                description="Dołączyłeś do swojego pierwszego klubu 🎉",
            )
        elif total == 3:
            grant_achievement(
                username,
                code="three_clubs",
                title="Trzy kluby",
                description="Należysz już do 3 klubów – to się nazywa aktywność!",
            )
        elif total == 5:
            grant_achievement(
                username,
                code="five_clubs",
                title="Pięć klubów",
                description="5 klubów? To już mała sieć społecznościowa 😎",
            )

    except Exception as e:
        logger.error("maybe_grant_membership_achievements error: %s", e)
    finally:
        db_release(conn)


def maybe_grant_event_achievements(username: str):
    """
    Przyznaje odznakę za zorganizowanie pierwszego wydarzenia (wywoływane po utworzeniu wydarzenia).
    """
    if not username:
        return
    grant_achievement(
        username,
        code="first_event_created",
        title="Organizator",
        description="Zorganizowałeś pierwsze wydarzenie 🎉",
    )


def get_clubs_for_cards(city=None, hobby=None, sort="newest"):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()

            query = """
                SELECT 
                    c.id,
                    c.name,
                    c.city,
                    c.description,
                    COUNT(m.username) AS members_count
                FROM clubs c
                LEFT JOIN members m ON c.id = m.club_id
                WHERE (COALESCE(c.is_hidden, 0) = 0)
            """
            params = []

            if city:
                query += " AND c.city ILIKE %s"
                params.append(f"%{city}%")

            query += " GROUP BY c.id"

            # nie mamy created_at, więc używamy id jako "najnowsze"
            if sort == "popular":
                query += " ORDER BY members_count DESC, c.id DESC"
            else:
                query += " ORDER BY c.id DESC"

            cur.execute(query, tuple(params))
            return cur.fetchall()

    finally:
        db_release(conn)

def get_club_details(club_id: int):
    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    c.id,
                    c.name,
                    c.city,
                    c.description,
                    COUNT(m.username) AS members_count,
                    c.latitude,
                    c.longitude
                FROM clubs c
                LEFT JOIN members m ON c.id = m.club_id
                WHERE c.id = %s
                GROUP BY c.id, c.name, c.city, c.description, c.latitude, c.longitude
            """, (club_id,))
            return cur.fetchone()
    finally:
        db_release(conn)


# ---------- Kluby partnerskie ----------
def get_partner_clubs(club_id: int):
    """Lista klubów będących partnerami (status=accepted). Zwraca listę (partner_club_id, partner_name)."""
    conn = db_conn()
    if not conn:
        return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.name FROM clubs c
                INNER JOIN club_partnerships p ON (
                    (p.club_id = %s AND p.partner_club_id = c.id) OR
                    (p.partner_club_id = %s AND p.club_id = c.id)
                )
                WHERE p.status = 'accepted' AND (COALESCE(c.is_hidden, 0) = 0)
            """, (club_id, club_id))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_partnership_invites_received(club_id: int):
    """Zaproszenia do partnerstwa skierowane DO tego klubu (do zaakceptowania). Zwraca (partnership_id, from_club_id, from_club_name)."""
    conn = db_conn()
    if not conn:
        return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.club_id, c.name
                FROM club_partnerships p
                JOIN clubs c ON c.id = p.club_id
                WHERE p.partner_club_id = %s AND p.status = 'pending'
            """, (club_id,))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_clubs_for_partnership_invite(from_club_id: int):
    """Kluby, do których można wysłać zaproszenie (nie self, nie już partnerzy, nie już pending). Zwraca (id, name)."""
    conn = db_conn()
    if not conn:
        return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name FROM clubs
                WHERE id != %s
                AND (COALESCE(is_hidden, 0) = 0)
                AND id NOT IN (
                    SELECT partner_club_id FROM club_partnerships WHERE club_id = %s
                    UNION
                    SELECT club_id FROM club_partnerships WHERE partner_club_id = %s
                )
                ORDER BY name
            """, (from_club_id, from_club_id, from_club_id))
            return cur.fetchall()
    finally:
        db_release(conn)


def invite_partnership(from_club_id: int, to_club_id: int) -> bool:
    if from_club_id == to_club_id:
        return False
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO club_partnerships (club_id, partner_club_id, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT(club_id, partner_club_id) DO UPDATE SET status = 'pending'
            """, (from_club_id, to_club_id))
        return True
    except Exception as e:
        logger.error("invite_partnership: %s", e)
        return False
    finally:
        db_release(conn)


def accept_partnership(partnership_id: int, accepting_club_id: int) -> bool:
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE club_partnerships
                SET status = 'accepted'
                WHERE id = %s AND partner_club_id = %s AND status = 'pending'
            """, (partnership_id, accepting_club_id))
        return True
    except Exception as e:
        logger.error("accept_partnership: %s", e)
        return False
    finally:
        db_release(conn)


def decline_partnership(partnership_id: int, declining_club_id: int) -> bool:
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE club_partnerships
                SET status = 'declined'
                WHERE id = %s AND partner_club_id = %s AND status = 'pending'
            """, (partnership_id, declining_club_id))
        return True
    except Exception as e:
        logger.error("decline_partnership: %s", e)
        return False
    finally:
        db_release(conn)


def get_accepted_partnerships_with_coords():
    """Dla mapy: pary (lat1, lon1, lat2, lon2) dla każdej zaakceptowanej partnerstwa (oba kluby z współrzędnymi)."""
    conn = db_conn()
    if not conn:
        return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    a.latitude, a.longitude,
                    b.latitude, b.longitude
                FROM club_partnerships p
                JOIN clubs a ON a.id = p.club_id
                JOIN clubs b ON b.id = p.partner_club_id
                WHERE p.status = 'accepted'
                  AND a.latitude IS NOT NULL AND a.longitude IS NOT NULL
                  AND b.latitude IS NOT NULL AND b.longitude IS NOT NULL
            """)
            return cur.fetchall()
    finally:
        db_release(conn)


def _arc_points(lat1: float, lon1: float, lat2: float, lon2: float, num_points: int = 25):
    """Punkty łuku parabolicznego między (lat1,lon1) a (lat2,lon2) – do rysowania na mapie."""
    import math
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2
    d = math.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) or 0.001
    k = min(0.3, 0.15 * d)
    ctrl_lat = mid_lat + k * (-(lon2 - lon1))
    ctrl_lon = mid_lon + k * (lat2 - lat1)
    points = []
    for i in range(num_points + 1):
        t = i / num_points
        # Kwadratowa krzywa Béziera: (1-t)²*A + 2(1-t)t*C + t²*B
        lat = (1 - t) ** 2 * lat1 + 2 * (1 - t) * t * ctrl_lat + t ** 2 * lat2
        lon = (1 - t) ** 2 * lon1 + 2 * (1 - t) * t * ctrl_lon + t ** 2 * lon2
        points.append((lat, lon))
    return points


def get_events_for_club(club_id: int):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT event_name, event_date, location
                FROM club_events
                WHERE club_id = %s
                ORDER BY event_date ASC
            """, (club_id,))
            return cur.fetchall()
    finally:
        db_release(conn)


def get_reviews_for_club(club_id: int):
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT username, rating, comment
                FROM club_reviews
                WHERE club_id = %s
                ORDER BY id DESC
            """, (club_id,))
            return cur.fetchall()
    finally:
        db_release(conn)

def add_club_review(club_id: int, username: str, rating: int, comment: str):
    # 🔎 prosty filtr treści dla komentarzy
    if comment and not is_content_allowed(comment):
        _warning_box(t("content_not_allowed"))
        return False
    
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO club_reviews (club_id, username, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (club_id, username, rating, comment))
        return True
    except Exception as e:
        logger.error("Add review error: %s", e)
        return False
    finally:
        db_release(conn)


def get_events_for_club(club_id: int):
    """Zwraca listę wydarzeń danego klubu."""
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, event_name, event_date, location, description
                FROM club_events
                WHERE club_id = %s
                ORDER BY event_date ASC
                """,
                (club_id,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error("Get events for club error: %s", e)
        return []
    finally:
        db_release(conn)

def add_event_for_club(
    club_id: int,
    event_name: str,
    event_date,
    location: str,
    description: str,
):
    """Dodaje nowe wydarzenie do klubu."""
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return False
        # 🔎 filtr treści dla nazwy / opisu wydarzenia
    if (event_name and not is_content_allowed(event_name)) or (
        description and not is_content_allowed(description)
    ):
        _warning_box(t("content_not_allowed"))
        return False

    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO club_events (club_id, event_name, event_date, location, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (club_id, event_name, event_date, location, description),
            )
        _success_box(t("event_added"))
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO club_events (club_id, event_name, event_date, location, description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (club_id, event_name, event_date, location, description),
            )

        maybe_grant_event_achievements(username)
        # ✨ log do feedu
        add_activity(
            activity_type="event_created",
            actor=username,
            city=None,  # i tak złapiemy to przez przynależność do klubu
            club_id=club_id,
            payload=event_name,
        )

                # 🔔 powiadomienia dla członków klubu
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT username FROM members WHERE club_id = %s",
                    (club_id,),
                )
                recipients = [r[0] for r in cur.fetchall()]

            for u in recipients:
                if u != username:
                    create_notification_for_user(
                        username=u,
                        template_key="notification_new_event",
                        event_name=event_name,
                    )
        except Exception as e:
            logger.error("event notifications error: %s", e)

        _success_box(t("event_added"))
        return True

    except Exception as e:
        logger.error("Add event for club error: %s", e)
        _error_box(t("db_error"))
        return False
    finally:
        db_release(conn)

def get_events_for_club(club_id: int):
    """Zwraca listę wydarzeń danego klubu."""
    conn = db_conn()
    if not conn:
        return []

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    id,
                    event_name,
                    event_date,
                    event_time,
                    location,
                    description
                FROM club_events
                WHERE club_id = %s
                ORDER BY event_date ASC, COALESCE(event_time, '00:00') ASC
                """,
                (club_id,),
            )
            return cur.fetchall()
    except Exception as e:
        logger.error("Get events for club error: %s", e)
        return []
    finally:
        db_release(conn)


def add_event_for_club(
    club_id: int,
    event_name: str,
    event_date,
    event_time,
    location: str,
    description: str,
):
    """Dodaje nowe wydarzenie do klubu."""
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return False

    # 🔎 filtr treści dla nazwy / opisu wydarzenia
    if (event_name and not is_content_allowed(event_name)) or (
        description and not is_content_allowed(description)
    ):
        _warning_box(t("content_not_allowed"))
        return False

    # zamieniamy datę i godzinę na ładne stringi
    try:
        event_date_str = (
            event_date.isoformat() if hasattr(event_date, "isoformat") else str(event_date)
        )
    except Exception:
        event_date_str = str(event_date)

    if event_time:
        try:
            event_time_str = (
                event_time.strftime("%H:%M")
                if hasattr(event_time, "strftime")
                else str(event_time)
            )
        except Exception:
            event_time_str = str(event_time)
    else:
        event_time_str = None

    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO club_events
                    (club_id, event_name, event_date, event_time, location, description)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    club_id,
                    event_name.strip(),
                    event_date_str,
                    event_time_str,
                    location.strip(),
                    description.strip(),
                ),
            )
            maybe_grant_event_achievements(username)
        return True
    except Exception as e:
        logger.error("Add event for club error: %s", e)
        _error_box(t("db_error"))
        return False
    finally:
        db_release(conn)


def join_club_direct(username: str, club_id: int):
    """Prosty helper używany w innych miejscach – bez Streamlit UI."""
    add_member_to_club(username, club_id, role="member")


def is_user_member(username: str, club_id: int) -> bool:
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM members WHERE username=%s AND club_id=%s LIMIT 1",
                (username, club_id),
            )
            return cur.fetchone() is not None
    finally:
        db_release(conn)

# === CLUB ROLES & PRIVACY ===================================

def get_club_privacy(club_id: int) -> str:
    """Zwraca privacy_level dla klubu ('public', 'private_request', 'secret')."""
    conn = db_conn()
    if not conn:
        return "public"
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT privacy_level FROM clubs WHERE id=%s", (club_id,))
            row = cur.fetchone()
            return row[0] if row and row[0] else "public"
    finally:
        db_release(conn)


def get_club_owner(club_id: int) -> Optional[str]:
    conn = db_conn()
    if not conn:
        return None
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT owner_username FROM clubs WHERE id=%s", (club_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        db_release(conn)


def user_exists(needle_username: str) -> bool:
    """Czy użytkownik o danej nazwie istnieje w bazie."""
    if not needle_username or not needle_username.strip():
        return False
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username = %s", (needle_username.strip(),))
            return cur.fetchone() is not None
    finally:
        db_release(conn)


def get_club_deputy(club_id: int) -> Optional[str]:
    """Zwraca nazwę użytkownika zastępcy zarządcy klubu (lub None)."""
    conn = db_conn()
    if not conn:
        return None
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT deputy_username FROM clubs WHERE id=%s", (club_id,))
            row = cur.fetchone()
            return row[0] if row and row[0] else None
    finally:
        db_release(conn)


def is_club_deputy(username: str, club_id: int) -> bool:
    return get_club_deputy(club_id) == username


def can_manage_club(username: str, club_id: int) -> bool:
    """Czy użytkownik może zarządzać klubem: owner, zastępca lub administrator aplikacji."""
    if not username:
        return False
    if st.session_state.get("is_admin"):
        return True
    if get_club_owner(club_id) == username or get_club_deputy(club_id) == username:
        return True
    return get_member_role(username, club_id) in ("owner", "moderator")


def get_member_role(username: str, club_id: int) -> Optional[str]:
    conn = db_conn()
    if not conn:
        return None
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT role FROM members WHERE username=%s AND club_id=%s",
                (username, club_id),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        db_release(conn)


def is_club_owner(username: str, club_id: int) -> bool:
    return get_member_role(username, club_id) == "owner"


def is_club_moderator_or_owner(username: str, club_id: int) -> bool:
    return get_member_role(username, club_id) in ("owner", "moderator")


def update_club_deputy(club_id: int, deputy_username: Optional[str]) -> bool:
    """Ustawia lub czyści zastępcę zarządcy klubu. Zwraca True przy sukcesie."""
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE clubs SET deputy_username = %s WHERE id = %s",
                (deputy_username if deputy_username else None, club_id),
            )
        return True
    except Exception as e:
        logger.error("update_club_deputy error: %s", e)
        return False
    finally:
        db_release(conn)


def update_club_owner(club_id: int, owner_username: Optional[str]) -> bool:
    """Ustawia zarządcę klubu (dla admina). Zwraca True przy sukcesie."""
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE clubs SET owner_username = %s WHERE id = %s",
                (owner_username if owner_username else None, club_id),
            )
            # zaktualizuj rolę w members
            cur.execute("UPDATE members SET role = 'member' WHERE club_id = %s", (club_id,))
            if owner_username:
                cur.execute(
                    """
                    INSERT INTO members (username, club_id, role)
                    VALUES (%s, %s, 'owner')
                    ON CONFLICT (username, club_id) DO UPDATE SET role = 'owner'
                    """,
                    (owner_username, club_id),
                )
        return True
    except Exception as e:
        logger.error("update_club_owner error: %s", e)
        return False
    finally:
        db_release(conn)


def add_member_to_club(username: str, club_id: int, role: str = "member") -> bool:
    """Dodaje użytkownika do klubu z daną rolą."""
    conn = db_conn()
    if not conn:
        return False
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO members (username, club_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (username, club_id) DO UPDATE SET role = EXCLUDED.role
                """,
                (username, club_id, role),
            )
            # uaktualnij licznik członków
            cur.execute(
                "UPDATE clubs SET members_count = (SELECT COUNT(*) FROM members WHERE club_id=%s) WHERE id=%s",
                (club_id, club_id),
            )
        return True
    except Exception as e:
        logger.error("add_member_to_club error: %s", e)
        return False
    finally:
        db_release(conn)

# === CLUB JOIN REQUESTS =====================================

def create_join_request(username: str, club_id: int) -> str:
    """
    Tworzy prośbę o dołączenie.
    Zwraca klucz tłumaczenia z komunikatem.
    """
    conn = db_conn()
    if not conn:
        return "db_error"

    try:
        with conn:
            cur = conn.cursor()

            # już członek?
            cur.execute(
                "SELECT 1 FROM members WHERE username=%s AND club_id=%s",
                (username, club_id),
            )
            if cur.fetchone():
                return "already_member"

            # istniejąca prośba?
            cur.execute(
                """
                SELECT status FROM club_join_requests
                WHERE username=%s AND club_id=%s
                """,
                (username, club_id),
            )
            row = cur.fetchone()
            if row and row[0] == "pending":
                return "club_join_request_exists"

            # zapis prośby (jeśli była odrzucona – nadpisujemy)
            cur.execute(
                """
                INSERT INTO club_join_requests (username, club_id, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (club_id, username) DO UPDATE SET status='pending', created_at = NOW()
                """,
                (username, club_id),
            )

        return "club_join_request_sent"
    except Exception as e:
        logger.error("create_join_request error: %s", e)
        return "db_error"
    finally:
        db_release(conn)


def get_pending_join_requests(club_id: int) -> List[Tuple[int, str, datetime]]:
    conn = db_conn()
    if not conn:
        return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, username, created_at
                FROM club_join_requests
                WHERE club_id=%s AND status='pending'
                ORDER BY created_at ASC
                """,
                (club_id,),
            )
            return cur.fetchall()
    finally:
        db_release(conn)


def approve_join_request(request_id: int, approver: str) -> bool:
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            # pobierz szczegóły
            cur.execute(
                "SELECT username, club_id FROM club_join_requests WHERE id=%s AND status='pending'",
                (request_id,),
            )
            row = cur.fetchone()
            if not row:
                return False

            username, club_id = row

            # dodaj do członków
            add_member_to_club(username, club_id, role="member")

            # oznacz jako zatwierdzoną
            cur.execute(
                "UPDATE club_join_requests SET status='approved' WHERE id=%s",
                (request_id,),
            )

            cur.execute("SELECT name FROM clubs WHERE id = %s", (club_id,))
            row_name = cur.fetchone()
            club_name = row_name[0] if row_name else ""
            if club_name:
                create_notification_for_user(username, "notification_join_approved", club_name=club_name)
        return True
    except Exception as e:
        logger.error("approve_join_request error: %s", e)
        return False
    finally:
        db_release(conn)


def reject_join_request(request_id: int, approver: str) -> bool:
    conn = db_conn()
    if not conn:
        return False

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE club_join_requests SET status='rejected' WHERE id=%s AND status='pending'",
                (request_id,),
            )
        return True
    except Exception as e:
        logger.error("reject_join_request error: %s", e)
        return False
    finally:
        db_release(conn)


def leave_club(club_id: int):
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM members WHERE username=%s AND club_id=%s",
                (username, club_id)
            )
        _success_box(t("club_left"))
    except Exception as e:
        logger.error("Leave club error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)

def reset_city_coordinates(city: str):
    city = (city or "").strip()
    if not city:
        return

    # 1) czyść cache miasta
    conn_cache = get_connection()
    if conn_cache:
        try:
            cur = conn_cache.cursor()
            cur.execute("DELETE FROM city_locations WHERE city = %s", (city,))
            conn_cache.commit()
        finally:
            cur.close()
            conn_cache.close()

    # 2) zeruj współrzędne klubów
    conn = db_conn()
    if not conn:
        return
    try:
        with conn:
            cur2 = conn.cursor()
            cur2.execute(
                "UPDATE clubs SET latitude=NULL, longitude=NULL WHERE city=%s",
                (city,),
            )
    finally:
        db_release(conn)


# =========================
# Strona tytułowa / Intro (przed wejściem do apki, bez bocznego menu)
# =========================
def _intro_background_data_uri():
    """Jeśli jest plik tła w assets/intro_background.png lub .jpg, zwraca data URI (base64)."""
    import base64
    assets_dir = pathlib.Path(__file__).parent / "assets"
    for name in ("intro_background.png", "intro_background.jpg", "intro_background.jpeg"):
        bg_path = assets_dir / name
        if not bg_path.exists():
            continue
        try:
            data = bg_path.read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            ext = "png" if name.endswith(".png") else "jpeg"
            return f"data:image/{ext};base64,{b64}"
        except Exception as e:
            logger.warning("Intro background image read failed: %s", e)
            continue
    return None


def show_intro_screen():
    """Ekran powitalny na tle obrazka – układ pod czytelność (ciemny overlay, jasny tekst)."""
    bg_uri = _intro_background_data_uri()
    bg_css = (
        f"background-image: url('{bg_uri}'); background-size: cover; background-position: center;"
        if bg_uri
        else "background: linear-gradient(180deg, #1e3a5f 0%, #0f1729 50%, #0a0e1a 100%);"
    )

    st.markdown(
        f"""
        <style>
        section[data-testid="stSidebar"] {{ display: none !important; }}
        /* Tło na całym widoku aplikacji – obrazek lub gradient */
        [data-testid="stAppViewContainer"] > section {{ background: transparent !important; }}
        [data-testid="stAppViewContainer"] {{
            {bg_css}
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
            min-height: 100vh !important;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, transparent 18%, transparent 50%, rgba(0,0,0,0.6) 80%, rgba(0,0,0,0.92) 100%);
            pointer-events: none;
            z-index: 0;
        }}
        .main .block-container {{ background: transparent !important; padding-top: 1rem !important; max-width: 100% !important; position: relative; z-index: 1; }}
        .main {{ background: transparent !important; }}
        /* Treść na ciemnym tle + animacja wejścia */
        .intro-content {{
            text-align: center;
            padding: 1.5rem 1rem 2rem;
            max-width: 560px;
            margin: 0 auto 1.5rem;
            background: rgba(0,0,0,0.45);
            border-radius: 16px;
            backdrop-filter: blur(6px);
            border: 1px solid rgba(13,148,136,0.4);
            box-shadow: 0 0 24px rgba(13,148,136,0.15);
            animation: introFadeIn 0.6s ease-out;
        }}
        @keyframes introFadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .intro-content h1 {{
            font-size: clamp(1.6rem, 4.5vw, 2.2rem);
            margin-bottom: 0.6rem;
            font-weight: 700;
            color: #fff !important;
        }}
        .intro-content .tagline {{
            font-size: 1.05rem;
            color: #d1d5db;
            margin-bottom: 1.25rem;
            line-height: 1.5;
        }}
        .intro-benefits {{
            text-align: left;
            max-width: 380px;
            margin: 0 auto;
            font-size: 0.95rem;
            line-height: 1.9;
            color: #e5e7eb;
        }}
        .intro-benefits li {{ margin: 0.35rem 0; }}
        .intro-sub {{ font-size: 0.85rem; color: #9ca3af; margin-top: 0.5rem; }}
        /* Przycisk Wchodzę – wyróżniony */
        .intro-cta-wrap {{ margin-top: 1rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Ustaw język (jak w language_selector), żeby t() działało
    forced = st.session_state.pop("_force_language", None)
    if forced:
        st.session_state["language"] = forced
    if "language" not in st.session_state:
        st.session_state["language"] = detect_language_from_ip()

    # Pasek górny: tylko zmiana języka (od pierwszego kliknięcia)
    with st.container():
        current_lang = st.session_state.get("language", "pl")
        languages = {"en": "English", "pl": "Polski"}
        lang_keys = list(languages.keys())
        default_index = lang_keys.index(current_lang) if current_lang in lang_keys else 0
        selected = st.selectbox(
            t("language_label"),
            options=lang_keys,
            format_func=languages.get,
            key="intro_lang_select",
            index=default_index,
        )
        if selected != current_lang:
            st.session_state["language"] = selected
            st.rerun()

    # Treść w „karcie” z półprzezroczystym tłem
    st.markdown(
        f"""
        <div class="intro-content">
            <h1>🌟 {t("intro_title")}</h1>
            <p class="tagline">{t("intro_tagline")}</p>
            <ul class="intro-benefits">
                <li>👥 {t("intro_benefit_1")}</li>
                <li>📅 {t("intro_benefit_2")}</li>
                <li>🗺️ {t("intro_benefit_3")}</li>
                <li>✨ {t("intro_benefit_4")}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button(f"🚀 **{t('intro_cta')}**", type="primary", use_container_width=True):
            st.session_state["intro_seen"] = True
            st.rerun()
    st.caption(t("intro_sub"))


# =========================
# Start (landing + logowanie) – bez sidebara, język i admin na stronie
# =========================
def _start_ensure_language():
    """Ustawia język na ekranie startu (bez sidebara)."""
    forced = st.session_state.pop("_force_language", None)
    if forced:
        st.session_state["language"] = forced
    if "language" not in st.session_state:
        st.session_state["language"] = detect_language_from_ip()


def show_start_screen():
    """
    Ekran startu po intro: bez bocznego menu, język i panel admina na stronie,
    czytelna nawigacja (Zaloguj / Zarejestruj / Zapomniałem hasła) + formularze.
    """
    # Ukryj sidebar; tło i karta – bardziej atrakcyjny, zwarty widok
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="stAppViewContainer"] > section { background: linear-gradient(165deg, #e0f2f1 0%, #f0fdfa 28%, #f8fafc 60%, #fff 100%) !important; min-height: 100vh !important; }
        .main .block-container { padding-top: 0.5rem !important; padding-bottom: 0.75rem !important; max-width: 720px !important; }
        .start-top-bar { margin: -0.5rem 0 0.75rem 0; }
        .start-title { text-align: center; margin-bottom: 0.25rem; font-size: 1.6rem !important; font-weight: 700 !important; color: #0f766e !important; text-shadow: 0 1px 2px rgba(15,118,110,0.15); }
        .start-subtitle { text-align: center; color: #475569; margin-bottom: 0.75rem; font-size: 0.95rem; line-height: 1.4; }
        .start-nav-btn { min-height: 44px !important; font-weight: 600 !important; }
        .start-card { padding: 1rem; border-radius: 14px; border: 1px solid rgba(13,148,136,0.2); background: rgba(255,255,255,0.85); box-shadow: 0 4px 20px rgba(13,148,136,0.08); margin: 0.5rem 0; }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="column"]) { gap: 0.5rem !important; }
        .stExpander { margin-top: 0.5rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _start_ensure_language()

    # ------ Pasek górny: tylko język (zmiana od pierwszego kliknięcia) ------
    current_lang = st.session_state.get("language", "pl")
    languages = {"en": "English", "pl": "Polski"}
    lang_keys = list(languages.keys())
    default_index = lang_keys.index(current_lang) if current_lang in lang_keys else 0
    selected = st.selectbox(
        t("language_label"),
        options=lang_keys,
        format_func=languages.get,
        key="start_screen_lang_select",
        index=default_index,
    )
    if selected != current_lang:
        st.session_state["language"] = selected
        st.rerun()

    # ------ Tytuł i podtytuł ------
    st.markdown(f'<p class="start-title"><strong>{t("landing_title")}</strong></p>', unsafe_allow_html=True)
    st.markdown(f'<p class="start-subtitle">{t("landing_subtitle")}</p>', unsafe_allow_html=True)

    # ------ Nawigacja: Zaloguj / Zarejestruj („Zapomniałem hasła” jest pod formularzem logowania) ------
    st.markdown(f"**{t('start_choose')}**")
    col_login, col_register = st.columns(2)
    with col_login:
        is_login = not st.session_state.get("show_register") and not st.session_state.get("reset_mode")
        if st.button(
            f"🔐 {t('login')}",
            type="primary" if is_login else "secondary",
            use_container_width=True,
            key="nav_login",
        ):
            st.session_state["show_register"] = False
            st.session_state["reset_mode"] = False
            st.rerun()
    with col_register:
        if st.button(
            f"📝 {t('register')}",
            type="primary" if st.session_state.get("show_register") else "secondary",
            use_container_width=True,
            key="nav_register",
        ):
            st.session_state["show_register"] = True
            st.session_state["reset_mode"] = False
            st.rerun()

    st.markdown("")  # minimalna przerwa

    # ------ Komunikat o zaproszeniu (gdy weszli z linku ?ref=...) ------
    ref_from_url = st.session_state.get("referrer_username")
    if ref_from_url:
        _info_box(t("referral_invite_banner", ref=ref_from_url))

    # ------ Formularz w zależności od trybu ------
    if st.session_state.get("post_register_add_hobbies") and st.session_state.get("post_register_username"):
        post_register_hobbies_step()
    elif st.session_state.get("reset_mode"):
        forgot_password_view()
        if st.button(f"← {t('back_to_login')}", key="back_from_forgot", type="secondary"):
            st.session_state["reset_mode"] = False
            st.rerun()
    elif st.session_state.get("show_register"):
        register_user()
        if st.button(f"🔐 {t('have_account_btn')}", key="back_from_register", type="secondary"):
            st.session_state["show_register"] = False
            st.rerun()
    else:
        login_user()
        if st.button(f"📝 {t('no_account_btn')}", key="go_register", type="secondary"):
            st.session_state["show_register"] = True
            st.rerun()

    # ------ Jedna zwinięta sekcja: Jak to działa + Dlaczego warto (mniej scrolla) ------
    with st.expander(f"ℹ️ {t('start_more_about')}", expanded=False):
        st.markdown(f"**{t('start_how_it_works')}** — {t('landing_extra_header')}")
        st.markdown(
            f"""
- {t("landing_extra_point_1")}
- {t("landing_extra_point_2")}
- {t("landing_extra_point_3")}
            """
        )
        st.markdown(f"**{t('start_why_join')}**")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.caption(f"👥 {t('landing_tile_1_title')}")
            st.caption(t("landing_tile_1_desc"))
        with b2:
            st.caption(f"📅 {t('landing_tile_2_title')}")
            st.caption(t("landing_tile_2_desc"))
        with b3:
            st.caption(f"🗺️ {t('landing_tile_3_title')}")
            st.caption(t("landing_tile_3_desc"))
        with b4:
            st.caption(f"⭐ {t('landing_tile_4_title')}")
            st.caption(t("landing_tile_4_desc"))


# =========================
# Auth screens (formularze – używane wewnątrz show_start_screen)
# =========================
def show_public_landing():
    """Legacy: prosta wersja landingu (używana tylko gdy coś wywoła bez startu)."""
    st.markdown(f"""
        <div style="text-align:center; padding: 60px 20px;">
            <h1>{t("landing_title")}</h1>
            <p style="font-size:18px; max-width:700px; margin:auto;">
                {t("landing_subtitle")}
            </p>
            <br><br>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"### 👥 {t('landing_tile_1_title')}")
        st.caption(t("landing_tile_1_desc"))
    with col2:
        st.markdown(f"### 📅 {t('landing_tile_2_title')}")
        st.caption(t("landing_tile_2_desc"))
    with col3:
        st.markdown(f"### 🗺️ {t('landing_tile_3_title')}")
        st.caption(t("landing_tile_3_desc"))
    with col4:
        st.markdown(f"### ⭐ {t('landing_tile_4_title')}")
        st.caption(t("landing_tile_4_desc"))

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"### {t('landing_extra_header')}")
    st.markdown(
        f"""
- {t("landing_extra_point_1")}
- {t("landing_extra_point_2")}
- {t("landing_extra_point_3")}
        """
    )
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(f"🚀 {t('landing_cta')}", type="primary"):
        st.session_state["show_register"] = True
        st.rerun()



def post_register_hobbies_step():
    """Krok po rejestracji: wybór 3 zainteresowań, potem przekierowanie do logowania."""
    username = st.session_state.get("post_register_username")
    if not username:
        st.session_state.pop("post_register_add_hobbies", None)
        st.session_state.pop("post_register_username", None)
        st.rerun()
        return

    st.subheader("🎯 " + t("onboarding_step_title"))
    st.caption(t("onboarding_step_subtitle"))
    lang = st.session_state.get("language", "pl")
    options = DEFAULT_HOBBIES.get(lang, DEFAULT_HOBBIES["pl"])

    with st.form("post_register_hobbies_form"):
        chosen = st.multiselect(t("onboarding_hobbies_label"), options, max_selections=10)
        submit = st.form_submit_button(t("onboarding_step_btn"), type="primary")

    if submit:
        if len(chosen) < 3:
            _warning_box(t("onboarding_step_min"))
            return
        conn = db_conn()
        if not conn:
            _error_box(t("db_error"))
            return
        try:
            with conn:
                cur = conn.cursor()
                for h in chosen:
                    cur.execute(
                        "INSERT INTO hobbies (username, hobby) VALUES (%s,%s)",
                        (username, h),
                    )
            st.session_state["post_register_add_hobbies"] = False
            st.session_state["post_register_username"] = None
            st.session_state["pre_filled_login"] = username
            _success_box(t("register_success"))
            _info_box(t("register_created_info"))
            st.rerun()
        except Exception as e:
            logger.error("Post-register hobbies error: %s", e)
            _error_box(t("db_error"))
        finally:
            db_release(conn)


def register_user():
    st.subheader("📝 " + t("register"))

    # Regulamin + Polityka w ekspanderach nad formularzem
    with st.expander(t("terms_title")):
        show_terms_of_service()

    with st.expander(t("privacy_title")):
        show_privacy_policy()

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input(t("username")).strip()
            city = st.text_input(t("city")).strip()
        with col2:
            email = st.text_input(t("email_label_reset")).strip()
            password = st.text_input(t("password"), type="password")

        accepted_tos = st.checkbox(t("accept_tos"), value=False)
        accepted_priv = st.checkbox(t("accept_privacy"), value=False)
        accepted_age = st.checkbox(t("accept_age"), value=False)

        submit = st.form_submit_button(t("register"), type="primary")

    if submit:
        # podstawowa walidacja
        if (
            not username
            or not password
            or not city
            or not email
            or not accepted_tos
            or not accepted_priv
            or not accepted_age
        ):
            _warning_box(t("all_fields_required"))
            return

        ok, err_msg = is_username_allowed(username)
        if not ok:
            _warning_box(t(err_msg))
            return

        ok, err_msg = validate_password(password)
        if not ok:
            _warning_box(err_msg)
            return

        # bardzo prosta walidacja e-maila (żeby złapać literówki typu 'roman@')
        if "@" not in email or "." not in email.split("@")[-1]:
            _warning_box(t("email_invalid"))
            return

        if not rate_limit_register_ok():
            _warning_box(t("rate_limit_register"))
            return

        # język wybrany w UI (domyślnie en/pl – jak masz ustawione)
        user_lang = st.session_state.get("language", "en")

        conn = db_conn()
        if not conn:
            return

        try:
            cur = conn.cursor()
            try:
                # kto polecił – z sesji, jeśli jest
                referrer = st.session_state.get("referrer_username")

                # nie pozwalamy być swoim własnym polecającym
                if referrer == username:
                    referrer = None

                # ⬇⬇⬇ NOWOŚĆ: zapisujemy language w bazie
                register_register_attempt()
                cur.execute(
                    """
                    INSERT INTO users (username, password, city, referrer, email, language)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (username, hash_password(password), city, referrer, email, user_lang),
                )
                conn.commit()

                # ⬇⬇⬇ WERYFIKACJĘ MAILA WYŁĄCZAMY NA RAZIE
                # token = create_email_verification_token(username)
                # verify_link = f"{APP_PUBLIC_URL}?verify_email={token}"
                # body = t(
                #     "email_verification_body",
                #     username=username,
                #     verify_link=verify_link,
                # )
                # send_email(email, t("email_verification_subject"), body)
                # _info_box(t("verify_email_info"))

                _success_box(t("register_success"))
                st.session_state["show_register"] = False
                # Krok onboarding: najpierw 3 hobby, potem logowanie
                st.session_state["post_register_add_hobbies"] = True
                st.session_state["post_register_username"] = username
                st.rerun()

            except (psycopg2.IntegrityError, sqlite3.IntegrityError):
                conn.rollback()
                _error_box(t("user_exists"))
            except Exception as e:
                conn.rollback()
                logger.error("Register error: %s", e)
                _error_box(t("db_error"))
        finally:
            db_release(conn)


def login_user():
    st.subheader("🔐 " + t("login"))
    st.markdown("---")

    # ✅ jeśli przyszliśmy tu świeżo po rejestracji – uzupełnij login
    prefill = st.session_state.pop("pre_filled_login", "")

    with st.form("login_form"):
        username = st.text_input(t("username"), value=prefill).strip()
        password = st.text_input(t("password"), type="password")
        submit = st.form_submit_button(t("login"), type="primary")

    # Zapomniałem hasła – pod przyciskiem „Zaloguj się”, logicznie przy formularzu logowania
    if st.button(f"🔑 {t('forgot_password_btn')}", key="login_forgot_btn", type="secondary"):
        st.session_state["reset_mode"] = True
        st.rerun()

    if not submit:
        return

    if not username or not password:
        _warning_box(t("all_fields_required"))
        return

    # (opcjonalnie można wyrzucić tę walidację, ale zostawiam jak było)
    ok, msg = validate_password(password)
    if not ok:
        _error_box(msg)
        logger.warning("Weak password attempt for user: %s", username)
        return

    conn = db_conn()
    if not conn:
        return

    try:
        cur = conn.cursor()

        # 1️⃣ Pobieramy hasło, rolę i język z bazy
        cur.execute(
            "SELECT password, is_admin, COALESCE(language, 'en') FROM users WHERE username = %s",
            (username,),
        )

        row = cur.fetchone()
        if not row:
            _error_box(t("login_invalid"))
            register_failed_login()
            time.sleep(0.5)
            return

        hashed_password, is_admin, lang = row

        # 2️⃣ Sprawdzamy hasło
        if not check_password(hashed_password, password):
            _error_box(t("login_invalid"))
            register_failed_login()
            time.sleep(0.5)
            return

        # 3️⃣ Sukces logowania
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.session_state["is_admin"] = bool(is_admin)

        # Ciągłość języka: zapisujemy aktualny wybór z sesji do bazy, żeby profil był zsynchronizowany.
        current_lang = st.session_state.get("language") or lang or "en"
        _save_user_language(username, current_lang)

        _success_box(t("login_success"))

        # ✅ reset licznika nieudanych logowań
        data = st.session_state.get("_login_rl")
        if isinstance(data, dict):
            data["fail_times"] = []

        # wymuszamy nowy przebieg, gdzie language_selector odczyta _force_language
        st.rerun()

    except Exception as e:
        logger.error("Login error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)



def forgot_password_view():
    st.subheader("🔑 " + t("reset_password_heading"))

    username = st.text_input(t("enter_username")).strip()

    if st.button(t("send_reset_link"), type="primary"):
        if not username:
            _warning_box(t("enter_username"))
            return

        conn = db_conn()
        if not conn:
            return

        try:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT email FROM users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()

            if not row or not row[0]:
                _error_box(t("username_not_found_or_no_email"))
                return

            email = row[0]
            token = create_password_reset_token(username)
            if not token:
                _error_box(t("password_reset_error"))
                return

            reset_link = f"{APP_PUBLIC_URL}?reset_token={token}"

            body = t(
                "password_reset_email_body",
                username=username,
                reset_link=reset_link,
            )

            if send_email(email, t("password_reset_email_subject"), body):
                _success_box(t("password_reset_email_sent"))
            else:
                _error_box(t("password_reset_email_failed"))

        except Exception as e:
            logger.error("forgot_password_view error: %s", e)
            _error_box(t("db_error"))


# =========================
# Clubs
# =========================
def create_club():
    username = st.session_state.get("username")
    if not username:
        # bezpieczeństwo – gdyby ktoś kiedyś przypadkiem zawołał create_club bez logowania
        _error_box(t("not_logged_in"))
        return

    st.subheader("➕ " + t("create_club"))

    # (opcjonalnie) możemy kiedyś pokazać tutaj suggested_names, na razie tylko logika
    suggested_names: list[str] = []
    try:
        suggested_names = get_suggested_clubs_for_user(username, limit=20)
    except Exception as e:
        logger.error("get_suggested_clubs_for_user in create_club error: %s", e)
        suggested_names = []

    with st.form("create_club_form"):
        club_name = st.text_input(t("club_name_label"))
        user_city = get_user_city(username)
        city = st.text_input(t("club_city_label"), value=user_city or "")
        description = st.text_area(t("club_description"), height=100)

        # === Privacy options ===
        privacy_choices = [
            ("public", t("club_privacy_public")),
            ("private_request", t("club_privacy_private_request")),
            ("secret", t("club_privacy_secret")),
        ]
        privacy_labels = [label for _, label in privacy_choices]

        selected_label = st.radio(
            t("club_privacy_label"),
            privacy_labels,
            index=0,
            key="create_club_privacy",
        )

        privacy_level = next(
            key for key, label in privacy_choices if label == selected_label
        )

        deputy_username_input = st.text_input(
            t("club_deputy_label"),
            placeholder="username",
            help=t("club_deputy_hint"),
            key="create_club_deputy",
        )

        submitted = st.form_submit_button(t("create_club_btn"), type="primary")

        if submitted:
            if not club_name or not city:
                _error_box(t("club_name_city_required"))
                return

            deputy_username = deputy_username_input.strip() if deputy_username_input else None
            if deputy_username:
                if deputy_username.lower() == username.lower():
                    _error_box(t("club_deputy_invalid"))
                    return
                if not user_exists(deputy_username):
                    _error_box(t("club_deputy_invalid"))
                    return

            conn = db_conn()
            if not conn:
                _error_box(t("db_error"))
                return

            try:
                with conn:
                    cur = conn.cursor()

                    lat, lon = resolve_city_coordinates(city)

                    cur.execute(
                        """
                        INSERT INTO clubs
                            (name, city, description, members_count, latitude, longitude, owner_username, deputy_username, privacy_level)
                        VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (club_name, city, description, lat, lon, username, deputy_username, privacy_level),
                    )
                    club_id = cur.fetchone()[0]

                    add_member_to_club(username, club_id, role="owner")

                _success_box(t("club_created", name=club_name))
            except Exception as e:
                logger.error("Create Club Error: %s", e)
                _error_box(t("db_error"))
            finally:
                db_release(conn)



def calculate_average_rating(club_id: int):
    conn = db_conn()
    if not conn: return None
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT AVG(rating) FROM reviews WHERE club_id=%s", (club_id,))
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else None
    finally:
        db_release(conn)

def join_club(club_id: int):
    """Obsługa dołączania z UI – respektuje prywatność klubu."""
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    privacy = get_club_privacy(club_id)

    # tajny – żadnych próśb, tylko zaproszenia
    if privacy == "secret":
        _info_box(t("club_is_secret"))
        return

    # publiczny – dołącz od razu
    if privacy == "public":
        ok = add_member_to_club(username, club_id, role="member")
        if ok:
            _success_box(t("club_joined"))
        else:
            _error_box(t("db_error"))
        return

    # prywatny – twórz prośbę
    if privacy == "private_request":
        msg_key = create_join_request(username, club_id)
        _info_box(t(msg_key))
        return

    # fallback (gdyby w bazie było coś dziwnego)
    ok = add_member_to_club(username, club_id, role="member")
    if ok:
        _success_box(t("club_joined"))
    else:
        _error_box(t("db_error"))


def get_club_reviews(club_id: int):
    conn = db_conn()
    if not conn: return []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT username, rating, review FROM reviews WHERE club_id=%s", (club_id,))
            rows = cur.fetchall()
            return [{"username": r[0], "rating": r[1], "review": r[2]} for r in rows]
    finally:
        db_release(conn)

def add_review(club_id: int, rating: int, review_text: str):
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return
    conn = db_conn()
    if not conn: return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO reviews (username, club_id, rating, review) VALUES (%s,%s,%s,%s)", (username, club_id, rating, review_text))
        _success_box(t("review_added"))
    except Exception as e:
        logger.error("Add review error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)

def club_forum(club_id: int):
    st.subheader("💬 " + t("club_forum"))
    conn = db_conn()
    if not conn:
        return
    try:
        current_user = st.session_state.get("username")

        # Pobierz wiadomości forum danego klubu
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, username, message, timestamp
                FROM forum_messages
                WHERE club_id = %s
                ORDER BY timestamp DESC
                """,
                (club_id,),
            )
            rows = cur.fetchall()

        # Wyświetl istniejące wiadomości
        for msg_id, author, message, ts in rows:
            with st.container():
                st.markdown(f"**{author}** • {ts}:")
                st.write(message)

                if current_user and current_user != author:
                    with st.expander(t("report_message_title"), expanded=False):
                        reason = st.text_area(
                            t("report_reason_placeholder"),
                            key=f"forum_report_reason_{msg_id}",
                        )
                        if st.button(
                            t("report_button"),
                            key=f"forum_report_btn_{msg_id}",
                            type="primary",
                        ):
                            ok = create_report(
                                reporter=current_user,
                                reported_user=author,
                                reported_club=club_id,
                                reported_message_id=msg_id,
                                reported_message_type="forum",
                                reason=reason,
                            )
                            if ok:
                                _success_box(t("report_sent"))
                            else:
                                _error_box(t("report_error"))

        # Formularz nowej wiadomości
        with st.form(f"new_msg_{club_id}"):
            new_message = st.text_area(t("write_new_message"))
            submitted = st.form_submit_button(t("send"), type="primary")

        if submitted:
            text = (new_message or "").strip()

            if not text:
                _warning_box(t("empty_message"))
                return

            # 🔎 prosty filtr treści
            if not is_content_allowed(text):
                _warning_box(t("content_not_allowed"))
                return

            if not current_user:
                _error_box(t("not_logged_in"))
                return

            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO forum_messages (club_id, username, message)
                    VALUES (%s, %s, %s)
                    """,
                    (club_id, current_user, text),
                )
            _success_box(t("message_sent"))
            st.rerun()
    finally:
        db_release(conn)


def view_clubs():
    lang = st.session_state.get("language", "pl")

    # NAGŁÓWEK
    st.header("🏘️ " + t("clubs_header"))

    # 🔙 powrót do „Co w mieście”
    if st.button("🏠 " + t("clubs_back_to_dashboard"), type="secondary"):
        st.session_state["menu_override"] = "dashboard_menu"
        st.session_state.pop("selected_club_id", None)
        st.rerun()

    username = st.session_state["username"]

    # Jeśli z innego miejsca ustawiono selected_club_id – pokaż szczegóły
    if "selected_club_id" in st.session_state:
        club_details_view(st.session_state["selected_club_id"])
        return

    # ===== FILTRY =====
    st.subheader("🔍 " + t("filters_header"))

    col1, col2 = st.columns(2)

    with col1:
        city_filter = st.text_input(t("city"))

    with col2:
        newest_label = t("sort_newest")
        popular_label = t("sort_popular")
        sort_option = st.selectbox(
            t("sort_by"),
            [newest_label, popular_label],
        )

    sort_value = "popular" if sort_option == popular_label else "newest"

    clubs = get_clubs_for_cards(
        city=city_filter if city_filter else None,
        sort=sort_value,
    )

    st.markdown("---")

    # ===== LISTA DO WYBORU (gdy wiele klubów) =====
    if not clubs:
        _info_box(t("no_clubs_for_filters"))
        return

    if len(clubs) > 5:
        quick_options = [
            (t("club_list_choose_placeholder"), None)
        ] + [(f"{name} ({city})", club_id) for club_id, name, city, desc, members_count in clubs]
        labels = [o[0] for o in quick_options]
        selected_label = st.selectbox(
            t("club_list_quick_select"),
            labels,
            key="club_list_quick_selectbox",
        )
        if selected_label and selected_label != quick_options[0][0]:
            idx = labels.index(selected_label)
            if idx > 0 and quick_options[idx][1] is not None:
                if st.button(t("club_list_go_to_club"), key="club_list_go_btn", type="primary"):
                    st.session_state["selected_club_id"] = quick_options[idx][1]
                    st.rerun()
        st.markdown("---")

    # helper do rysowania kart klubów (żeby nie kopiować kodu)
    def render_club_cards(club_rows):
        for club_id, name, city, desc, members_count in club_rows:

            is_member = is_user_member(username, club_id)

            status_member = "🟢 " + t("status_you_are_member")
            status_not_member = "⚪ " + t("status_not_member")
            status_badge = status_member if is_member else status_not_member

            action_leave = "❌ " + t("club_leave")
            action_join = "✅ " + t("club_join")
            action_label = action_leave if is_member else action_join

            people_word = t("people_count")
            manage_caption = t("manage_membership_hint")
            details_label = "🔍 " + t("details")

            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #2a2a2a;
                        border-radius:16px;
                        padding:20px;
                        margin-bottom:18px;
                        background:linear-gradient(145deg,#0f0f0f,#1a1a1a);
                        box-shadow:0 0 12px rgba(0,0,0,0.4);
                        color:#e8e8e8;
                    ">
                        <h3 style="margin-bottom:6px; color:#f5f5f5;">🏷️ {name}</h3>
                        <p style="opacity:0.95; color:#e0e0e0;">📍 {city} | 👥 {members_count} {people_word}</p>
                        <p style="margin-top:10px; color:#e0e0e0;">{(desc or '')[:120]}.</p>
                        <p style="margin-top:8px; color:#e0e0e0;"><b>Status:</b> {status_badge}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                colA, colB = st.columns([1, 3])

                with colA:
                    if st.button(
                        action_label,
                        key=f"club_action_{club_id}",
                        type="tertiary" if is_member else "primary",
                    ):
                        if is_member:
                            leave_club(club_id)
                        else:
                            join_club(club_id)
                        st.rerun()

                    if st.button(details_label, key=f"club_details_{club_id}", type="secondary"):
                        st.session_state["selected_club_id"] = club_id
                        st.rerun()

                with colB:
                    st.caption(manage_caption)

    # ===== TOP 10 + RESZTA =====
    total = len(clubs)
    top_10 = clubs[:10]
    other = clubs[10:]

    if total <= 10:
        # Mało klubów – pokazujemy po prostu wszystkie
        header_all = (
            "📋 Wszystkie kluby"
            if lang == "pl"
            else "📋 All clubs"
        )
        st.markdown(f"### {header_all}")
        render_club_cards(clubs)
    else:
        # TOP 10
        header_top = (
            "🏆 Top 10 klubów"
            if lang == "pl"
            else "🏆 Top 10 clubs"
        )
        st.markdown(f"### {header_top}")
        render_club_cards(top_10)

        # Pozostałe w expanderze
        header_other = (
            f"📂 Pozostałe kluby ({len(other)})"
            if lang == "pl"
            else f"📂 Other clubs ({len(other)})"
        )
        with st.expander(header_other, expanded=False):
            render_club_cards(other)



def club_details_view(club_id: int):
    username = st.session_state.get("username")
    if not username:
        st.stop()

    lang = st.session_state.get("language", "pl")

    club = get_club_details(club_id)
    if not club:
        msg = t("club_not_found")
        _error_box(msg)
        return

    club_id, name, city, description, members_count, club_lat, club_lon = club

    # ===== POGODA (współrzędne klubu lub geokodowanie miasta) =====
    try:
        if club_lat is not None and club_lon is not None:
            weather = get_weather_by_coords(club_lat, club_lon, lang)
        else:
            weather = get_weather(city)
    except Exception:
        weather = None

    st.markdown(f"## 🏷️ {name}")

    members_word = t("club_members")
    st.caption(f"📍 {city} • 👥 {members_count} {members_word}")

    is_member = is_user_member(username, club_id)

    colA, colB = st.columns([1, 3])

    # --- lewa kolumna: akcje ---
    with colA:
        leave_label = "❌ " + t("club_leave")
        join_label = "✅ " + t("club_join")

        if is_member:
            if st.button(leave_label, key=f"club_leave_{club_id}", type="tertiary"):
                leave_club(club_id)
                st.rerun()
        else:
            if st.button(join_label, key=f"club_join_{club_id}", type="primary"):
                join_club(club_id)
                st.rerun()

        if st.button("⬅ " + t("back_to_club_list"), type="secondary"):
            st.session_state.pop("selected_club_id", None)
            st.rerun()

    # --- prawa kolumna: pogoda + opis ---
    with colB:
        st.markdown("### 🌦️ " + t("weather"))
        if weather:
            st.write(weather)
        else:
            _info_box(t("no_weather"))

        st.markdown("### 📖 " + t("club_description"))
        if description:
            st.write(description)
        else:
            _info_box(t("no_description_yet"))

    st.markdown("---")

    # ===== KLUBY PARTNERSKIE =====
    partners = get_partner_clubs(club_id)
    st.markdown("### 🤝 " + t("partners_section_header"))
    if partners:
        for pid, pname in partners:
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"- **{t('partner_badge')}** {pname}")
            with c2:
                if st.button(t("partners_show_club"), key=f"goto_partner_{pid}", type="secondary"):
                    st.session_state["selected_club_id"] = pid
                    st.rerun()
    else:
        st.caption(t("partners_none"))

    # Dla zarządcy / zastępcy / admina: zaproszenia do zaakceptowania + wysyłanie zaproszeń
    if can_manage_club(username, club_id):
        invites = get_partnership_invites_received(club_id)
        if invites:
            st.markdown("#### " + t("partners_pending_invites"))
            for pid, from_id, from_name in invites:
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.write(f"• **{from_name}** " + t("partners_invited_you"))
                with c2:
                    if st.button(t("accept"), key=f"part_accept_{pid}", type="primary"):
                        if accept_partnership(pid, club_id):
                            _success_box(t("partners_accepted"))
                            st.rerun()
                with c3:
                    if st.button(t("reject"), key=f"part_decline_{pid}", type="tertiary"):
                        if decline_partnership(pid, club_id):
                            st.rerun()

        available = get_clubs_for_partnership_invite(club_id)
        if available:
            st.markdown("#### " + t("partners_invite_section"))
            opt_ids = [0] + [c[0] for c in available]
            id_to_name = {c[0]: c[1] for c in available}
            chosen_id = st.selectbox(
                t("partners_choose_club"),
                options=opt_ids,
                format_func=lambda x: "—" if x == 0 else id_to_name.get(x, str(x)),
                key=f"part_invite_select_{club_id}",
            )
            if chosen_id and st.button(t("partners_send_invite"), key=f"part_invite_btn_{club_id}", type="primary"):
                if invite_partnership(club_id, chosen_id):
                    _success_box(t("partners_invite_sent"))
                    st.rerun()
                else:
                    _error_box(t("db_error"))

    st.markdown("---")

    # ===== WYDARZENIA =====
    render_club_events_section(club_id, club_city=city)
        # ===== CZŁONKOWIE / MODERATORZY / PROŚBY =====
    st.markdown("---")
    st.markdown(f"### 👥 {t('club_members_section')}")

    if not can_manage_club(username, club_id):
        _info_box(t("no_permissions"))
        return

    # Ustawienia klubu (zastępca zarządcy)
    current_owner = get_club_owner(club_id)
    current_deputy = get_club_deputy(club_id)
    with st.expander(t("club_settings_expander")):
        st.caption(t("club_settings_deputy_caption"))
        st.write(t("club_owner_label") + ": **" + (current_owner or "—") + "**")
        st.write(t("club_deputy_display") + ": **" + (current_deputy or "—") + "**")
        with st.form("club_deputy_form"):
            new_deputy = st.text_input(t("club_deputy_label"), value=current_deputy or "", key="club_deputy_input")
            if st.form_submit_button(t("save")):
                val = new_deputy.strip() if new_deputy else None
                if val and (val.lower() == (current_owner or "").lower() or not user_exists(val)):
                    _warning_box(t("club_deputy_invalid"))
                elif update_club_deputy(club_id, val or None):
                    _success_box(t("club_deputy_saved"))
                    st.rerun()
                else:
                    _error_box(t("db_error"))

    # oczekujące prośby
    st.subheader("⏳ " + t("club_pending_requests"))
    pending = get_pending_join_requests(club_id)
    if not pending:
        st.caption(t("club_no_pending_requests"))
    else:
        for req_id, req_user, created_at in pending:
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"• {req_user} ({created_at})")
            with cols[1]:
                if st.button(t("approve"), key=f"approve_req_{req_id}", type="primary"):
                    if approve_join_request(req_id, username):
                        _success_box(t("club_action_success"))
                        st.rerun()
                    else:
                        _error_box(t("club_action_error"))
            with cols[2]:
                if st.button(t("reject"), key=f"reject_req_{req_id}", type="tertiary"):
                    if reject_join_request(req_id, username):
                        _success_box(t("club_action_success"))
                        st.rerun()
                    else:
                        _error_box(t("club_action_error"))

    st.markdown("### 👤 / 🛡️ Roles")

    # dodawanie moderatora
    new_mod = st.text_input(t("club_add_moderator"), key=f"new_mod_{club_id}")
    if st.button("OK", key=f"add_mod_btn_{club_id}", type="primary"):
        if not new_mod:
            _warning_box(t("username_required"))
        else:
            if add_member_to_club(new_mod, club_id, role="moderator"):
                _success_box(t("club_action_success"))
                st.rerun()
            else:
                _error_box(t("club_action_error"))

    # w tajnym klubie proseśby nie działają – właściciel może ręcznie dodać członka
    if get_club_privacy(club_id) == "secret":
        new_member = st.text_input(
            t("club_add_member_secret"), key=f"new_secret_member_{club_id}"
        )
        if st.button("OK", key=f"add_secret_member_btn_{club_id}", type="primary"):
            if not new_member:
                _warning_box(t("username_required"))
            else:
                if add_member_to_club(new_member, club_id, role="member"):
                    _success_box(t("club_action_success"))
                    st.rerun()
                else:
                    _error_box(t("club_action_error"))

    st.markdown("---")

    # ===== OPINIE / RECENZJE =====
    st.markdown("### ⭐ " + t("ratings_reviews"))

    # Formularz dodawania opinii
    with st.form(f"review_form_{club_id}"):
        rating = st.selectbox(
            t("your_rating"),
            [1, 2, 3, 4, 5],
            index=4,
            key=f"rating_{club_id}",
        )
        comment = st.text_area(
            t("your_review"),
            key=f"comment_{club_id}",
        )

        submit_review = st.form_submit_button(t("add_review"), type="primary")

    if submit_review:
        success = add_club_review(club_id, username, rating, comment)
        if success:
            _success_box(t("review_added"))
            st.rerun()
        else:
            _error_box(t("db_error"))

    # Wyświetlanie opinii
    reviews = get_reviews_for_club(club_id)
    if not reviews:
        _info_box(t("no_ratings"))
    else:
        avg = sum(r[1] for r in reviews) / len(reviews)
        st.caption(f"⭐ {t('average_rating')}: {avg:.1f}/5 ({len(reviews)})")

        for user, rating, comment in reviews:
            with st.container(border=True):
                st.markdown(f"**{user}** • ⭐ {rating}/5")
                if comment:
                    st.caption(comment)

    st.markdown("---")

    # ===== FORUM KLUBU =====
    club_forum(club_id)


def render_club_events_section(club_id: int, club_city: str | None = None):
    lang = st.session_state.get("language", "pl")
    current_user = st.session_state.get("username")

    st.markdown("## 📅 " + t("upcoming_events"))

    events = get_events_for_club(club_id)

    if not events:
        no_events_msg = (
            t("no_events_organize_first")
        )
        _info_box(no_events_msg)
    else:
        for ev_id, name, ev_date, ev_time, location, desc in events:
            # linia z datą + ewentualnie godziną
            if ev_time:
                date_line = f"📆 {ev_date} • 🕒 {ev_time}"
            else:
                date_line = f"📆 {ev_date}"

            with st.container():
                st.markdown(
                    f"""
                    **{name}**  
                    {date_line}  
                    📍 {location or club_city or '-'}  
                    """
                )
                if desc:
                    st.caption(desc)
                st.markdown("---")

    # ===== UPRAWNIENIA DO DODAWANIA WYDARZEŃ =====
    can_add = False
    if current_user:
        # tu możesz zaostrzyć do is_club_moderator_or_owner, jeśli chcesz
        can_add = is_user_member(current_user, club_id)

    if not can_add:
        # tylko podgląd wydarzeń, bez formularza
        info_text = t("only_members_can_add_events")
        _info_box(info_text)
        return

    # --- formularz dodawania wydarzenia (tylko dla członków) ---
    st.markdown("### ➕ " + t("add_event"))

    name_label = t("event_name_label")
    date_label = t("event_date_label")
    time_label = t("event_time_label")
    place_label = t("event_place_label")
    desc_label = t("event_desc_optional")
    missing_name = (
        t("event_name_required")
    )

    from datetime import datetime, date  # na wszelki wypadek, jeśli nie jest na górze

    with st.form(f"add_event_{club_id}"):
        event_name = st.text_input(name_label)
        event_date = st.date_input(date_label, value=date.today())
        event_time = st.time_input(
            time_label,
            value=datetime.now().time().replace(second=0, microsecond=0),
        )
        location = st.text_input(place_label, value=club_city or "")
        description = st.text_area(desc_label)

        submitted = st.form_submit_button(t("add_event"), type="primary")

    if submitted:
        if not event_name.strip():
            _warning_box(missing_name)
            return

        ok = add_event_for_club(
            club_id=club_id,
            event_name=event_name.strip(),
            event_date=event_date,
            event_time=event_time,
            location=location.strip(),
            description=description.strip(),
        )
        if ok:
            _success_box(t("event_added"))
            st.rerun()
        else:
            _error_box(t("db_error"))




# =========================
# Map
# =========================
def show_osm_map():
    st.subheader("🗺️ " + t("clubs_map"))
    conn = db_conn()

    # Gdy baza nie jest skonfigurowana: pusta mapa
    if not conn:
        _info_box(t("map_no_db_info"))
        m = folium.Map(location=[52.0, 19.0], zoom_start=5)  # środek Polski
        st_folium(m, width=None, height=500)
        return

    try:
        with conn:
            cur = conn.cursor()
            # najpierw próbujemy uzupełnić brakujące współrzędne
            cur.execute("SELECT id, city FROM clubs WHERE latitude IS NULL OR longitude IS NULL")
            missing = cur.fetchall()
            for club_id, city in missing:
                lat, lon = resolve_city_coordinates(city)
                if lat is not None and lon is not None:
                    cur.execute(
                        "UPDATE clubs SET latitude=%s, longitude=%s WHERE id=%s",
                        (lat, lon, club_id),
                    )

            # teraz bierzemy wszystkie z wypełnionymi współrzędnymi (nie ukryte)
            cur.execute(
                """
                SELECT name, latitude, longitude
                FROM clubs
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                  AND (COALESCE(is_hidden, 0) = 0)
                """
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(
                t("no_clubs_on_map")
            )
            m = folium.Map(location=[52.0, 19.0], zoom_start=5)
            st_folium(m, width=None, height=500)
            return

        df = pd.DataFrame(rows, columns=["name", "latitude", "longitude"])

        avg_lat = df["latitude"].mean()
        avg_lon = df["longitude"].mean()
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=5)
        cluster = MarkerCluster().add_to(m)

        for _, r in df.iterrows():
            folium.Marker(
                location=[r["latitude"], r["longitude"]],
                popup=r["name"],
                icon=folium.Icon(icon="flag"),
            ).add_to(cluster)

        # Łuki między klubami partnerskimi (zaakceptowane partnerstwa)
        for row in get_accepted_partnerships_with_coords():
            lat1, lon1, lat2, lon2 = row
            arc = _arc_points(lat1, lon1, lat2, lon2)
            folium.PolyLine(
                locations=arc,
                color="#0d9488",
                weight=2,
                opacity=0.7,
                popup=t("partners_on_map_popup"),
            ).add_to(m)

        st_folium(m, width=None, height=500)
    except Exception as e:
        logger.error("Map error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


# =========================
# Gallery
# =========================
def manage_gallery(club_id: int):
    lang = st.session_state.get("language", "pl")
    MAX_MB = 10
    MAX_BYTES = MAX_MB * 1024 * 1024

    st.subheader("🖼️ " + t("gallery"))

    # dopisz info o limicie do labela
    label = (
        f"{t('select_file')} (max {MAX_MB} MB)"
        if lang == "pl"
        else f"{t('select_file')} (max {MAX_MB} MB)"
    )

    file = st.file_uploader(
        label,
        type=["jpg", "jpeg", "png", "mp4"],
    )

    # upload
    if file:
        size_mb = file.size / (1024 * 1024)

        if file.size > MAX_BYTES:
            if lang == "pl":
                _warning_box(
                    f"Plik jest za duży ({size_mb:.1f} MB). "
                    f"Maksymalny rozmiar to {MAX_MB} MB. "
                    "Spróbuj zmniejszyć plik lub skompresować wideo."
                )
            else:
                _warning_box(
                    f"File is too large ({size_mb:.1f} MB). "
                    f"Maximum size is {MAX_MB} MB. "
                    "Please resize or compress your file."
                )
            return

        path, media_type = save_upload(file, int(club_id))
        if path:
            conn = db_conn()
            if not conn:
                return
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO media_gallery (club_id, media_type, media_path, uploaded_by)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (int(club_id), media_type, path, st.session_state["username"]),
                    )
                _success_box(t("file_added"))
            except Exception as e:
                logger.error("Gallery insert error: %s", e)
                _error_box(t("db_error"))
            finally:
                db_release(conn)

    # odczyt jak było
    conn = db_conn()
    if not conn:
        return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT media_type, media_path FROM media_gallery WHERE club_id=%s",
                (int(club_id),),
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(t("no_media"))
            return

        for media_type, media_path in rows:
            if media_type == "image":
                st.image(media_path)
            elif media_type == "video":
                st.video(media_path)
    finally:
        db_release(conn)


def gallery():
    st.subheader("🖼️ " + t("gallery"))
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT clubs.id, clubs.name
                FROM clubs
                INNER JOIN members ON clubs.id = members.club_id
                WHERE members.username = %s
                """,
                (username,),
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(t("no_club_membership"))
            return

        clubs_df = pd.DataFrame(rows, columns=["id", "name"])
        club_names = clubs_df["name"].tolist()
        selected = st.selectbox(t("select_club"), club_names)
        if selected:
            club_id = int(
                clubs_df.loc[clubs_df["name"] == selected, "id"].iloc[0]
            )
            manage_gallery(club_id)
    finally:
        db_release(conn)

# =========================
# Notifications
# =========================
def notifications_view():
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    st.subheader("🔔 " + t("notifications_title"))

    conn = db_conn()
    if not conn:
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, message, timestamp, read
                FROM notifications
                WHERE username=%s
                ORDER BY timestamp DESC
                """,
                (username,),
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(t("notifications_empty"))
            return

        for nid, message, ts, read_flag in rows:
            cols = st.columns([8, 2])

            with cols[0]:
                style = "opacity:0.6;" if read_flag else "font-weight:bold;"
                st.markdown(
                    f"<div style='{style}'>🕒 {ts}<br>{message}</div>",
                    unsafe_allow_html=True,
                )

            with cols[1]:
                if not read_flag:
                    if st.button(
                        t("notifications_mark_read"),
                        key=f"mark_read_{nid}",
                        type="secondary",
                    ):
                        conn2 = db_conn()
                        if conn2:
                            try:
                                with conn2:
                                    cur2 = conn2.cursor()
                                    cur2.execute(
                                        "UPDATE notifications SET read = 1 WHERE id = %s",
                                        (nid,),
                                    )
                            finally:
                                db_release(conn2)
                        st.rerun()
    finally:
        db_release(conn)

# =========================
# Messages
# =========================
def show_messages():
    st.subheader("💬 " + t("private_messages"))
    conn = db_conn()
    if not conn:
        return
    try:
        username = st.session_state["username"]
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT pm.id, pm.sender, pm.content, pm.timestamp
                FROM private_messages pm
                WHERE pm.receiver = %s
                AND NOT EXISTS (
                    SELECT 1
                    FROM blocks b
                    WHERE (b.blocker = %s AND b.blocked = pm.sender)
                        OR (b.blocker = pm.sender AND b.blocked = %s)
                )
                ORDER BY pm.id DESC
                """,
                (username, username, username),
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(t("no_messages"))
        else:
            for msg_id, sender, content, ts in rows:
                with st.container():
                    st.markdown(f"**{t('from')}: {sender}** • {ts}")
                    st.write(content)

                    if sender != username:
                        with st.expander(t("report_message_title"), expanded=False):
                            reason = st.text_area(
                                t("report_reason_placeholder"),
                                key=f"pm_report_reason_{msg_id}",
                            )
                            if st.button(
                                t("report_button"),
                                key=f"pm_report_btn_{msg_id}",
                                type="primary",
                            ):
                                ok = create_report(
                                    reporter=username,
                                    reported_user=sender,
                                    reported_message_id=msg_id,
                                    reported_message_type="private",
                                    reason=reason,
                                )
                                if ok:
                                    _success_box(t("report_sent"))
                                else:
                                    _error_box(t("report_error"))
    finally:
        db_release(conn)


def send_message():
    st.subheader("✉️ " + t("new_message"))

    # 👇 nowość: spróbuj wziąć odbiorcę z sesji (np. z rekomendacji)
    default_receiver = st.session_state.pop("prefill_receiver", "")

    with st.form("send_msg"):
        receiver = st.text_input(t("to"), value=default_receiver)
        content = st.text_area(t("message_content"))
        submit = st.form_submit_button(t("send"), type="primary")

    if submit:
        # 🔎 prosty filtr treści
        if content and not is_content_allowed(content):
            _warning_box(t("content_not_allowed"))
            return

        if receiver and content:
            sender = st.session_state["username"]
            if not rate_limit_message_ok(sender):
                _warning_box(t("rate_limit_message"))
                return
            conn = db_conn()
            if not conn:
                return
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO private_messages (sender, receiver, content) VALUES (%s,%s,%s)",
                        (sender, receiver, content),
                    )

                register_message_sent(sender)
                # 🔔 powiadomienie dla odbiorcy (w jego języku)
                create_notification_for_user(
                    username=receiver,
                    template_key="notification_new_message",
                    sender=sender,
                )

                _success_box(t("message_sent"))

            except Exception as e:
                logger.error("Send msg error: %s", e)
                _error_box(t("db_error"))
            finally:
                db_release(conn)
        else:
            _warning_box(t("both_fields"))


# =========================
# Events
# =========================
def manage_events():
    lang = st.session_state.get("language", "pl")
    current_user = st.session_state.get("username")

    if not current_user:
        _info_box(t("not_logged_in"))
        return

    # nagłówek + etykiety w 2 językach
    st.subheader(t("events_my_header"))

    conn = db_conn()
    if not conn:
        return

    from datetime import datetime

    try:
        with conn:
            cur = conn.cursor()
            # tylko kluby, do których NALEŻY aktualny użytkownik
            cur.execute(
                """
                SELECT c.*
                FROM clubs c
                JOIN members m ON c.id = m.club_id
                WHERE m.username = %s
                ORDER BY c.name
                """,
                (current_user,),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]

        if not rows:
            _info_box(t("no_clubs_join_to_add_events"))
            return

        clubs = pd.DataFrame(rows, columns=cols)
        club_names = clubs["name"].unique().tolist()

        selected = st.selectbox(t("select_club"), club_names)

        if selected:
            with st.form("add_event_global"):
                event_name = st.text_input(t("event_name_label"))
                event_date = st.date_input(t("event_date_label"))
                event_time = st.time_input(
                    t("event_time_label"),
                    value=datetime.now().time().replace(second=0, microsecond=0),
                )
                location = st.text_input(t("event_location_label"))
                description = st.text_area(t("event_desc_label"))
                submit = st.form_submit_button(t("add_event"), type="primary")

            if submit:
                if not event_name.strip():
                    _warning_box(t("event_name_required"))
                else:
                    club_id = int(
                        clubs.loc[clubs["name"] == selected, "id"].iloc[0]
                    )

                    # konwersja daty/godziny do stringów
                    try:
                        event_date_str = (
                            event_date.isoformat()
                            if hasattr(event_date, "isoformat")
                            else str(event_date)
                        )
                    except Exception:
                        event_date_str = str(event_date)

                    if event_time:
                        try:
                            event_time_str = (
                                event_time.strftime("%H:%M")
                                if hasattr(event_time, "strftime")
                                else str(event_time)
                            )
                        except Exception:
                            event_time_str = str(event_time)
                    else:
                        event_time_str = None

                    with conn:
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO club_events
                                (club_id, event_name, event_date, event_time, location, description)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (
                                club_id,
                                event_name.strip(),
                                event_date_str,
                                event_time_str,
                                location.strip(),
                                description.strip(),
                            ),
                        )
                    maybe_grant_event_achievements(current_user)
                    _success_box(t("event_added"))

    except Exception as e:
        logger.error("Manage events error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


def display_events(events):
    lang = st.session_state.get("language", "pl")

    st.subheader("📅 " + t("upcoming_events"))

    if not events:
        msg = (
            t("no_upcoming_events")
        )
        _info_box(msg)
        return

    date_label = t("date_label")
    loc_label = t("location_label")
    desc_label = t("description_label")

    for event in events:
        event_name, event_date, location = event[:3]
        description = event[3] if len(event) > 3 else ""

        with st.container():
            st.markdown(f"**{event_name}**")
            st.write(f"📆 {date_label}: {event_date}")
            if location:
                st.write(f"📍 {loc_label}: {location}")
            if description:
                st.write(f"📝 {desc_label}: {description}")
            st.markdown("---")



# =========================
# Admin
# =========================
def admin_panel():
    """
    Panel administratora dostępny tylko po podaniu kodu z Google Authenticatora.
    Nie wymaga bycia zalogowanym jako zwykły użytkownik.
    """
    # wejście tylko przez TOTP
    if not ensure_admin_totp():
        return

    # przycisk wyjścia z trybu panelu admina
    if st.button("⬅️ " + t("admin_exit_btn"), type="secondary"):
        st.session_state["admin_portal"] = False
        st.session_state.pop("admin_totp_ok", None)
        st.rerun()

    lang = st.session_state.get("language", "pl")

    st.subheader("🛠️ " + t("administrative_panel"))

    conn = db_conn()
    if not conn:
        return

    try:
        tab_stats, tab_users, tab_clubs, tab_reports = st.tabs(
            [t("stats_label"), t("manage_users"), t("manage_clubs"), t("moderation_reports_label")]
        )

        # ==============
        # Zakładka: Statystyki
        # ==============
        with tab_stats:
            with conn:
                cur = conn.cursor()

                # ogólne liczby
                cur.execute("SELECT COUNT(*) FROM users")
                total_users = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM clubs")
                total_clubs = cur.fetchone()[0]

                # te tabele mogą jeszcze nie istnieć w starej bazie, więc łapiemy wyjątek
                try:
                    cur.execute("SELECT COUNT(*) FROM club_events")
                    total_events = cur.fetchone()[0]
                except Exception:
                    total_events = None

                try:
                    cur.execute("SELECT COUNT(*) FROM private_messages")
                    total_messages = cur.fetchone()[0]
                except Exception:
                    total_messages = None

                # aktywni użytkownicy (na podstawie last_activity)
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE last_activity >= NOW() - INTERVAL '1 day')  AS day,
                        COUNT(*) FILTER (WHERE last_activity >= NOW() - INTERVAL '7 days')  AS week,
                        COUNT(*) FILTER (WHERE last_activity >= NOW() - INTERVAL '30 days') AS month,
                        COUNT(*) FILTER (WHERE last_activity >= NOW() - INTERVAL '365 days') AS year
                    FROM users
                    """
                )
                active_day, active_week, active_month, active_year = cur.fetchone()

                # TOP 5 miast
                cur.execute(
                    """
                    SELECT city, COUNT(*) AS cnt
                    FROM users
                    WHERE city IS NOT NULL AND city <> ''
                    GROUP BY city
                    ORDER BY cnt DESC
                    LIMIT 5
                    """
                )
                top_cities = cur.fetchall()

                # TOP 5 klubów
                cur.execute(
                    """
                    SELECT name, city, members_count
                    FROM clubs
                    ORDER BY members_count DESC, id ASC
                    LIMIT 5
                    """
                )
                top_clubs = cur.fetchall()

                                # Zużycie dysku przez galerię
                try:
                    # Kluby (ID, nazwa, miasto)
                    cur.execute("SELECT id, name, city FROM clubs")
                    clubs_rows = cur.fetchall()

                    # Wszystkie pliki z galerii
                    cur.execute(
                        "SELECT club_id, media_path FROM media_gallery"
                    )
                    gallery_rows = cur.fetchall()
                except Exception:
                    clubs_rows = []
                    gallery_rows = []


            if lang == "pl":
                total_users_label = "Wszyscy użytkownicy"
                total_clubs_label = "Wszystkie kluby"
                total_events_label = "Wydarzenia"
                total_messages_label = "Wiadomości prywatne"
                active_24h_label = "Aktywni 24h"
                active_7d_label = "Aktywni 7 dni"
                active_30d_label = "Aktywni 30 dni"
                active_365d_label = "Aktywni 365 dni"
                cities_header = "TOP 5 miast (liczba użytkowników)"
                clubs_header = "TOP 5 klubów (najwięcej członków)"
            else:
                total_users_label = "Total users"
                total_clubs_label = "Total clubs"
                total_events_label = "Events"
                total_messages_label = "Private messages"
                active_24h_label = "Active last 24h"
                active_7d_label = "Active last 7 days"
                active_30d_label = "Active last 30 days"
                active_365d_label = "Active last 365 days"
                cities_header = "Top 5 cities (users)"
                clubs_header = "Top 5 clubs (members)"

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(total_users_label, total_users)
            col2.metric(total_clubs_label, total_clubs)
            if total_events is not None:
                col3.metric(total_events_label, total_events)
            if total_messages is not None:
                col4.metric(total_messages_label, total_messages)

            st.markdown("---")

                        # 📸 Nowa sekcja: zajętość galerii
            if gallery_rows:
                if lang == "pl":
                    st.markdown("### 📸 Zajętość galerii")
                    st.caption(
                        "Szacunkowe zużycie miejsca przez pliki w galeriach klubów "
                        "(na podstawie rozmiaru plików zapisanych na dysku)."
                    )
                else:
                    st.markdown("### 📸 Gallery storage usage")
                    st.caption(
                        "Approximate disk usage of club galleries "
                        "(based on file sizes stored on disk)."
                    )

                club_meta = {cid: (name, city) for cid, name, city in clubs_rows}
                size_per_club: dict[int, int] = {}
                files_per_club: dict[int, int] = {}

                total_bytes = 0
                for club_id, media_path in gallery_rows:
                    files_per_club[club_id] = files_per_club.get(club_id, 0) + 1

                    size = 0
                    try:
                        if media_path and os.path.exists(media_path):
                            size = os.path.getsize(media_path)
                    except Exception:
                        size = 0

                    total_bytes += size
                    size_per_club[club_id] = size_per_club.get(club_id, 0) + size

                rows_data = []
                for club_id, bytes_used in size_per_club.items():
                    name, city = club_meta.get(club_id, (f"ID {club_id}", ""))
                    mb = bytes_used / (1024 * 1024)
                    files_count = files_per_club.get(club_id, 0)

                    if lang == "pl":
                        rows_data.append(
                            {
                                "ID klubu": club_id,
                                "Klub": name,
                                "Miasto": city,
                                "Plików": files_count,
                                "Rozmiar [MB]": round(mb, 2),
                            }
                        )
                    else:
                        rows_data.append(
                            {
                                "Club ID": club_id,
                                "Club": name,
                                "City": city,
                                "Files": files_count,
                                "Size [MB]": round(mb, 2),
                            }
                        )

                if rows_data:
                    df = pd.DataFrame(rows_data)
                    if lang == "pl":
                        df = df.sort_values("Rozmiar [MB]", ascending=False)
                    else:
                        df = df.sort_values("Size [MB]", ascending=False)

                    st.dataframe(df, use_container_width=True)

                    total_mb = total_bytes / (1024 * 1024)
                    total_files = len(gallery_rows)
                    if lang == "pl":
                        _info_box(
                            f"Łącznie: {total_files} plików, ok. {total_mb:.2f} MB."
                        )
                    else:
                        _info_box(
                            f"Total: {total_files} files, approx. {total_mb:.2f} MB."
                        )
            else:
                # brak plików w galerii – mały żarcik dla admina :)
                _info_box(t("gallery_empty"))

            col5, col6, col7, col8 = st.columns(4)
            col5.metric(active_24h_label, active_day)
            col6.metric(active_7d_label, active_week)
            col7.metric(active_30d_label, active_month)
            col8.metric(active_365d_label, active_year)

            st.markdown("---")

            # top miasta
            st.markdown(f"### 📍 {cities_header}")
            if top_cities:
                df_cities = pd.DataFrame(top_cities, columns=["city", "users"])
                st.table(df_cities)
            else:
                _info_box(t("no_city_data"))

            st.markdown(f"### 🏷️ {clubs_header}")
            if top_clubs:
                df_clubs = pd.DataFrame(
                    top_clubs, columns=["name", "city", "members_count"]
                )
                st.table(df_clubs)
            else:
                _info_box(t("no_clubs_short"))

        # ==============
        # Zakładka: Użytkownicy
        # ==============
        with tab_users:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT
                        u.username,
                        u.email,
                        u.city,
                        u.is_admin,
                        u.is_verified,
                        u.last_activity,
                        COUNT(m.club_id) AS clubs_count
                    FROM users u
                    LEFT JOIN members m ON u.username = m.username
                    GROUP BY
                        u.username, u.email, u.city, u.is_admin, u.is_verified, u.last_activity
                    ORDER BY u.username
                    """
                )
                rows = cur.fetchall()

            if not rows:
                _info_box(t("no_users_manage"))
            else:
                users = pd.DataFrame(
                    rows,
                    columns=[
                        "username",
                        "email",
                        "city",
                        "is_admin",
                        "is_verified",
                        "last_activity",
                        "clubs_count",
                    ],
                )

                # filtry
                if lang == "pl":
                    filter_label = "Filtruj po nazwie lub e-mailu"
                    city_filter_label = "Filtruj po mieście"
                    delete_label = t("select_user_delete")
                    profile_label = t("show_user_profile_btn")
                    confirm_delete_label = t("delete_user")
                else:
                    filter_label = "Filter by username or email"
                    city_filter_label = "Filter by city"
                    delete_label = t("select_user_delete")
                    profile_label = "Show user profile"
                    confirm_delete_label = t("delete_user")

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    text_filter = st.text_input(filter_label, key="admin_users_filter")
                with col_f2:
                    city_filter = st.text_input(
                        city_filter_label, key="admin_users_city_filter"
                    )

                df_filtered = users.copy()

                if text_filter:
                    mask = (
                        df_filtered["username"].str.contains(
                            text_filter, case=False, na=False
                        )
                        | df_filtered["email"].fillna("").str.contains(
                            text_filter, case=False, na=False
                        )
                    )
                    df_filtered = df_filtered[mask]

                if city_filter:
                    df_filtered = df_filtered[
                        df_filtered["city"]
                        .fillna("")
                        .str.contains(city_filter, case=False, na=False)
                    ]

                st.dataframe(df_filtered, use_container_width=True)

                if not df_filtered.empty:
                    # ładniejsze opcje w selectboxie
                    options = []
                    mapping = {}
                    for _, row in df_filtered.iterrows():
                        label = (
                            f"{row['username']} | {row['email'] or '-'} | "
                            f"{row['city'] or '-'} | kluby: {row['clubs_count']}"
                        )
                        options.append(label)
                        mapping[label] = row["username"]

                    selected_label = st.selectbox(delete_label, options)

                    if selected_label:
                        selected_username = mapping[selected_label]

                        st.markdown(
                            f"{profile_label}: "
                            f"[{selected_username}](?user={selected_username})"
                        )

                        if st.button(confirm_delete_label, key="admin_confirm_delete_user", type="tertiary"):
                            with conn:
                                cur = conn.cursor()
                                cur.execute(
                                    "DELETE FROM users WHERE username=%s",
                                    (selected_username,),
                                )
                            _success_box(
                                t("user_deleted", u=selected_username)
                            )
                            st.rerun()

        # ==============
        # Zakładka: Kluby
        # ==============
        with tab_clubs:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT
                        c.id,
                        c.name,
                        c.city,
                        c.members_count,
                        c.owner_username,
                        c.deputy_username,
                        COALESCE(AVG(r.rating), 0) AS avg_rating
                    FROM clubs c
                    LEFT JOIN club_reviews r ON c.id = r.club_id
                    GROUP BY c.id, c.name, c.city, c.members_count, c.owner_username, c.deputy_username
                    ORDER BY c.id
                    """
                )
                rows = cur.fetchall()

            if not rows:
                _info_box(t("no_clubs_manage"))
            else:
                clubs = pd.DataFrame(
                    rows,
                    columns=["id", "name", "city", "members_count", "owner_username", "deputy_username", "avg_rating"],
                )

                if lang == "pl":
                    filter_name_label = "Filtruj po nazwie klubu"
                    filter_city_label = "Filtruj po mieście"
                    select_club_label = t("select_club_delete")
                    view_club_label = t("partners_show_club")
                    delete_club_btn = t("delete_club")
                else:
                    filter_name_label = "Filter by club name"
                    filter_city_label = "Filter by city"
                    select_club_label = t("select_club_delete")
                    view_club_label = t("partners_show_club")
                    delete_club_btn = t("delete_club")

                col_cf1, col_cf2 = st.columns(2)
                with col_cf1:
                    name_filter = st.text_input(
                        filter_name_label, key="admin_clubs_name_filter"
                    )
                with col_cf2:
                    city_filter_c = st.text_input(
                        filter_city_label, key="admin_clubs_city_filter"
                    )

                df_clubs = clubs.copy()

                if name_filter:
                    df_clubs = df_clubs[
                        df_clubs["name"]
                        .str.contains(name_filter, case=False, na=False)
                    ]

                if city_filter_c:
                    df_clubs = df_clubs[
                        df_clubs["city"]
                        .str.contains(city_filter_c, case=False, na=False)
                    ]

                st.dataframe(df_clubs, use_container_width=True)

                if not df_clubs.empty:
                    options = []
                    mapping = {}
                    for _, row in df_clubs.iterrows():
                        owner = row.get("owner_username") or "—"
                        deputy = row.get("deputy_username") or "—"
                        label = (
                            f"{row['id']} | {row['name']} | {row['city']} | "
                            f"👤 {owner} | 🔄 {deputy} | 👥 {row['members_count']} | ⭐ {round(row['avg_rating'], 2)}"
                        )
                        options.append(label)
                        mapping[label] = (row["id"], row["name"], owner, deputy)

                    selected_club_label = st.selectbox(
                        select_club_label, options
                    )

                    if selected_club_label:
                        club_id, club_name, admin_owner, admin_deputy = mapping[selected_club_label]

                        st.markdown(
                            f"{view_club_label}: "
                            f"[{club_name}](?club={club_id})"
                        )
                        st.caption(f"👤 {t('club_owner_label')}: {admin_owner}  |  🔄 {t('club_deputy_display')}: {admin_deputy}")

                        # Zarządzanie klubem (zmiana zarządcy / zastępcy)
                        with st.expander(t("admin_club_manage_expander")):
                            with st.form("admin_club_manage_form"):
                                new_owner = st.text_input(t("club_owner_label"), value="" if admin_owner == "—" else (admin_owner or ""), key="admin_new_owner")
                                new_deputy = st.text_input(t("club_deputy_display"), value="" if admin_deputy == "—" else (admin_deputy or ""), key="admin_new_deputy")
                                if st.form_submit_button(t("admin_save_club_manage")):
                                    ok = True
                                    if new_owner.strip() and not user_exists(new_owner.strip()):
                                        _warning_box(t("club_deputy_invalid"))
                                        ok = False
                                    if ok and new_deputy.strip() and not user_exists(new_deputy.strip()):
                                        _warning_box(t("club_deputy_invalid"))
                                        ok = False
                                    if ok:
                                        if update_club_owner(club_id, new_owner.strip() or None):
                                            update_club_deputy(club_id, new_deputy.strip() or None)
                                            _success_box(t("club_deputy_saved"))
                                            st.rerun()
                                        else:
                                            _error_box(t("db_error"))

                        if st.button(delete_club_btn, key="admin_delete_club_btn", type="tertiary"):
                            with conn:
                                cur = conn.cursor()
                                cur.execute(
                                    "DELETE FROM clubs WHERE id=%s",
                                    (club_id,),
                                )
                            _success_box(t("club_deleted", c=club_name))
                            st.rerun()

        # ==============
        # Zakładka: Moderacja / zgłoszenia
        # (zostawiamy tak jak było u Ciebie)
        # ==============
        with tab_reports:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT
                        id,
                        reporter,
                        reported_user,
                        reported_club,
                        reported_message_id,
                        reported_message_type,
                        reason,
                        status,
                        created_at
                    FROM reports
                    ORDER BY status ASC, created_at DESC
                    """
                )
                reports = cur.fetchall()

            if not reports:
                msg = t("no_reports_angel")
                _info_box(msg)
            else:
                for (
                    rid,
                    reporter,
                    reported_user,
                    reported_club,
                    reported_message_id,
                    reported_message_type,
                    reason,
                    status,
                    created_at,
                ) in reports:
                    status_icon = "🟢" if status == "closed" else "🔴"
                    header = f"{status_icon} #{rid} • {created_at} • {status}"

                    with st.expander(header, expanded=(status == "open")):
                        st.markdown(f"**Zgłaszający:** {reporter}")
                        if reported_user:
                            st.markdown(
                                f"**Użytkownik:** "
                                f"[{reported_user}](?user={reported_user})"
                            )
                        if reported_club:
                            st.markdown(
                                f"**Klub ID:** "
                                f"[{reported_club}](?club={reported_club})"
                            )
                        if reported_message_id:
                            st.markdown(
                                f"**ID wiadomości:** {reported_message_id} "
                                f"({reported_message_type or '-'})"
                            )
                        st.markdown("**Powód:**")
                        st.write(reason)

                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            if status == "open":
                                if st.button(t("report_close"), key=f"report_close_{rid}", type="primary"):
                                    if update_report_status(rid, "closed"):
                                        _success_box(t("report_status_updated"))
                                        st.rerun()
                            else:
                                if st.button(t("report_reopen"), key=f"report_reopen_{rid}", type="secondary"):
                                    if update_report_status(rid, "open"):
                                        _success_box(t("report_status_updated"))
                                        st.rerun()
                        with col_b:
                            if reported_user and status == "open":
                                if st.button(t("report_warn_user"), key=f"report_warn_{rid}"):
                                    create_notification_for_user(reported_user, "notification_warning_from_admin")
                                    _success_box(t("report_warning_sent"))
                                    st.rerun()
                        with col_c:
                            if reported_club and status == "open":
                                if st.button(t("report_hide_club"), key=f"report_hide_{rid}", type="tertiary"):
                                    if set_club_hidden(reported_club, True):
                                        _success_box(t("report_club_hidden"))
                                        st.rerun()
                        with col_d:
                            if reported_club:
                                if st.button(t("report_unhide_club"), key=f"report_unhide_{rid}"):
                                    if set_club_hidden(reported_club, False):
                                        _success_box(t("report_club_unhidden"))
                                        st.rerun()

    except Exception as e:
        logger.error("Admin panel error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


# =========================
# Member search & Hobby search
# =========================
def search_member():
    st.subheader("👤 " + t("select_member"))
    name = st.text_input(t("search"))
    if st.button(t("search"), type="primary"):
        conn = db_conn()
        if not conn:
            return
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT clubs.name AS club_name, members.username
                    FROM members
                    INNER JOIN clubs ON members.club_id = clubs.id
                    WHERE members.username ILIKE %s
                """, (f"%{name}%",))
                rows = cur.fetchall()

            if not rows:
                _info_box(t("no_results"))
            else:
                data = [{"club_name": r[0], "username": r[1]} for r in rows]
                df = pd.DataFrame(data, columns=["club_name", "username"])
                st.dataframe(df, use_container_width=True)
        finally:
            db_release(conn)



def search_by_hobby():
    st.subheader("🎯 " + t("search_by_hobby"))
    username = st.session_state.get("username")

    col1, col2 = st.columns(2)
    with col1:
        hobby = st.text_input("Hobby")
    with col2:
        city = st.text_input(t("city") + " (opcjonalne)")

    if st.button(t("search"), type="primary"):
        conn = db_conn()
        if not conn:
            return
        try:
            params = [hobby]
            sql = """
                SELECT
                    users.username,
                    users.city,
                    users.last_activity,
                    (NOW() - users.last_activity < INTERVAL '5 minutes') AS is_online
                FROM hobbies
                INNER JOIN users ON hobbies.username = users.username
                WHERE hobbies.hobby = %s
            """
            if city:
                sql += " AND users.city ILIKE %s"
                params.append(f"%{city}%")

            if username:
                sql += " AND users.username <> %s"
                params.append(username)

            sql += """
                ORDER BY
                    (users.city = %s) DESC,
                    is_online DESC,
                    users.last_activity DESC NULLS LAST
            """

            # miasto zalogowanego użytkownika (boost w sortowaniu)
            user_city = None
            if username:
                with conn:
                    cur2 = conn.cursor()
                    cur2.execute(
                        "SELECT city FROM users WHERE username=%s",
                        (username,),
                    )
                    r = cur2.fetchone()
                    user_city = r[0] if r else None
            params.append(user_city or "")

            with conn:
                cur = conn.cursor()
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

            if not rows:
                _info_box(t("no_results"))
            else:
                for u_name, u_city, last_act, is_online in rows:
                    status_label = t("online") if is_online else t("offline")
                    st.markdown(f"**{u_name}** ({u_city}) — {status_label}")
                    if last_act:
                        st.caption(f"{t('last_activity')}: {last_act}")
        finally:
            db_release(conn)



def recommend_users():
    lang = st.session_state.get("language", "pl")
    st.subheader("👥 " + t("user_recommendations"))

    username = st.session_state.get("username")
    if not username:
        msg = (
            "Zaloguj się, aby zobaczyć rekomendacje."
            if lang == "pl"
            else "Log in to see recommendations."
        )
        _warning_box(msg)
        return

    conn = db_conn()
    if not conn:
        _error_box(t("db_error"))
        return

    try:
        with conn:
            cur = conn.cursor()

            # Miasto zalogowanego użytkownika
            cur.execute(
                "SELECT city FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            user_city = row[0] if row else None

            # Użytkownicy, których NIE obserwujesz i nie są Tobą
            # preferuj tych z tego samego miasta, online i bardziej aktywnych
            cur.execute(
                """
                SELECT
                    u.username,
                    u.city,
                    u.last_activity,
                    (NOW() - u.last_activity < INTERVAL '5 minutes') AS is_online,
                    CASE WHEN u.city = %s AND %s IS NOT NULL THEN 1 ELSE 0 END AS same_city
                FROM users u
                WHERE u.username <> %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM follows f
                      WHERE f.follower = %s
                        AND f.following = u.username
                  )
                ORDER BY same_city DESC,
                         is_online DESC,
                         u.last_activity DESC NULLS LAST,
                         u.username
                LIMIT 50
                """,
                (user_city, user_city, username, username),
            )
            rows = cur.fetchall()

        if not rows:
            _info_box(t("no_results"))
            return

        # --- etykiety ---
        city_label = "Miasto" if lang == "pl" else "City"
        same_city_label = (
            "To samo miasto co Ty"
            if lang == "pl"
            else "Same city as you"
        )
        online_label = t("online")
        offline_label = t("offline")
        follow_btn_label = t("follow_btn")
        msg_btn_label = "✉️ " + t("message_btn")

        # helper do rysowania kart użytkowników (żeby nie kopiować kodu)
        def render_user_cards(user_rows, key_prefix: str):
            for u_name, city, last_activity, is_on, same_city in user_rows:
                with st.container(border=True):
                    # nagłówek
                    st.markdown(f"**{u_name}**")

                    # status + miasto
                    status_label = online_label if is_on else offline_label
                    if city:
                        st.caption(f"📍 {city_label}: {city}")
                    st.caption(f"🟢 {status_label}")

                    # info o wspólnym mieście
                    if same_city:
                        st.caption(f"🏙️ {same_city_label}")

                    # przyciski akcji
                    col1, col2, col3 = st.columns([1, 1, 2])

                    with col1:
                        if st.button(
                            follow_btn_label,
                            key=f"{key_prefix}_follow_{u_name}",
                            type="primary",
                        ):
                            follow_user(u_name)
                            st.rerun()

                    with col2:
                        if st.button(
                            msg_btn_label,
                            key=f"{key_prefix}_msg_{u_name}",
                            type="secondary",
                        ):
                            st.session_state["prefill_receiver"] = u_name
                            # używamy kodu klucza z menu, nie polskiego stringa
                            st.session_state["menu_override"] = "messages"
                            st.rerun()

        # === TOP 10 REKOMENDACJI ===
        top10 = rows[:10]
        top_header = (
            "🏆 Top 10 polecanych"
            if lang == "pl"
            else "🏆 Top 10 recommended"
        )
        st.markdown(f"### {top_header}")
        render_user_cards(top10, "top")

        # === REKOMENDACJE WEDŁUG KATEGORII ===
        cat_header = (
            "📂 Rekomendacje według kategorii"
            if lang == "pl"
            else "📂 Recommendations by category"
        )
        st.markdown(f"### {cat_header}")

        # podział na kategorie
        same_city_users = [r for r in rows if r[4]]
        online_users = [r for r in rows if r[3]]
        other_city_users = [r for r in rows if not r[4]]

        tab1, tab2, tab3 = st.tabs(
            [t("tab_same_city"), t("tab_online"), t("tab_other_cities")]
        )

        with tab1:
            if same_city_users:
                render_user_cards(same_city_users, "samecity")
            else:
                _info_box(t("no_results"))

        with tab2:
            if online_users:
                render_user_cards(online_users, "online")
            else:
                _info_box(t("no_results"))

        with tab3:
            if other_city_users:
                render_user_cards(other_city_users, "othercity")
            else:
                _info_box(t("no_results"))

    except Exception as e:
        logger.error("User recommendations error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


# =========================
# Friends / Following
# =========================
def follow_user(target_username: str):
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return
    if username == target_username:
        return  # sam siebie nie musisz obserwować, ego i tak da radę ;)

    conn = db_conn()
    if not conn:
        return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO follows (follower, following)
                VALUES (%s, %s)
                ON CONFLICT (follower, following) DO NOTHING
                """,
                (username, target_username),
            )
        _success_box(t("now_following_user", u=target_username))
    except Exception as e:
        logger.error("Follow error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


def unfollow_user(target_username: str):
    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    conn = db_conn()
    if not conn:
        return
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM follows WHERE follower=%s AND following=%s",
                (username, target_username),
            )
        _success_box(t("no_longer_following_user", u=target_username))
    except Exception as e:
        logger.error("Unfollow error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)


def friends_page():
    lang = st.session_state.get("language", "pl")
    st.subheader("👥 " + t("friends_list"))

    username = st.session_state.get("username")
    if not username:
        _error_box(t("not_logged_in"))
        return

    conn = db_conn()
    if not conn:
        _error_box(t("db_error"))
        return

    try:
        with conn:
            cur = conn.cursor()

            # osoby, które TY obserwujesz (following)
            cur.execute(
                """
                SELECT u.username,
                       u.city,
                       u.last_activity,
                       (NOW() - u.last_activity < INTERVAL '5 minutes') AS is_online
                FROM follows f
                JOIN users u ON u.username = f.following
                WHERE f.follower = %s
                ORDER BY is_online DESC,
                         u.last_activity DESC NULLS LAST,
                         u.username
                """,
                (username,),
            )
            following_rows = cur.fetchall()

            # osoby, które obserwują CIEBIE (followers)
            cur.execute(
                """
                SELECT u.username,
                       u.city,
                       u.last_activity,
                       (NOW() - u.last_activity < INTERVAL '5 minutes') AS is_online
                FROM follows f
                JOIN users u ON u.username = f.follower
                WHERE f.following = %s
                ORDER BY is_online DESC,
                         u.last_activity DESC NULLS LAST,
                         u.username
                """,
                (username,),
            )
            follower_rows = cur.fetchall()

        col1, col2 = st.columns(2)

        city_label = "Miasto" if lang == "pl" else "City"
        online_label = t("online")
        offline_label = t("offline")

        unfollow_btn_label = t("unfollow_btn")
        follow_back_btn_label = t("follow_btn")
        msg_btn_label = "✉️ " + t("message_btn")

        # LEWA KOLUMNA – osoby, które obserwujesz
        with col1:
            st.markdown("### " + t("following"))
            if not following_rows:
                _info_box(t("no_results"))
            else:
                for u_name, city, last_activity, is_on in following_rows:
                    status_label = online_label if is_on else offline_label

                    with st.container(border=True):
                        st.markdown(f"**{u_name}**")
                        if city:
                            st.caption(f"📍 {city_label}: {city}")
                        st.caption(f"🟢 {status_label}")

                        c1, c2 = st.columns(2)

                        with c1:
                            if st.button(
                                unfollow_btn_label,
                                key=f"unfollow_{u_name}",
                                type="tertiary",
                            ):
                                unfollow_user(u_name)
                                st.rerun()

                        with c2:
                            if st.button(
                                msg_btn_label,
                                key=f"friends_msg_{u_name}",
                                type="secondary",
                            ):
                                st.session_state["prefill_receiver"] = u_name
                                st.session_state["menu_override"] = "messages"
                                st.rerun()

        # PRAWA KOLUMNA – osoby, które obserwują CIEBIE
        with col2:
            st.markdown("### " + t("followers"))
            if not follower_rows:
                _info_box(t("no_results"))
            else:
                for u_name, city, last_activity, is_on in follower_rows:
                    status_label = online_label if is_on else offline_label

                    with st.container(border=True):
                        st.markdown(f"**{u_name}**")
                        if city:
                            st.caption(f"📍 {city_label}: {city}")
                        st.caption(f"🟢 {status_label}")

                        # sprawdzamy, czy Ty już ich obserwujesz
                        is_already_following = any(
                            row[0] == u_name for row in following_rows
                        )

                        c1, c2 = st.columns(2)

                        with c1:
                            if not is_already_following:
                                if st.button(
                                    follow_back_btn_label,
                                    key=f"follow_back_{u_name}",
                                    type="primary",
                                ):
                                    follow_user(u_name)
                                    st.rerun()
                            else:
                                st.write(t("you_follow_label"))

                        with c2:
                            if st.button(
                                msg_btn_label,
                                key=f"followers_msg_{u_name}",
                                type="secondary",
                            ):
                                st.session_state["prefill_receiver"] = u_name
                                st.session_state["menu_override"] = "messages"
                                st.rerun()

    except Exception as e:
        logger.error("Friends page error: %s", e)
        _error_box(t("db_error"))
    finally:
        db_release(conn)



# =========================
# Diagnostics
# =========================
def diagnostics():
    import socket, json
    st.subheader("🔧 Diagnostics")
    host = os.getenv("DB_HOST") or "—"
    db_url = os.getenv("DATABASE_URL")
    st.code(json.dumps({
        "DB_HOST": host,
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_SSLMODE": os.getenv("DB_SSLMODE", "require"),
        "DATABASE_URL_present": bool(db_url),
    }, ensure_ascii=False, indent=2))
    if host and host != "—":
        try:
            st.write("DNS lookup for DB_HOST:", host)
            st.write(socket.getaddrinfo(host, None))
            _success_box("DNS resolved ✔")
        except Exception as e:
            _error_box(f"DNS resolution failed: {e}")
    try:
        conn = db_conn()
        if conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                _success_box("DB connection OK ✔")
            db_release(conn)
        else:
            _error_box("DB connection is None.")
    except Exception as e:
        _error_box(f"DB quick test failed: {e}")



def diagnostics():
    st.subheader("🔧 Diagnostics")

    conn = db_conn()
    if not conn:
        _error_box(t("db_connection_error"))
        return

    try:
        with conn:
            cur = conn.cursor()

            # Użytkownicy
            cur.execute("SELECT username, city, is_admin FROM users ORDER BY username")
            user_rows = cur.fetchall()
            st.markdown("### Użytkownicy w bazie")
            if not user_rows:
                st.write("— brak —")
            else:
                df_users = pd.DataFrame(user_rows, columns=["username", "city", "is_admin"])
                st.dataframe(df_users, use_container_width=True)

            # Liczby rekordów w tabelach
            stats = {}
            for table in ["clubs", "hobbies", "members", "club_events", "forum_messages", "private_messages"]:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]

            st.markdown("### Statystyki tabel")
            st.json(stats)
    except Exception as e:
        logger.error("Diagnostics error: %s", e)
        _error_box(f"Błąd diagnostyki: {e}")
    finally:
        db_release(conn)


def get_public_user_profile(username: str):
    """
    Minimalne dane o użytkowniku do publicznego profilu.
    """
    username = (username or "").strip()
    if not username:
        return None

    conn = db_conn()
    if not conn:
        return None

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, city, description, profile_picture
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()
    except Exception as e:
        logger.error("get_public_user_profile error: %s", e)
        return None
    finally:
        db_release(conn)

    if not row:
        return None

    return {
        "username": row[0],
        "city": row[1],
        "description": row[2],
        "profile_picture": row[3],
    }


def public_user_profile_view(username: str):
    lang = st.session_state.get("language", "pl")

    conn = db_conn()
    if not conn:
        _error_box(t("db_error"))
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT username, city, hobbies, about_me, last_activity
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()

        if not row:
            _error_box(t("user_not_found"))
            return

        username, city, hobbies, about_me, last_activity = row

        title = t("public_user_profile_title")

        st.markdown(f"## 👤 {title}: {username}")

        if city:
            st.write(f"📍 **{t('city')}:** {city}")

        if last_activity:
            st.write(f"⏰ **{t('last_activity')}:** {last_activity}")

        st.markdown("---")

        st.markdown(f"### ⭐ {t('hobbies_title')}")
        if hobbies:
            st.write(hobbies)
        else:
            _info_box(t("no_data"))

        st.markdown(f"### 📝 {t('profile_about')}")
        if about_me:
            st.write(about_me)
        else:
            _info_box(t("no_description"))

        # --- Zgłoszenie użytkownika ---
        current_user = st.session_state.get("username")
        if current_user and current_user != username:
            st.markdown("---")
            st.markdown(f"### 🚩 {t('report_user_title')}")

            with st.form(f"report_user_form_{username}"):
                reason = st.text_area(
                    t("report_reason_placeholder"),
                    key=f"report_reason_user_{username}",
                )
                submitted = st.form_submit_button(t("report_button"), type="primary")

            if submitted:
                ok = create_report(
                    reporter=current_user,
                    reported_user=username,
                    reason=reason,
                )
                if ok:
                    _success_box(t("report_sent"))
                else:
                    _error_box(t("report_error"))
    finally:
        db_release(conn)


def public_club_view(club_id: int):
    lang = st.session_state.get("language", "pl")

    conn = db_conn()
    if not conn:
        _error_box(t("db_error"))
        return

    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT c.id, c.name, c.city, c.description, COUNT(m.username) AS members_count
                FROM clubs c
                LEFT JOIN members m ON c.id = m.club_id
                WHERE c.id = %s
                GROUP BY c.id
                """,
                (club_id,),
            )
            club = cur.fetchone()

        if not club:
            _error_box(t("club_not_found"))
            return

        club_id, name, city, description, members_count = club

        title = t("public_club_view_title")

        st.markdown(f"## 🏷️ {title}: {name}")
        st.write(f"📍 **{t('city')}:** {city}")
        st.write(f"👥 **{t('members')}:** {members_count}")

        st.markdown(f"### 📖 {t('club_description')}")
        if description:
            st.write(description)
        else:
            _info_box(t("no_description"))

        st.markdown("---")

        # Podgląd wydarzeń w trybie tylko-do-odczytu
        render_club_events_section(club_id, club_city=city)

        # --- Zgłoszenie klubu ---
        current_user = st.session_state.get("username")
        if current_user:
            st.markdown("---")
            st.markdown(f"### 🚩 {t('report_club_title')}")

            with st.form(f"report_club_form_{club_id}"):
                reason = st.text_area(
                    t("report_reason_placeholder"),
                    key=f"report_reason_club_{club_id}",
                )
                submitted = st.form_submit_button(t("report_button"), type="primary")

            if submitted:
                ok = create_report(
                    reporter=current_user,
                    reported_club=club_id,
                    reason=reason,
                )
                if ok:
                    _success_box(t("report_sent"))
                else:
                    _error_box(t("report_error"))

    finally:
        db_release(conn)



# =========================
# Terms
# =========================
def show_terms_of_service():
    st.subheader("📜 " + t("terms_title"))
    st.markdown(t("terms_text"))

def show_privacy_policy():
    st.subheader("🔒 " + t("privacy_title"))
    st.markdown(t("privacy_text"))

def about_view():
    """Strona O nas / Jak to działa – opis aplikacji i CTA."""
    st.title("📖 " + t("about_title"))
    st.caption(t("about_subtitle"))
    assets_dir = pathlib.Path(__file__).parent / "assets"
    intro_img = assets_dir / "intro_background.png"
    if not intro_img.exists():
        intro_img = assets_dir / "intro_background.jpg"
    if intro_img.exists():
        try:
            st.image(str(intro_img), use_container_width=True, caption="")
        except Exception:
            pass
    st.markdown(t("about_body"))
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t("about_cta_clubs"), type="primary", use_container_width=True, key="about_btn_clubs"):
            st.session_state["menu_override"] = "club_list"
            st.rerun()
    with col2:
        if st.button("🏠 " + t("dashboard_menu"), use_container_width=True, key="about_btn_dash", type="secondary"):
            st.session_state["menu_override"] = "dashboard_menu"
            st.rerun()


def contact_support_view():
    st.title("📬 Kontakt & Wsparcie / Contact & Support")

    st.markdown("""
## 🇵🇱 Wsparcie twórcy
Tworzę tę aplikację z pasji i misji łączenia ludzi przez ich hobby.  
Jeśli chcesz wesprzeć rozwój projektu i pomóc utrzymać go przy życiu — będzie mi ogromnie miło!  
Każda kawa to dodatkowa linijka kodu napisana z uśmiechem ☕💙  

**☕ Buy me a coffee:**  
https://buycoffee.to/find-friends-with-hobbies  

**💸 PayPal:**  
@RomanKnopp726  

**📨 Kontakt:**  
find_friends_with_hobbies@proton.me  

---

## 🇬🇧 Support the creator
I’m building this app to help people connect through shared hobbies.  
If you'd like to support the project and keep it alive — I'd truly appreciate it!  
Every coffee powers the next feature ☕🚀  

**☕ Buy me a coffee:**  
https://buycoffee.to/find-friends-with-hobbies  

**💸 PayPal:**  
@RomanKnopp726  

**📨 Contact:**  
find_friends_with_hobbies@proton.me  
    """)

# =========================
# APP START / MAIN
# =========================

try:
    initialize_db()
except Exception as e:
    logger.exception("initialize_db failed (shared DB or permissions?): %s", e)
    _error_box(t("db_connection_error") + " " + (str(e)[:200] or ""))

# --- Flag stanu (przed jakimkolwiek widokiem) ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "show_register" not in st.session_state:
    st.session_state["show_register"] = False

if "reset_mode" not in st.session_state:
    st.session_state["reset_mode"] = False

if "admin_portal" not in st.session_state:
    st.session_state["admin_portal"] = False

if "intro_seen" not in st.session_state:
    st.session_state["intro_seen"] = False


# =========================
# Specjalne tryby z linków w mailach
# =========================

if verify_token:
    verify_email_view(verify_token)
    st.stop()

if reset_token:
    reset_password_view(reset_token)
    st.stop()

# =========================
# PUBLICZNE WIDOKI Z LINKÓW
# =========================

public_username = query_params.get("user")
public_club_id = query_params.get("club")

# Jeśli w URL jest ?user=Roman -> pokaż publiczny profil
if public_username:
    public_user_profile_view(public_username)
    st.stop()

# Jeśli w URL jest ?club=3 -> pokaż publiczny widok klubu
if public_club_id:
    try:
        cid = int(public_club_id)
    except (TypeError, ValueError):
        _error_box("Nieprawidłowy identyfikator klubu.")
    else:
        public_club_view(cid)
    st.stop()

# =========================
# TRYB PANELU ADMINA (zawsze dostępny, jeśli kliknięto przycisk)
# =========================

if st.session_state.get("admin_portal"):
    admin_panel()
    st.stop()

# =========================
# STRONA TYTUŁOWA / INTRO (przed wejściem)
# =========================
if not st.session_state.get("intro_seen"):
    show_intro_screen()
    st.stop()

# =========================
# WIDOK DLA NIEZALOGOWANYCH (start – bez sidebara, język i admin na stronie)
# =========================

if not st.session_state["logged_in"]:
    show_start_screen()
    st.stop()

# =========================
# WIDOK DLA ZALOGOWANYCH (boczne menu z językiem i panelem admina)
# =========================
language_selector()

update_last_activity()

# --- Podpowiedź o rozwijanym menu (na górze sidebara) ---
st.sidebar.caption(t("sidebar_expand_hint"))

# --- Wsparcie & Kontakt (przycisk w sidebarze) ---
if st.sidebar.button("📬 " + t("contact_support"), key="contact_support_btn"):
    st.session_state["menu_override"] = "contact_support"
    st.rerun()

if user_needs_onboarding(st.session_state["username"]):
    onboarding_view()
    st.stop()

apply_customizations()

# 🔔 Dzwonek z liczbą nieprzeczytanych powiadomień
uname = st.session_state.get("username")
unread = get_unread_notifications_count(uname) if uname else 0

bell_label_base = "🔔 " + t("notifications_bell_label")
if unread > 0:
    bell_label = f"{bell_label_base} ({unread})"
else:
    bell_label = bell_label_base

if st.sidebar.button(bell_label, key="notifications_bell"):
    st.session_state["menu_override"] = "notifications_menu"
    st.rerun()

st.sidebar.markdown("## 📂 " + t("menu"))

# Ikony przy pozycjach menu
MENU_ICONS = {
    "dashboard_menu": "🏠",
    "profile": "👤",
    "club_list": "📋",
    "clubs_map": "🗺️",
    "events_menu": "📅",
    "messages": "💬",
    "friends_menu": "👥",
    "recommendations_menu": "✨",
    "gallery": "🖼️",
    "about_menu": "📖",
    "contact_support": "📬",
    "logout": "🚪",
}

# używamy KODÓW, nie gołych stringów
menu_keys = [
    "dashboard_menu",
    "profile",
    "club_list",
    "clubs_map",
    "events_menu",
    "messages",
    "friends_menu",
    "recommendations_menu",
    "gallery",
    "about_menu",
    "contact_support",
]

menu_keys.append("logout")

def _format_menu(key: str) -> str:
    icon = MENU_ICONS.get(key, "•")
    return f"{icon} {t(key)}"

override = st.session_state.pop("menu_override", None)

menu = st.sidebar.radio(
    t("choose_view"),
    options=menu_keys,
    format_func=_format_menu,
    index=0,
    key="main_menu_radio",
)

if override and override in menu_keys:
    menu = override

# --- Podpowiedź o menu tylko w zakładce „Co w mieście”, raz – po „OK, rozumiem” już się nie pokazuje ---
# Komunikat jako zwykły blok HTML (bez st.info), przycisk osobno – unikamy „przycisku w przycisku”
if menu == "dashboard_menu" and not st.session_state.get("menu_hint_dismissed"):
    hint_raw = t("sidebar_collapsed_hint")
    hint_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", hint_raw)
    st.markdown(
        f'<div style="background-color: #e0f2f1; border: 1px solid #0d9488; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; color: #0f172a;">{hint_html}</div>',
        unsafe_allow_html=True,
    )
    if st.button(t("sidebar_collapsed_ok"), key="menu_hint_ok", type="secondary"):
        st.session_state["menu_hint_dismissed"] = True
        st.rerun()
    st.markdown("---")

# router po KODACH, nie po tekstach
if menu == "dashboard_menu":
    dashboard_view()

elif menu == "profile":
    set_user_customizations()

elif menu == "club_list":
    view_clubs()

elif menu == "clubs_map":
    show_osm_map()

elif menu == "events_menu":
    city = get_user_city(st.session_state["username"])

    # 🔙 powrót do „Co w mieście”
    if st.button("🏠 " + t("events_back_to_dashboard"), type="secondary"):
        st.session_state["menu_override"] = "dashboard_menu"
        st.rerun()

    events = get_upcoming_events_in_city(city)
    display_events(events)
    manage_events()


elif menu == "notifications_menu":
    notifications_view()

elif menu == "messages":
    show_messages()
    send_message()

elif menu == "friends_menu":
    friends_page()

elif menu == "recommendations_menu":
    recommend_users()

elif menu == "gallery":
    gallery()

elif menu == "about_menu":
    about_view()

elif menu == "admin_panel_menu":
    admin_panel()

elif menu == "contact_support":
    contact_support_view()

elif menu == "logout":
    # zapamiętaj język, żeby po wylogowaniu nie przeskakiwał
    lang = st.session_state.get("language")
    st.session_state.clear()
    if lang:
        st.session_state["_force_language"] = lang
    st.rerun()

# Wstrzyknięcie na końcu runu – style są ostatnie w DOM i wygrywają z innymi (alerty, file uploader)
def _inject_alert_and_uploader_fix():
    """Ciemny, czytelny tekst w st.info/st.warning/st.error i w st.file_uploader – wstrzyknięte na końcu runu."""
    st.markdown("""
    <style id="alert-uploader-fix">
    /* Alerty – zawsze ciemny tekst na jasnym tle (niezależnie od motywu i kolejności stylów) */
    .stAlert, .stSuccess, [data-testid="stAlert"],
    .stAlert *, .stSuccess *, [data-testid="stAlert"] *,
    .stAlert p, .stAlert span, .stAlert div, [data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div,
    [data-testid="stAlert"] .stMarkdown, [data-testid="stAlert"] .stMarkdown * {
        color: #1e293b !important;
    }
    .stAlert, .stSuccess, [data-testid="stAlert"] {
        background-color: #e0f2f1 !important;
        border-color: #0d9488 !important;
    }
    /* File uploader – ciemny tekst w drop zone */
    [data-testid="stFileUploader"], [data-testid="stFileUploader"] *, [data-testid="stFileUploader"] span, [data-testid="stFileUploader"] small {
        color: #1e293b !important;
    }
    [data-testid="stFileUploader"] [data-testid="stDropzoneInput"],
    [data-testid="stFileUploader"] [data-testid="stDropzoneInput"] * {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
    }
    </style>
    """, unsafe_allow_html=True)

_inject_alert_and_uploader_fix()
