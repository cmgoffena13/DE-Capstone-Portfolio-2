from typing import List

from confluent_kafka import Producer
from flask import current_app
from polygon.websocket.models import WebSocketMessage


class PolygonStream:
    def __init__(self, TOPIC):
        from startup import app

        self.app = app
        with self.app.app_context():
            producer_conf = {"bootstrap.servers": current_app.config["KAFKA_BROKER"]}
        self.producer = Producer(producer_conf)
        self.TOPIC = TOPIC

    def _delivery_report(self, err, m):
        if err:
            with self.app.app_context():
                current_app.logger.debug(f"Message delivery failed: {err}")
        else:
            with self.app.app_context():
                current_app.logger.debug(
                    f"Message delivered to Kafka: {m.topic()} [{m.partition()}]"
                )

    def _handle_msg(self, msg: List[WebSocketMessage]):
        for m in msg:
            with self.app.app_context():
                current_app.logger.debug(f"Received message from Polygon: {m}")
            self.producer.produce(
                self.TOPIC, m.encode("utf-8"), callback=self._delivery_report
            )
        self.producer.flush()

    def start_websocket(self, ws):
        ws.run(handle_msg=self._handle_msg)
