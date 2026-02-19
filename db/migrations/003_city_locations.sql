-- Cache współrzędnych miast dla stabilnych pinezek na mapie

CREATE TABLE IF NOT EXISTS city_locations (
    city       TEXT PRIMARY KEY,
    latitude   DOUBLE PRECISION NOT NULL,
    longitude  DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
