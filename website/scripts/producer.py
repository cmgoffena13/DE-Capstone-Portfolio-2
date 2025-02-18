import threading
import time
from datetime import date, datetime, timezone
from typing import List

from confluent_kafka import Producer
from flask import current_app
from polygon.websocket.models import WebSocketMessage
from scripts.utils import (
    EquityAgg,
    article_to_json,
    dict_to_article,
    equity_agg_to_json,
    fetch_with_retries,
    read_config,
)


class PolygonStream:
    def __init__(self, TOPIC):
        from startup import app

        self.app = app
        with self.app.app_context():
            current_app.logger.info("Initializing PolygonStream")
            if current_app.config["LOCAL"] == 1:
                producer_conf = {
                    "bootstrap.servers": current_app.config["KAFKA_BROKER"]
                }
                current_app.logger.info("Local Config Initialized")
            else:
                producer_conf = read_config()
                current_app.logger.info(
                    f"Confluent Config Initialized: {producer_conf}"
                )
        self.producer = Producer(producer_conf)
        self.TOPIC = TOPIC

    def _delivery_report(self, err, m):
        if err:
            with self.app.app_context():
                current_app.logger.info(f"Message delivery failed: {err}")
        else:
            with self.app.app_context():
                current_app.logger.info(
                    f"Message delivered to Kafka. Topic: {m.topic()}; Partition: {m.partition()}; "
                    f"Key: {m.key()}; Message: {m.value()}"
                )

    def _handle_msg(self, msg: List[WebSocketMessage]):
        for m in msg:
            self.producer.produce(
                self.TOPIC,
                key=m.symbol.encode("utf-8"),
                value=equity_agg_to_json(EquityAgg(**m.__dict__)),
                callback=self._delivery_report,
            )
        self.producer.flush()

    def start_websocket(self, ws):
        def run_ws():
            with self.app.app_context():
                current_app.logger.info("Starting Polygon Stream...")
            ws.run(handle_msg=self._handle_msg)

        threading.Thread(target=run_ws).start()
        with self.app.app_context():
            current_app.logger.info("Polygon Stream Started")


class GuardianAPI:
    def __init__(self, TOPIC, SEARCH):
        from startup import app

        self.app = app
        with self.app.app_context():
            current_app.logger.info("Initializing GuardianAPI Stream")
            if current_app.config["LOCAL"] == 1:
                producer_conf = {
                    "bootstrap.servers": current_app.config["KAFKA_BROKER"]
                }
            else:
                producer_conf = read_config()
            self.GUARDIAN_API_KEY = current_app.config["GUARDIAN_API_KEY"]
        self.producer = Producer(producer_conf)
        self.api_url = "https://content.guardianapis.com/search"
        self.TOPIC = TOPIC
        self.SEARCH = SEARCH
        self.payload = {
            "api-key": self.GUARDIAN_API_KEY,
            "page-size": 10,
            "section": "us-news",
            "q": self.SEARCH,
            "from-date": date.today().strftime("%Y-%m-%d"),
            "page": 1,
            "order-by": "oldest",
        }

    def _delivery_report(self, err, m):
        if err:
            with self.app.app_context():
                current_app.logger.info(f"Message delivery failed: {err}")
        else:
            with self.app.app_context():
                current_app.logger.info(
                    f"Message delivered to Kafka. Topic: {m.topic()}; Partition: {m.partition()}; "
                    f"Key: {m.key()}; Message: {m.value()}"
                )

    def _update_date(self):
        formatted_date = date.today().strftime("%Y-%m-%d")
        self.payload["from-date"] = formatted_date

    def start_api_stream(self):
        def loop_api():
            # Initialize watermark so we don't add messages before the date.
            watermark = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            with self.app.app_context():
                current_app.logger.info("Starting Guardian Stream...")
            # Start an infinite loop
            while True:
                data = fetch_with_retries(url=self.api_url, params=self.payload)
                records = data["response"]["results"]

                for record in records:
                    timestamp = datetime.strptime(
                        record["webPublicationDate"], "%Y-%m-%dT%H:%M:%SZ"
                    ).replace(tzinfo=timezone.utc)
                    if timestamp > watermark:
                        watermark = timestamp
                        record["search"] = self.SEARCH
                        article = dict_to_article(
                            record=record
                        )  # convert to dataclass and validate
                        self.producer.produce(
                            self.TOPIC,
                            key=self.SEARCH.encode("utf-8"),
                            value=article_to_json(article=article),
                            callback=self._delivery_report,
                        )
                self.producer.flush()

                current_page = data["response"]["currentPage"]
                total_pages = data["response"]["pages"]

                # Loop through the pages
                while current_page < total_pages:
                    current_page += 1
                    with self.app.app_context():
                        current_app.logger.info(
                            f"API Call Current Page: {current_page}"
                        )
                    self.payload["page"] = current_page

                    data = fetch_with_retries(url=self.api_url, params=self.payload)
                    records = data["response"]["results"]

                    for record in records:
                        timestamp = datetime.strptime(
                            record["webPublicationDate"], "%Y-%m-%dT%H:%M:%SZ"
                        ).replace(tzinfo=timezone.utc)
                        if timestamp > watermark:
                            watermark = timestamp
                            record["search"] = self.SEARCH
                            article = dict_to_article(
                                record=record
                            )  # convert to dataclass and validate
                            self.producer.produce(
                                self.TOPIC,
                                key=self.SEARCH,
                                value=article_to_json(article=article),
                                callback=self._delivery_report,
                            )
                    self.producer.flush()
                time.sleep(60)
                self._update_date()

        threading.Thread(target=loop_api).start()
        with self.app.app_context():
            current_app.logger.info("Guardian Stream Started")
