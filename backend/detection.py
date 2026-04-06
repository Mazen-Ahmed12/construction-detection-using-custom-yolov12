import os
import cv2
import base64
from datetime import datetime
from ultralytics import YOLO
from kafka_producer import send_event
from db import insert_event
from concurrent.futures import ThreadPoolExecutor

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
MODEL_PATH = "../best.pt"
executor = ThreadPoolExecutor(max_workers=10)
model = YOLO(MODEL_PATH)


async def start_detection_for_video(video_path, clients):
    """Process video, send frames+events to WebSocket clients and Kafka/Postgres"""
    import asyncio

    cap = cv2.VideoCapture(video_path)
    frame_id = 0

    def process_event(event):
        send_event(event)
        insert_event(event)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_id += 1
        timestamp = datetime.now().isoformat(timespec="milliseconds")

        results = model.track(frame, persist=True)
        events = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.int().cpu().numpy()
            class_ids = results[0].boxes.cls.int().cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()

            for box, t_id, c_id in zip(boxes, track_ids, class_ids):
                x1, y1, x2, y2 = map(int, box)
                class_name = model.names[c_id]
                t_id = int(t_id)

                # Draw bounding box on frame
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{class_name} ID:{t_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

                event = {
                    "frame_id": frame_id,
                    "equipment_id": t_id,
                    "equipment_type": class_name,
                    "timestamp": timestamp,
                    "state": "ACTIVE",
                    "activity": "working",
                    "motion_source": "global_motion",
                }
                events.append(event)
                executor.submit(process_event, event)

        # encode frame to base64
        _, buffer = cv2.imencode(".jpg", frame)
        frame_b64 = base64.b64encode(buffer).decode("utf-8")

        # send to all WebSocket clients
        if clients:
            frame_data = {"frame_id": frame_id, "frame": frame_b64, "events": events}
            for ws in clients:
                try:
                    await ws.send_json(frame_data)
                except:
                    pass

        await asyncio.sleep(0.01)  # small delay to allow event loop

    cap.release()
