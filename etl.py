"""
Weather ETL pipeline
Extract -> Transform -> Validate -> Load

Pulls the last 30 days of weather for a few Indian cities from the
free Open-Meteo API, cleans it with Pandas, checks data quality,
and saves it into a SQLite database.

Run it with:  python etl.py
"""

import json
import logging
import os
import sqlite3

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------
# Settings (change these if you want)
# ---------------------------------------------------------------
CITIES = {
    "Ahmedabad": (23.03, 72.58),
    "Mumbai": (19.08, 72.88),
    "Delhi": (28.61, 77.21),
    "Chennai": (13.08, 80.27),
    "Kolkata": (22.57, 88.36),
    "Bengaluru": (12.97, 77.59),
    "Hyderabad": (17.38, 78.48),
    "Jaipur": (26.91, 75.79),
}

API_URL = "https://api.open-meteo.com/v1/forecast"
RAW_FOLDER = "raw"
DB_NAME = "weather.db"
TABLE_NAME = "daily_weather"

# Logging prints nice messages with time, so we can see what the pipeline is doing
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ---------------------------------------------------------------
# 1) EXTRACT: get raw data from the API
# ---------------------------------------------------------------
def extract():
    """Call the API for every city and return a dict: {city: raw_json}."""
    os.makedirs(RAW_FOLDER, exist_ok=True)
    raw_data = {}

    for city, (lat, lon) in CITIES.items():
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "past_days": 30,       # last 30 days
            "forecast_days": 1,    # plus today
            "timezone": "auto",
        }

        try:
            response = requests.get(API_URL, params=params, timeout=15)
            response.raise_for_status()  # raises an error if status is 4xx/5xx
            data = response.json()
        except requests.exceptions.RequestException as e:
            # If one city fails, we log it and move on instead of crashing everything
            logging.error(f"Could not fetch {city}: {e}")
            continue

        raw_data[city] = data

        # Save the untouched raw JSON (good practice: always keep the raw data)
        with open(os.path.join(RAW_FOLDER, f"{city}.json"), "w") as f:
            json.dump(data, f)

        logging.info(f"Extracted {city}")

    return raw_data


# ---------------------------------------------------------------
# 2) TRANSFORM: clean and reshape the data
# ---------------------------------------------------------------
def transform(raw_data):
    """Turn the raw JSON of all cities into one clean DataFrame."""
    frames = []

    for city, data in raw_data.items():
        # data["daily"] looks like {"time": [...], "temperature_2m_max": [...], ...}
        # so it converts straight into a table
        df_city = pd.DataFrame(data["daily"])
        df_city["city"] = city  # remember which city these rows belong to
        frames.append(df_city)

    # Stack all cities on top of each other (one row = one city on one day)
    df = pd.concat(frames, ignore_index=True)

    # Rename columns to friendlier names
    df = df.rename(columns={
        "time": "date",
        "temperature_2m_max": "temp_max",
        "temperature_2m_min": "temp_min",
        "precipitation_sum": "rain_mm",
    })

    # Fix data types
    df["date"] = pd.to_datetime(df["date"])

    # Remove duplicate rows (same city + same date)
    before = len(df)
    df = df.drop_duplicates(subset=["city", "date"])
    logging.info(f"Dropped {before - len(df)} duplicate rows")

    # Handle missing values
    # no rain data -> assume 0 mm; missing temps can't be guessed, so drop those rows
    df["rain_mm"] = df["rain_mm"].fillna(0)
    df = df.dropna(subset=["temp_max", "temp_min"])

    # New calculated columns
    df["temp_range"] = df["temp_max"] - df["temp_min"]
    df["rain_category"] = np.where(
        df["rain_mm"] > 10, "Heavy",
        np.where(df["rain_mm"] > 0, "Light", "None"),
    )

    return df


# ---------------------------------------------------------------
# 3) VALIDATE: data quality checks
# ---------------------------------------------------------------
def validate(df):
    """Run quality checks. Raises an error if something is wrong."""
    problems = []

    # Check 1: no nulls in important columns
    key_cols = ["city", "date", "temp_max", "temp_min"]
    null_count = df[key_cols].isnull().sum().sum()
    if null_count > 0:
        problems.append(f"{null_count} null values in key columns")

    # Check 2: temperatures in a sensible range
    bad_temp = df[(df["temp_max"] > 55) | (df["temp_min"] < -10)]
    if len(bad_temp) > 0:
        problems.append(f"{len(bad_temp)} rows with unrealistic temperatures")

    # Check 3: max temp should never be less than min temp
    bad_order = df[df["temp_max"] < df["temp_min"]]
    if len(bad_order) > 0:
        problems.append(f"{len(bad_order)} rows where temp_max < temp_min")

    # Check 4: rain can't be negative
    if (df["rain_mm"] < 0).any():
        problems.append("negative rain values found")

    # Check 5: no duplicate (city, date) pairs
    if df.duplicated(subset=["city", "date"]).any():
        problems.append("duplicate city+date rows found")

    # Quality report
    if problems:
        for p in problems:
            logging.error(f"Validation failed: {p}")
        raise ValueError("Data quality checks failed, not loading data.")

    logging.info(f"Validation passed: {len(df)} rows, {df['city'].nunique()} cities")
    return df


# ---------------------------------------------------------------
# 4) LOAD: save into SQLite
# ---------------------------------------------------------------
def load(df):
    """Write the clean DataFrame into a SQLite table."""
    df = df.copy()
    # SQLite has no real date type, so we store dates as text like 2026-10-03
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_NAME)
    try:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        logging.info(f"Loaded {len(df)} rows into {DB_NAME} -> table '{TABLE_NAME}'")
    finally:
        conn.close()  # always close the connection, even if something fails


# ---------------------------------------------------------------
# Run everything in order
# ---------------------------------------------------------------
def main():
    logging.info("Pipeline started")

    raw = extract()
    if not raw:
        logging.error("No data extracted, stopping.")
        return

    clean = transform(raw)
    clean = validate(clean)
    load(clean)

    logging.info("Pipeline finished successfully")


if __name__ == "__main__":
    main()