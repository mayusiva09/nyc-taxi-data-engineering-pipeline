from src.transform import REQUIRED
from src.config import MONTHS

def test_expected_source_fields():
    assert "trip_distance" in REQUIRED
    assert "tpep_pickup_datetime" in REQUIRED

def test_two_months_configured():
    assert MONTHS == ("2023-01", "2023-02")
