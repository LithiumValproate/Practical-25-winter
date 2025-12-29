import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_engine():
    user = os.getenv("USER")
    password = os.getenv("PASSWORD")
    host = os.getenv("HOST")
    port = os.getenv("PORT")
    db = os.getenv("DB")

    return create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}")


STATION_PATH = Path("dump/station.csv")
SQL_PATH = Path("dump/china_data_insert.sql")
FIGURE_DIR = Path("Figure")
FIGURE_PNG_DIR = FIGURE_DIR / "png"
FIGURE_SVG_DIR = FIGURE_DIR / "svg"
