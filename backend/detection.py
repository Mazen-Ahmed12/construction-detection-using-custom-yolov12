import os
import cv2
import base64
from datetime import datetime
from ultralytics import YOLO
from kafka_producer import send_event
from db import insert_event
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

MODEL_PATH = "../best.pt"
model = YOLO(MODEL_PATH)

executor = ThreadPoolExecutor(max_workers=10)

# =========================
# MEMORY STORAGE
# =========================
prev_rois = {}
state_memory = {}

time_tracker = defaultdict(
    lambda: {"last_seen": None, "working_time": 0, "idle_time": 0}
)


# =========================
# ROI MOTION DETECTION
# =========================
def is_moving_roi(track_id, frame, box):
    x1, y1, x2, y2 = box

    # crop ROI
    roi = frame[y1:y2, x1:x2]

    if roi.size == 0:
        return False

    # grayscale + blur (reduce noise)
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    roi_gray = cv2.GaussianBlur(roi_gray, (5, 5), 0)

    if track_id not in prev_rois:
        prev_rois[track_id] = roi_gray
        return False

    prev = prev_rois[track_id]

    # resize to match previous ROI
    roi_gray = cv2.resize(roi_gray, (prev.shape[1], prev.shape[0]))

    # difference
    diff = cv2.absdiff(prev, roi_gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    motion_score = thresh.sum() / 255

    prev_rois[track_id] = roi_gray

    # 🔥 Tune this if needed
    return motion_score > 500


# =========================
# STATE SMOOTHING
# =========================
def get_stable_state(track_id, moving):
    if track_id not in state_memory:
        state_memory[track_id] = {"count": 0, "state": "INACTIVE"}

    mem = state_memory[track_id]

    if moving:
        mem["count"] += 1
    else:
        mem["count"] -= 1

    # clamp range
    mem["count"] = max(-5, min(5, mem["count"]))

    # decision logic
    if mem["count"] > 2:
        state = "ACTIVE"
    elif mem["count"] < -2:
        state = "INACTIVE"
    else:
        state = mem["state"]

    mem["state"] = state
    return state


# =========================
# ACTIVITY CLASSIFICATION
# =========================
def classify_activity(state, class_name):
    if state == "INACTIVE":
        return "Waiting"

    name = class_name.lower()

    if "excavator" in name:
        return "Digging"
    elif "truck" in name:
        return "Dumping"
    elif "loader" in name:
        return "Loading"

    return "Moving"


# =========================
# MAIN DETECTION FUNCTION
# =========================
async def start_detection_for_video(video_path, clients):
    import asyncio

    cap = cv2.VideoCapture(video_path)

    def process_event(event):
        send_event(event)
        insert_event(event)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = datetime.now()
        events = []

        results = model.track(frame, persist=True)

        if results and results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.int().cpu().numpy()
            class_ids = results[0].boxes.cls.int().cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()

            for box, t_id, c_id in zip(boxes, track_ids, class_ids):
                x1, y1, x2, y2 = map(int, box)
                class_name = model.names[c_id]
                t_id = int(t_id)

                # =========================
                # NEW MOTION LOGIC
                # =========================
                moving = is_moving_roi(t_id, frame, box)
                state = get_stable_state(t_id, moving)

                # =========================
                # ACTIVITY
                # =========================
                activity = classify_activity(state, class_name)

                # =========================
                # TIME TRACKING
                # =========================
                tracker = time_tracker[t_id]

                if tracker["last_seen"]:
                    delta = (now - tracker["last_seen"]).total_seconds()

                    if state == "ACTIVE":
                        tracker["working_time"] += delta
                    else:
                        tracker["idle_time"] += delta

                tracker["last_seen"] = now

                total = tracker["working_time"] + tracker["idle_time"]
                utilization = (
                    (tracker["working_time"] / total) * 100 if total > 0 else 0
                )

                # =========================
                # DRAW UI
                # =========================
                color = (0, 255, 0) if state == "ACTIVE" else (0, 0, 255)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame,
                    f"{class_name} ID:{t_id} {state}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

                # =========================
                # EVENT
                # =========================
                event = {
                    "equipment_id": t_id,
                    "equipment_type": class_name,
                    "timestamp": now.isoformat(),
                    "state": state,
                    "activity": activity,
                    "working_time": tracker["working_time"],
                    "idle_time": tracker["idle_time"],
                    "utilization": utilization,
                }

                events.append(event)
                executor.submit(process_event, event)

        # =========================
        # SEND FRAME
        # =========================
        _, buffer = cv2.imencode(".jpg", frame)
        frame_b64 = base64.b64encode(buffer).decode("utf-8")

        if clients:
            data = {"frame": frame_b64, "events": events}
            for ws in clients:
                try:
                    await ws.send_json(data)
                except:
                    pass

        await asyncio.sleep(0.03)

    cap.release()
