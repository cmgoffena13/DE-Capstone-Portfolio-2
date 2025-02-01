from confluent_kafka import Producer
import time
import os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "test-topic-2"

producer_conf = {"bootstrap.servers": KAFKA_BROKER}
producer = Producer(producer_conf)

def delivery_report(err, msg):
    if err:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

for i in range(10):
    message = f"Message {i}"
    producer.produce(TOPIC, message.encode("utf-8"), callback=delivery_report)
    producer.flush()
    time.sleep(1)

print("Finished producing messages.")