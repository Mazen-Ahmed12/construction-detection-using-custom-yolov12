import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # add project root

import cv2
from datetime import datetime
from ultralytics import YOLO
from kafka.producer import send_event
from db.db import insert_event
from concurrent.futures import ThreadPoolExecutor

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

MODEL_PATH = "best.pt"
VIDEO_PATH = "video.mp4"

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(VIDEO_PATH)
frame_id = 0

# Thread pool to handle Kafka + DB
executor = ThreadPoolExecutor(max_workers=10)  # adjust if needed


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

    if results and results[0].boxes is not None:
        boxes = results[0].boxes.xyxy.int().cpu().numpy()
        class_ids = results[0].boxes.cls.int().cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().numpy()

        for box, t_id, c_id in zip(boxes, track_ids, class_ids):
            x1, y1, x2, y2 = map(int, box)
            class_name = model.names[c_id]
            t_id = int(t_id)

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

            executor.submit(process_event, event)

    cv2.imshow("frame", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
executor.shutdown(wait=True)
