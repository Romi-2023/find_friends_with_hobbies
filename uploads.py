# uploads.py – zapis plików do galerii klubów
"""
Zapisywanie wgranych plików (zdjęcia/wideo) do katalogu mediów.
Zwraca (path, media_type) lub (None, None) przy błędzie.
Błędy walidacji: wywołujący powinien wyświetlić st.error(t("file_type_not_allowed")) itd.
"""

import mimetypes
import os
import pathlib
import uuid

import config


ALLOWED_TYPES = {"image/jpeg", "image/png", "video/mp4"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def save_upload(file, club_id: int):
    """
    Zapisuje plik do config.MEDIA_DIR.
    Zwraca (path, media_type) lub (None, None).
    Wywołujący sprawdza: jeśli path is None, sprawdź file.type / file.size i pokaż t("file_type_not_allowed") / t("file_too_large").
    """
    if file.type not in ALLOWED_TYPES:
        return None, None  # caller: st.error(t("file_type_not_allowed"))

    if file.size > MAX_FILE_SIZE:
        return None, None  # caller: st.error(t("file_too_large"))

    os.makedirs(config.MEDIA_DIR, exist_ok=True)
    ext = mimetypes.guess_extension(file.type) or pathlib.Path(file.name).suffix.lower()
    uid = uuid.uuid4().hex
    safe_name = f"{club_id}_{uid}{ext}"
    path = os.path.join(config.MEDIA_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(file.read())
    media_type = "video" if file.type.startswith("video") else "image"
    return path, media_type
