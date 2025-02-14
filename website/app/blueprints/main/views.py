import asyncio

from app.blueprints.main.forms import NewsForm, TickerForm
from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from polygon import WebSocketClient
from scripts.producer import GuardianAPI, PolygonStream

main_bp = Blueprint(name="main", import_name=__name__, template_folder="templates")


ws_instance = None


@main_bp.route("/index", methods=["GET", "POST"])
@main_bp.route("/", methods=["GET", "POST"])
def index():
    tickers_form = TickerForm()
    news_form = NewsForm()
    global ws_instance
    if tickers_form.validate_on_submit():
        tickers = tickers_form.tickers.data.split(",")
        formatted_tickers = ["AM." + ticker.strip() for ticker in tickers]
        try:
            if ws_instance:
                current_app.logger.debug("Stopping Polygon Stream...")
                asyncio.ensure_future(
                    ws_instance.close()
                )  # close method is asynchronous

            ws_instance = WebSocketClient(
                api_key=current_app.config["POLYGON_API_KEY"],
                subscriptions=formatted_tickers,
                feed="delayed.polygon.io",
            )

            s = PolygonStream(TOPIC="stock-prices")
            s.start_websocket(ws=ws_instance)
            flash("Tracking started successfully!", "success")
        except Exception as e:
            flash("Failed to start tracking. Please try again later.", "danger")
            current_app.logger.debug(f"Failed to start Polygon Stream: {e}")
        return redirect(url_for("main.index"))

    if news_form.validate_on_submit():
        search = news_form.news.data
        try:
            s = GuardianAPI(TOPIC="news-articles", SEARCH=search)
            s.start_api_stream()
            flash("Tracking started successfully!", "success")
        except Exception as e:
            flash("Failed to start tracking. Please try again later.", "danger")
            current_app.logger.debug(f"Failed to start Guardian Stream: {e}")
        return redirect(url_for("main.index"))

    return render_template(
        template_name_or_list="main/index.html",
        tickers_form=tickers_form,
        news_form=news_form,
    )
