# Weather ETL Pipeline

I built this small project to learn how ETL pipelines actually work. It pulls the last 30 days of weather for 8 Indian cities, cleans the data, checks its quality, and stores it in a SQLite database that I can then query with SQL.

## What it does

1. **Extract**: calls the free Open-Meteo API with `requests` for 8 cities (Ahmedabad, Mumbai, Delhi, Chennai, Kolkata, Bengaluru, Hyderabad, Jaipur) and saves the raw JSON in `raw/`.
2. **Transform**: uses Pandas to combine everything into one table, fix column names and date types, remove duplicates, handle missing values, and add two new columns (`temp_range` and `rain_category`).
3. **Validate**: runs 5 quality checks (nulls, unrealistic temperatures, max temp lower than min temp, negative rain, duplicate city+date rows). If any check fails, nothing gets loaded.
4. **Load**: saves the clean data into `weather.db` (table: `daily_weather`).

## Tech used

Python, Pandas, NumPy, Requests, SQLite, Streamlit (for the small dashboard)

## Project files

- `etl.py`: the main pipeline
- `queries.sql`: SQL queries I wrote to ask questions about the data
- `app.py`: small Streamlit dashboard on top of the database
- `requirements.txt`: libraries needed

## How to run it

```bash
pip install -r requirements.txt
python etl.py
```

This creates `weather.db` and a `raw/` folder.

To open the dashboard (run `etl.py` first, because the app needs the database):

```bash
streamlit run app.py
```

## SQL queries

`queries.sql` has 6 queries I wrote on the loaded data, like:
- average max temp per city
- hottest day for each city (window function)
- cities with more than 50 mm total rain (`GROUP BY` + `HAVING`)
- 3-day moving average of temperature

## What I learned

- ETL is basically getting messy data from somewhere, cleaning it, checking it, and storing it so other people can use it. Doing it myself made it way clearer than just reading about it.
- Validation is important. Adding checks means bad data gets caught before it reaches the database.
- I also learned to keep the raw data untouched in `raw/`, so I can always re-run the cleaning if something goes wrong.
- Next I want to schedule it to run daily and try a bigger dataset.

## Data credit

Weather data by [Open-Meteo.com](https://open-meteo.com/).