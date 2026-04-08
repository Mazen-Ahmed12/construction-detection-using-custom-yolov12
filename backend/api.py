import os, shutil, asyncio, logging
from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from multiprocessing import Process, Queue, Event
import detection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

UPLOAD_FOLDER = "temp_videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

clients = []
app.state.current_detection_proc = None
app.state.current_queue = None
app.state.current_stop_event = None
app.state.queue_forwarder_task = None


async def _queue_forwarder(queue: Queue):
    loop = asyncio.get_event_loop()
    while True:
        try:
            data = await loop.run_in_executor(None, queue.get)
        except Exception:
            await asyncio.sleep(0.01)
            continue
        if data is None:
            break
        for ws in list(clients):
            try:
                await ws.send_json(data)
            except:
                pass


def _stop_previous_process():
    proc, queue, event, forwarder = (
        app.state.current_detection_proc,
        app.state.current_queue,
        app.state.current_stop_event,
        app.state.queue_forwarder_task,
    )
    if proc and proc.is_alive():
        logger.info("Stopping previous detection process pid=%s", proc.pid)
        event.set()
        proc.join(timeout=4)
        if proc.is_alive():
            logger.warning("Force terminating pid=%s", proc.pid)
            proc.terminate()
            proc.join(timeout=2)
    if queue:
        try:
            queue.put(None)
        except:
            pass
    if forwarder:
        try:
            forwarder.cancel()
        except:
            pass


@app.post("/upload")
async def upload_video(file: UploadFile):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    _stop_previous_process()

    queue, stop_event = Queue(maxsize=10), Event()
    proc = Process(
        target=detection.run_detection_process,
        args=(file_path, queue, stop_event),
        daemon=True,
    )
    proc.start()
    forwarder_task = asyncio.create_task(_queue_forwarder(queue))

    app.state.current_detection_proc, app.state.current_queue = proc, queue
    app.state.current_stop_event, app.state.queue_forwarder_task = (
        stop_event,
        forwarder_task,
    )

    return {"status": "started", "file": file.filename, "pid": proc.pid}


@app.websocket("/ws/video")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in clients:
            clients.remove(websocket)
