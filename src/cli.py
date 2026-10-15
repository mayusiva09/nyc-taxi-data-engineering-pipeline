import argparse
from .extract import download_all
from .transform import transform
from .load import load, quality_checks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["download", "transform", "load", "check", "run"])
    command = parser.parse_args().command
    if command in ("download", "run"): download_all()
    if command in ("transform", "run"): transform()
    if command in ("load", "run"): load()
    if command in ("check", "run"): quality_checks()
if __name__ == "__main__": main()
