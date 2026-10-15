import os
import pandas as pd
import psycopg
import streamlit as st

st.set_page_config(page_title="NYC Taxi Analytics", layout="wide")
st.title("NYC Yellow Taxi Analytics")
st.caption("Data: January–February 2023. Total charges exclude unrecorded cash tips.")
URL = os.environ["TAXI_DATABASE_URL"]

@st.cache_data(ttl=60)
def query(sql, params=()):
    with psycopg.connect(URL) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return pd.DataFrame(cur.fetchall(), columns=[x.name for x in cur.description])

month = st.selectbox("Pickup month", ["All months", "January 2023", "February 2023"])

filter_sql = {"All months":"TRUE", "January 2023":"pickup_date_key BETWEEN 20230101 AND 20230131", "February 2023":"pickup_date_key BETWEEN 20230201 AND 20230228"}[month]
try:
    stats = query(f"""SELECT count(*) AS trips, coalesce(sum(total_amount),0) AS charges,
        round((sum(fare_amount)/nullif(sum(trip_distance),0))::numeric,2) AS fare_per_mile
        FROM fact_taxi_trips WHERE {filter_sql}""").iloc[0]
    a,b,c = st.columns(3)
    a.metric("Trips", f"{stats['trips']:,}")
    b.metric("Total recorded charges", f"${stats['charges']:,.2f}")
    c.metric("Distance-weighted fare / mile", f"${stats['fare_per_mile'] or 0}")
    st.subheader("Peak pickup hours")
    hours=query(f"SELECT pickup_hour, count(*) AS trips FROM fact_taxi_trips WHERE {filter_sql} GROUP BY 1 ORDER BY 1")
    if not hours.empty:
        st.bar_chart(hours.set_index("pickup_hour"))
    st.subheader("Total recorded charges by payment type")
    pay=query(f"""SELECT p.payment_name, sum(f.total_amount)::float AS revenue
        FROM fact_taxi_trips f JOIN dim_payment p ON p.payment_key=f.payment_key
        WHERE {filter_sql.replace('pickup_date_key','f.pickup_date_key')}
        GROUP BY p.payment_name ORDER BY revenue DESC""")
    if not pay.empty:
        st.bar_chart(pay.set_index("payment_name"))
except psycopg.Error as exc:
    st.error("Database is not ready. Run the ETL DAG and refresh this page.")
    st.caption(type(exc).__name__)
