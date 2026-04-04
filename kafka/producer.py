from confluent_kafka import Producer
import json

producer = Producer({"bootstrap.servers": "localhost:9092"})


def send_event(event: dict):
    # Convert dict to JSON string
    value = json.dumps(event)
    producer.produce(
        "equipment_events", key=str(event.get("equipment_id")), value=value
    )
    producer.flush()
