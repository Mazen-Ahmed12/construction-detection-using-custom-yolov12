import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
from ultralytics import YOLO

# ===============================
# CONFIG
# ===============================
MODEL_PATH = "best.pt"
VIDEO_PATH = "video.mp4"

# ===============================
# LOAD MODEL
# ===============================
model = YOLO(MODEL_PATH)

# ===============================
# VIDEO LOOP
# ===============================
cap = cv2.VideoCapture(VIDEO_PATH)
frame_id = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_id += 1

    # ===============================
    # YOLO TRACKING
    # ===============================
    results = model.track(frame, persist=True)

    if results and results[0].boxes is not None and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.int().cpu().numpy()
        ids = results[0].boxes.id.int().cpu().numpy()
        classes = results[0].boxes.cls.int().cpu().numpy()

        for box, track_id, cls in zip(boxes, ids, classes):
            x1, y1, x2, y2 = map(int, box)  # ensure integer coordinates
            cls = int(cls)
            equipment_class = results[0].names[cls]

            # === DRAW BOUNDING BOX ===
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # === LABEL: CLASS NAME + ID BESIDE IT (exactly what you asked for) ===
            label = f"{equipment_class} ID:{track_id}"

            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,  # slightly bigger for better readability
                (0, 255, 0),
                2,
            )

    cv2.imshow("YOLO Tracking - ID Beside Class", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
