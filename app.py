"""
Tiny Streamlit app on top of weather.db
Run it with:  streamlit run app.py
"""

import sqlite3

import pandas as pd
import streamlit as st

st.title("Weather in Indian Cities (last 30 days)")

# Connect to the database that etl.py created
conn = sqlite3.connect("weather.db")

# Get the list of cities for the dropdown
cities = pd.read_sql("SELECT DISTINCT city FROM daily_weather ORDER BY city", conn)["city"].tolist()
city = st.selectbox("Pick a city", cities)

# The user just picks a city; the SQL runs behind the scenes
# The ? is a placeholder, it gets replaced safely with the chosen city
df = pd.read_sql(
    "SELECT date, temp_max, temp_min, rain_mm FROM daily_weather WHERE city = ? ORDER BY date",
    conn,
    params=(city,),
)
conn.close()

# Quick summary numbers
col1, col2, col3 = st.columns(3)
col1.metric("Hottest day (°C)", round(df["temp_max"].max(), 1))
col2.metric("Coldest night (°C)", round(df["temp_min"].min(), 1))
col3.metric("Total rain (mm)", round(df["rain_mm"].sum(), 1))

# Charts
st.subheader("Temperature")
st.line_chart(df.set_index("date")[["temp_max", "temp_min"]])

st.subheader("Rainfall")
st.bar_chart(df.set_index("date")["rain_mm"])

# Raw table
st.subheader("Data")
st.dataframe(df)

st.caption("Weather data by Open-Meteo.com")