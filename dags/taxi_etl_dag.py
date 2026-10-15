from datetime import datetime, timedelta
from airflow.decorators import dag, task
from src.extract import download_all
from src.transform import transform
from src.load import load, quality_checks

@dag(
    dag_id="nyc_yellow_taxi_batch_etl",
    start_date=datetime(2023, 3, 1),
    schedule=None,
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
    tags=["nyc-taxi", "batch-etl"],
)
def taxi_pipeline():
    @task
    def download():
        return [str(x) for x in download_all()]
    @task
    def clean(_files):
        return transform()
    @task
    def warehouse(_rows):
        return load()
    @task
    def check(_inserted):
        return quality_checks()
    check(warehouse(clean(download())))

taxi_pipeline()
