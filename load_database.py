import os

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
