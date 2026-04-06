from confluent_kafka import Producer
import json

producer = Producer({"bootstrap.servers": "localhost:9092"})


def send_event(event):
    producer.produce(
        "equipment_events",
        key=str(event["equipment_id"]),
        value=json.dumps(event),
    )
    producer.flush()
