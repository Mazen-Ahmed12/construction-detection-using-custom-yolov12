Equipment Utilization & Activity Classification Prototype
=========================================================

📌 Overview
-----------

This project demonstrates a **real-time, microservices-based pipeline** for analyzing construction equipment utilization using **computer vision** and a **distributed backend architecture**. It tracks equipment states (ACTIVE/INACTIVE), classifies activities (Digging, Swinging/Loading, Dumping, Waiting), and calculates utilization metrics. Results are streamed via **Kafka** and displayed in a simple dashboard UI.

⚙️ Features
-----------

*   **Computer Vision (YOLO + Motion Analysis)**
    
    *   Detects equipment (excavators, dump trucks, etc.)
        
    *   Classifies ACTIVE vs INACTIVE states
        
    *   Handles articulated motion (e.g., excavator arm moving while tracks are stationary)
        
    *   Activity classification: Digging, Dumping, Waiting, Moving
        
*   **Analytics Backend**
    
    *   FastAPI microservice for video uploads and WebSocket streaming
        
    *   PostgreSQL database for event storage
        
    *   Kafka for distributed messaging
        
*   **Frontend Dashboard (React/Streamlit)**
    
    *   Displays processed video frames with bounding boxes
        
    *   Shows live machine states and activities
        
    *   Utilization dashboard with working/idle time counters
        

🏗️ Architecture Overview
-------------------------

### Docker Compose Services

ServicePurpose**Zookeeper**Coordinates Kafka brokers**Kafka**Message broker for streaming CV results**Postgres**Stores equipment events and utilization metrics**FastAPI Service**Handles video uploads, runs detection, streams results**Frontend (React/Streamlit)**Displays processed video feed and utilization dashboard

### Data Flow

1.  **Video Upload** → FastAPI receives video and spawns detection process.
    
2.  **Detection Service** → YOLO + motion analysis classify states/activities.
    
3.  **Kafka Payloads** → JSON messages with frame, state, activity, and utilization.
    
4.  **Database Sink** → PostgreSQL stores events.
    
5.  **Frontend UI** → WebSocket stream updates dashboard in real-time.
    

🚀 Setup Instructions
---------------------

### 1\. Clone Repository

```bash

git clone https://github.com/Mazen-Ahmed12/construction-detection-using-custom-yolov12.git
cd construction-detection-using-custom-yolov12
```
### 2\. Start Services
```
bash

docker-compose up -d 
```
This spins up **Kafka, Zookeeper, and PostgreSQL**.

### 3\. Install Python Dependencies
```
bash

pip install -r requirements.txt
```
### 4\. Run FastAPI Backend
```
bash

uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
### 5\. Run Frontend

If using React:

``` bash

cd frontend  npm install  npm start 
```

🧩 Design Decisions & Trade-offs
--------------------------------

### 1\. **Articulated Motion Challenge**

*   Problem: Excavators can be ACTIVE even if only the arm moves while tracks remain stationary.
    
*   Solution:
    
    *   **Region-based motion analysis**: Each ROI (bounding box) is checked for movement.
        
    *   **Hybrid detection**: Combines center-shift tracking, background subtraction, and frame differencing.
        
    *   **Stable state memory**: Prevents flickering by requiring sustained motion before switching states.
        
*   Trade-off: Slight delay (~0.5s) in state transitions for stability, but avoids false positives.
    

### 2\. **Activity Classification**

*   Excavators:
    
    *   Moving → **Digging**
        
    *   Active but not moving → **Idle Excavator**
        
    *   Inactive → **Waiting**
        
*   Dump Trucks:
    
    *   Moving → **Dumping**
        
    *   Active but not moving → **Waiting Truck**
        
    *   Inactive → **Waiting**
        
        

This rule-based classification is lightweight and interpretable, though less flexible than deep activity recognition models.

### 3\. **Backend Architecture**

*   **FastAPI + Multiprocessing**: Each video runs in its own detection process for isolation.
    
*   **Kafka**: Ensures scalability and decoupling between CV microservice and UI/database.
    
*   **PostgreSQL**: Chosen for structured event storage and time-series queries.
    

Trade-off: Kafka adds complexity but future-proofs the system for scaling to multiple machines and streams.

📊 Example Kafka Payload
------------------------

```json
{
  "frame_id": 450,
  "equipment_id": "EX-001",
  "equipment_class": "excavator",
  "timestamp": "00:00:15.000",
  "utilization": {
    "current_state": "ACTIVE",
    "current_activity": "DIGGING",
    "motion_source": "arm_only"
  },
  "time_analytics": {
    "total_tracked_seconds": 15.0,
    "total_active_seconds": 12.5,
    "total_idle_seconds": 2.5,
    "utilization_percent": 83.3
  }
}
```

🎥 Demo
-------

there is a short video showing the run and the output on the website:

*   Video feed with bounding boxes
    
*   Dashboard updating in real-time

  
