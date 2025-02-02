import os
from os.path import abspath, dirname, join

from dotenv import load_dotenv

base_dir = abspath(dirname(dirname(__file__)))
load_dotenv(join(base_dir, ".env"))
load_dotenv(join(base_dir, ".flaskenv"))


class Config(object):
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG")
    FLASK_ENV = os.environ.get("FLASK_ENV")
    FLASK_APP = os.environ.get("FLASK_APP", "startup.py")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")
    SECRET_KEY = os.environ.get("SECRET_KEY", "12345")

    POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY")

    KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
