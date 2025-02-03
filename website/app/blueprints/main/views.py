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
                ws_instance.stop()

            ws_instance = WebSocketClient(
                api_key=current_app.config["POLYGON_API_KEY"],
                subscriptions=formatted_tickers,
                feed="delayed.polygon.io",
            )

            s = PolygonStream(TOPIC="stock-prices")
            s.start_websocket(ws=ws_instance)
            flash("Tracking started successfully!", "success")
        except Exception:
            flash("Failed to start tracking. Please try again later.", "danger")
        return redirect(url_for("main.index"))

    if news_form.validate_on_submit():
        search = news_form.news.data
        try:
            GuardianAPI(TOPIC="news-articles", SEARCH=search)
            GuardianAPI.start_api_stream()
            flash("Tracking started successfully!", "success")
        except Exception:
            flash("Failed to start tracking. Please try again later.", "danger")
        return redirect(url_for("main.index"))

    return render_template(
        template_name_or_list="main/index.html",
        tickers_form=tickers_form,
        news_form=news_form,
    )
