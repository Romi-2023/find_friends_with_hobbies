# Find Friends with Hobbies

Aplikacja społecznościowa do znajdowania osób o podobnych zainteresowaniach: kluby, wydarzenia, wiadomości, rekomendacje.

- **Repo:** [github.com/Romi-2023/find_friends_with_hobbies](https://github.com/Romi-2023/find_friends_with_hobbies)
- **Stack:** Python, Streamlit, PostgreSQL (lub SQLite), bcrypt, Folium
- **Wdrożenie:** Dockerfile + [DEPLOY.md](DEPLOY.md) – DigitalOcean App Platform

## Live demo
- https://find-friend-with-hobby-app-9smie.ondigitalocean.app/

## Portfolio page
- https://romi-2023.github.io/knopp_roman_portfolio/ongoing/find_friends_with_hobbies/

## Licencja

[Wszelkie prawa zastrzeżone](LICENSE) – kod jest własnością autora. Użycie, modyfikacja i rozpowszechnianie bez zezwolenia są zabronione.

## Uruchomienie lokalne

```bash
pip install -r requirements.txt
# Ustaw .env (np. USE_SQLITE=1 do testów)
streamlit run app.py
```

---

## 1. Wypchnięcie na GitHub

Repozytorium: `https://github.com/Romi-2023/find_friends_with_hobbies.git`

**Żeby DigitalOcean mógł zbudować aplikację z repo, repozytorium musi być publiczne.**  
W GitHubie: **Settings** → na dole **Danger Zone** → **Change repository visibility** → **Make public**.

Wypchnij kod:

```bash
git add .
git status   # upewnij się, że NIE ma .env (jest w .gitignore)
git commit -m "Aplikacja Find Friends with Hobbies – gotowa do wdrożenia"
git push origin main
```

**Uwaga:** Plik `.env` nie trafi do repo (jest w `.gitignore`). Na DO ustawisz zmienne w panelu.

---

## 2. Wdrożenie na DigitalOcean

1. **Apps** → **Create App** → wybierz źródło **GitHub** i to repozytorium (branch `main`).
2. **Build:** wykryty Dockerfile – zostaw domyślne.
3. **Environment Variables** (obowiązkowe):
   - `DATABASE_URL` – connection string do Twojej bazy PostgreSQL na DO
   - `USE_SQLITE=0`
   - `APP_PUBLIC_URL` – URL aplikacji (np. `https://twoja-app-xxxx.ondigitalocean.app`) – możesz ustawić po pierwszym deployu
4. **Deploy** – po zbudowaniu aplikacja będzie dostępna pod podanym adresem.

Szczegóły (mail, TOTP, OpenCage): [DEPLOY.md](DEPLOY.md).
