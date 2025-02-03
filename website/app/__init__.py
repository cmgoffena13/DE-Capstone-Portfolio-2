import logging
import os
from logging.handlers import TimedRotatingFileHandler

from app.blueprints import main_bp
from app.extensions import bootstrap
from config.settings import Config
from flask import Flask, render_template


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    set_logging(app=app)
    error_templates(app=app)

    extensions(app=app)
    blueprints(app=app)

    return app


def blueprints(app):
    """
    Register 0 or more blueprints (mutates the app passed in).

    :param app: Flask application instance
    :return: None
    """
    app.register_blueprint(blueprint=main_bp)
    return None


def extensions(app):
    """
    Register 0 or more extensions (mutates the app passed in).

    :param app: Flask application instance
    :return: None
    """
    bootstrap.init_app(app=app)
    return None


def error_templates(app):
    """
    Register 0 or more custom error pages (mutates the app passed in).

    :param app: Flask application instance
    :return: None
    """

    def render_status(status):
        """
        Render a custom template for a specific status.
        Source: http://stackoverflow.com/a/30108946

        :param status: Status as a written name
        :type status: str
        :return: None
        """
        # Get the status code from the status, default to a 500 so that we
        # catch all types of errors and treat them as a 500.
        code = getattr(status, "code", 500)
        return render_template(f"errors/{code}.html"), code

    for error in [404, 429, 500]:
        app.errorhandler(error)(render_status)

    return None


def set_logging(app):
    """
    Set logging handlers dependent upon log level and environment

    :param app: Flask application instance
    :return: None
    """

    if app.config["LOG_LEVEL"] == "INFO" and app.config["FLASK_ENV"] == "development":
        if not os.path.exists("logs"):
            os.mkdir("logs")
        file_handler = TimedRotatingFileHandler(
            "logs/personal-website.log", when="D", interval=1, backupCount=5, delay=True
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]",
                "%Y-%m-%dT%H:%M:%S%z",
            )
        )
        app.logger.addHandler(file_handler)

    return None
