# geo_weather.py – geokodowanie (OpenCage) i pogoda (Open-Meteo)
"""
Geolokalizacja miast i pobieranie pogody.
- geocode_with_opencage(city_name) -> (lat, lon) lub (None, None)
- resolve_city_coordinates(city) – cache w DB + OpenCage
- get_weather(city, lang) – pogoda dla miasta (język do formatu tekstu)
"""

import logging
import requests
import streamlit as st

import config
from db import get_connection, db_conn, db_release

logger = logging.getLogger(__name__)


def _geocode_nominatim(city_name: str):
    """
    Fallback: geokoder Nominatim (OpenStreetMap), bez klucza API.
    Używany gdy OPENCAGE_API_KEY nie jest ustawiony.
    """
    city_name = (city_name or "").strip()
    if not city_name:
        return (None, None)
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_name, "format": "json", "limit": 1}
        headers = {"User-Agent": "FindFriendsWithHobbies/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code != 200:
            return (None, None)
        data = resp.json()
        if not data:
            return (None, None)
        lat = data[0].get("lat")
        lon = data[0].get("lon")
        if lat is not None and lon is not None:
            return (float(lat), float(lon))
    except Exception as e:
        logger.warning("Nominatim geocode failed for '%s': %s", city_name, e)
    return (None, None)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def geocode_with_opencage(city_name: str):
    """
    Geokoder OpenCage. Najpierw dokładna nazwa, potem z DEFAULT_COUNTRY jako hint.
    Gdy brak klucza API – fallback na Nominatim.
    """
    city_name = (city_name or "").strip()
    if not city_name:
        return (None, None)

    if config.OPENCAGE_API_KEY:
        queries = [city_name]
        if config.DEFAULT_COUNTRY and config.DEFAULT_COUNTRY.lower() not in city_name.lower():
            queries.append(f"{city_name}, {config.DEFAULT_COUNTRY}")

        url = "https://api.opencagedata.com/geocode/v1/json"
        for q in queries:
            params = {
                "q": q,
                "key": config.OPENCAGE_API_KEY,
                "limit": 1,
                "no_annotations": 1,
            }
            try:
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                results = data.get("results")
                if not results:
                    continue
                geom = results[0].get("geometry", {})
                lat, lon = geom.get("lat"), geom.get("lng")
                if lat is not None and lon is not None:
                    return (lat, lon)
            except Exception:
                continue

    return _geocode_nominatim(city_name)


def resolve_city_coordinates(city: str):
    """Współrzędne miasta: najpierw cache w city_locations, potem OpenCage."""
    city = (city or "").strip()
    if not city:
        return (None, None)

    conn = get_connection()
    if conn is None:
        # tryb bez bazy (SKIP_DB) – tylko geokoder zewnętrzny
        return geocode_with_opencage(city)
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT latitude, longitude FROM city_locations WHERE city = %s",
            (city,),
        )
        row = cur.fetchone()
        if row and row[0] is not None and row[1] is not None:
            return (row[0], row[1])

        lat, lon = geocode_with_opencage(city)
        if lat is not None and lon is not None:
            cur.execute(
                """
                INSERT INTO city_locations (city, latitude, longitude)
                VALUES (%s, %s, %s)
                ON CONFLICT (city)
                DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
                """,
                (city, lat, lon),
            )
            conn.commit()
            return (lat, lon)
        return (None, None)
    finally:
        cur.close()
        conn.close()


@st.cache_data(show_spinner=False, ttl=10 * 60)
def get_weather_by_coords(lat: float, lon: float, lang: str = "pl") -> str | None:
    """
    Pogoda z Open-Meteo dla podanych współrzędnych (bez geokodowania).
    """
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "timezone": "auto",
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_weather")
        if not current:
            return None
        temp = current.get("temperature")
        wind = current.get("windspeed")
        if temp is None:
            return None
        if wind is not None:
            if lang == "pl":
                return f"{temp}°C, wiatr {wind} km/h"
            return f"{temp}°C, wind {wind} km/h"
        return f"{temp}°C"
    except requests.RequestException as err:
        logger.warning("Weather by coords failed (%s,%s): %s", lat, lon, err)
        return None


@st.cache_data(show_spinner=False, ttl=10 * 60)
def get_weather(city: str, lang: str = "pl") -> str | None:
    """
    Pogoda z Open-Meteo (bez klucza API).
    Używa resolve_city_coordinates dla lat/lon.
    Zwraca np. '7.2°C, wiatr 12 km/h' lub None.
    """
    city = (city or "").strip()
    if not city:
        return None

    lat, lon = resolve_city_coordinates(city)
    if lat is None or lon is None:
        return None

    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "timezone": "auto",
            },
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current_weather")
        if not current:
            return None

        temp = current.get("temperature")
        wind = current.get("windspeed")
        if temp is None:
            return None
        if wind is not None:
            if lang == "pl":
                return f"{temp}°C, wiatr {wind} km/h"
            return f"{temp}°C, wind {wind} km/h"
        return f"{temp}°C"
    except requests.RequestException as err:
        logger.warning("Weather fetch failed for '%s' (%s,%s): %s", city, lat, lon, err)
        return None
