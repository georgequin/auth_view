# 📸 Webcam Streaming & Recording Server

## Overview
This project is a **web-based camera streaming and recording system** built with **Flask** (Python) for the backend and a **browser client** using modern JavaScript and Web APIs.  
It allows multiple clients to connect, stream live frames from their webcams, and optionally record those streams server-side.

You can deploy the backend on any server (PythonAnywhere, Render, Linode, etc.) and access the web client from any browser-enabled device.

---

## 🚀 Features

### 🎥 Web Client
- Runs directly in a **browser** (no Python installation required)
- Captures webcam video using `navigator.mediaDevices.getUserMedia()`
- Streams JPEG frames to the Flask server every 0.5 seconds
- Lets the user **enter and remember the server URL**
- Auto-generates a unique **Client ID** for each device/session
- Displays live video preview and connection status
- Toggle **Start / Stop Streaming** with a button

### 🖥️ Flask Backend
- Accepts live image uploads via `/upload`
- Tracks connected clients and frame statistics
- Supports real-time dashboard view (`/`)
- Optional **recording system** (PyAV or OpenCV)
- Stores recordings temporarily, uploads to Firebase
- Provides admin API endpoints for:
  - `/record/start` and `/record/stop`
  - `/recordings` (list all recordings)
  - `/stats` and `/latest_frame`

---

## 🧩 Project Structure
flask_app/
├── server/
│ ├── init.py # Flask app factory
│ ├── routes.py # All endpoints and upload logic
│ ├── recording.py # Recorder & RecordingManager classes
│ ├── firebase_service.py # Firebase upload & metadata helpers
│ ├── recordings_tmp/ # Temporary local files
│ └── templates/
│ ├── dashboard.html # Optional live view
│ └── client.html # Web client UI (camera streaming)
├── flask_app.py # App entry point
├── requirements.txt
└── README.md


---

## ⚙️ Installation (Local)

### 1️⃣ Clone the repo
```bash
git clone https://github.com/yourusername/webcam-flask-stream.git
cd webcam-flask-stream


python -m venv venv
source venv/bin/activate     # (Linux/Mac)
venv\Scripts\activate        # (Windows)


pip install flask opencv-python firebase-admin


sudo apt install ffmpeg
pip install flask av firebase-admin

python flask_app.py


http://127.0.0.1:5000
```

 ## Key Endpoints
Method	Endpoint	Description
GET	/	Dashboard (live preview)
GET	/client	Web camera client UI
GET	/test	Health check
POST	/upload	Receive frames from clients
POST	/record/start	Start recording for a client
POST	/record/stop	Stop recording and upload
GET	/recordings	List recent recordings
GET	/stats	Frame statistics
GET	/clients	Connected clients
