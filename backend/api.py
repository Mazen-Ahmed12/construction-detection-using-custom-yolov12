import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from detection import start_detection_for_video

UPLOAD_FOLDER = "temp_videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients
clients = []


@app.post("/upload")
async def upload_video(file: UploadFile):
    """Upload video and start detection"""
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Start detection for this uploaded video
    asyncio.create_task(start_detection_for_video(file_path, clients))

    return {"filename": file.filename, "path": file_path}


@app.websocket("/ws/video")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for sending frames + events"""
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        clients.remove(websocket)
