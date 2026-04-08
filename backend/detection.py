import os, cv2, numpy as np, base64, time, logging
from datetime import datetime
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("detection")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
MODEL_PATH = "../best.pt"

# Load YOLO model
try:
    model = YOLO(MODEL_PATH)
    try:
        model.to("cuda")
    except:
        logger.warning("CUDA not available; using CPU")
except Exception:
    model = None
    logger.exception("Failed to load YOLO model")

# memory variables
prev_rois, centers_memory, state_memory = {}, {}, {}

fgbg = cv2.createBackgroundSubtractorMOG2(
    history=200, varThreshold=20, detectShadows=False
)
time_tracker = defaultdict(
    lambda: {"last_seen": None, "working_time": 0, "idle_time": 0, "state": "INACTIVE"}
)
frame_count = 0


# --- Motion & State Helpers ---
def is_moving_roi(track_id, frame, box):
    x1, y1, x2, y2 = box
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return False

    roi = cv2.resize(roi, (96, 96))
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

    # Movement by center shift
    moving_center = False
    if track_id in centers_memory:
        px, py = centers_memory[track_id]
        if ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 > 2:
            moving_center = True
    centers_memory[track_id] = (cx, cy)

    # Background subtraction
    gray = cv2.GaussianBlur(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    fg_mask = cv2.medianBlur(fgbg.apply(gray), 5)
    moving_bg = np.sum(fg_mask > 0) / fg_mask.size > 0.015

    # Frame diff
    prev = prev_rois.get(track_id)
    prev_rois[track_id] = gray
    if prev is None:
        return moving_center or moving_bg
    if gray.shape != prev.shape:
        gray = cv2.resize(gray, (prev.shape[1], prev.shape[0]))
    diff = cv2.absdiff(prev, gray)
    moving_diff = (
        np.sum(cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)[1] > 0) / diff.size
        > 0.01
    )

    return moving_center or moving_bg or moving_diff


# for stable state (no fliking for the state changing)
def get_stable_state(track_id, moving, now):
    mem = state_memory.setdefault(track_id, {"state": "INACTIVE", "last_change": now})
    if (
        moving
        and mem["state"] == "INACTIVE"
        and (now - mem["last_change"]).total_seconds() > 0.5
    ):
        mem.update(state="ACTIVE", last_change=now)
    elif (
        not moving
        and mem["state"] == "ACTIVE"
        and (now - mem["last_change"]).total_seconds() > 0.5
    ):
        mem.update(state="INACTIVE", last_change=now)
    return mem["state"]


def classify_activity(state, name, moving):
    name = name.lower()
    if "excavator" in name:
        return (
            "Digging"
            if moving
            else ("Idle Excavator" if state == "ACTIVE" else "Waiting")
        )
    if "dump_truck" in name:
        return (
            "Dumping"
            if moving
            else ("Waiting Truck" if state == "ACTIVE" else "Waiting")
        )
    return "Moving" if moving else "Waiting"


def _clear_per_run_memory():
    prev_rois.clear()
    centers_memory.clear()
    state_memory.clear()
    time_tracker.clear()


# Main function
def run_detection_process(video_path, out_queue, stop_event):
    global frame_count
    _clear_per_run_memory()
    executor, cap = ThreadPoolExecutor(max_workers=6), cv2.VideoCapture(video_path)
    logger.info("Detection started for %s (pid=%s)", video_path, os.getpid())

    try:
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            now = datetime.now()
            events = []

            try:
                results = (
                    model.track(frame, persist=True, device=0, imgsz=416, verbose=False)
                    if model
                    else None
                )
            except:
                results = None

            active_ids = set()
            if results and results[0].boxes is not None:
                boxes = results[0].boxes.xyxy.int().cpu().numpy()
                class_ids = results[0].boxes.cls.int().cpu().numpy()
                track_ids = (
                    results[0].boxes.id.int().cpu().numpy()
                    if results[0].boxes.id is not None
                    else [-1] * len(boxes)
                )

                for box, track_id, class_id in zip(boxes, track_ids, class_ids):
                    if track_id == -1:
                        continue
                    class_name, track_id = model.names[class_id], int(track_id)
                    active_ids.add(track_id)

                    moving = (
                        is_moving_roi(track_id, frame, box)
                        if frame_count % 2 == 0
                        else state_memory.get(track_id, {}).get("state") == "ACTIVE"
                    )
                    state = get_stable_state(track_id, moving, now)
                    tracker = time_tracker[track_id]

                    # Update times
                    if tracker["last_seen"]:
                        delta = (now - tracker["last_seen"]).total_seconds()
                        if tracker["state"] == "ACTIVE":
                            tracker["working_time"] += delta
                        else:
                            tracker["idle_time"] += delta

                    tracker.update(last_seen=now, state=state)

                    total = tracker["working_time"] + tracker["idle_time"]
                    utilization = (
                        (tracker["working_time"] / total * 100) if total > 0 else 0
                    )
                    activity = classify_activity(state, class_name, moving)

                    # bbox display and text
                    color = (0, 255, 0) if state == "ACTIVE" else (0, 0, 255)
                    cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
                    cv2.putText(
                        frame,
                        f"{class_name} ID:{track_id} {state}",
                        (box[0], box[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        2,
                    )
                    cv2.putText(
                        frame,
                        f"M:{int(moving)}",
                        (box[0], box[3] + 15),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 0),
                        1,
                    )

                    event = {
                        "equipment_id": track_id,
                        "equipment_type": class_name,
                        "timestamp": now.isoformat(),
                        "state": state,
                        "activity": activity,
                        "working_time": tracker["working_time"],
                        "idle_time": tracker["idle_time"],
                        "utilization": utilization,
                    }
                    events.append(event)
                    executor.submit(lambda e=event: None)  # placeholder for DB/Kafka

            # Encode frame + push to queue
            try:
                _, buffer = cv2.imencode(".jpg", frame)
                frame_b64 = base64.b64encode(buffer).decode("utf-8")
                out_queue.put_nowait({"frame": frame_b64, "events": events})
            except:
                try:
                    out_queue.put({"frame": frame_b64, "events": events}, timeout=0.5)
                except:
                    pass

            time.sleep(0.001)

    finally:
        cap.release()
        executor.shutdown(wait=False)
        _clear_per_run_memory()
        try:
            out_queue.put(None)
        except:
            pass
        logger.info("Detection process exiting for %s", video_path)
