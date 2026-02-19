# Find Friends with Hobbies – wdrożenie na DO App Platform (PostgreSQL z DO)
FROM python:3.12-slim

WORKDIR /app

# Zależności systemowe (opcjonalnie dla Pillow/geopy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DigitalOcean App Platform ustawia zmienną PORT
ENV PORT=8080
EXPOSE 8080

# Streamlit nasłuchuje na 0.0.0.0 i porcie z ENV
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
