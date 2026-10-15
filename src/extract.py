from pathlib import Path
import requests
from .config import BASE_URL, DATA_DIR, MONTHS
from .logging_config import get_logger
log = get_logger(__name__)

def download_month(month: str) -> Path:
    if month not in MONTHS:
        raise ValueError(f"Unsupported month: {month}")
    folder = DATA_DIR / "raw"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"yellow_tripdata_{month}.parquet"
    if target.is_file() and target.stat().st_size > 1024:
        log.info(f"Cached source: {target}")
        return target
    url = f"{BASE_URL}/{target.name}"
    temp = target.with_suffix(".partial")
    try:
        with requests.get(url, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            with temp.open("wb") as fh:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        fh.write(block)
        if temp.stat().st_size < 1024:
            raise RuntimeError("Downloaded file unexpectedly small")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    log.info(f"Downloaded {target.name}: {target.stat().st_size} bytes")
    return target

def download_all():
    return [download_month(m) for m in MONTHS]
