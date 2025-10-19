from flask import Blueprint, request, jsonify, render_template
import cv2, numpy as np, base64, time
from datetime import datetime

from .recording import RecordingManager
from .firebase_service import get_db

bp = Blueprint("server", __name__)

frame_count = 0
received_frames = []
MAX_FRAMES_STORED = 50
connected_clients = {}

rec_mgr = RecordingManager()


def _get_client_id() -> str:
    return request.headers.get("X-Client-ID") or request.args.get("clientId") or "unknown"


@bp.route("/")
def index():
    return render_template("dashboard.html")


@bp.route("/upload", methods=["POST"])
def upload_frame():
    global frame_count, received_frames
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image file"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        image_data = file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        # (Optional) processed preview -> grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        _, buffer = cv2.imencode(".jpg", processed, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        frame_count += 1
        received_frames.append({
            "frame_data": frame_base64,
            "timestamp": time.time(),
            "frame_number": frame_count,
            "original_size": len(image_data),
            "processed_size": len(buffer)
        })
        if len(received_frames) > MAX_FRAMES_STORED:
            received_frames.pop(0)

        # ---- NEW: if recording is active for this client, add original frame ----
        client_id = _get_client_id()
        connected_clients[client_id] = time.time()  # track last frame time
        rec_mgr.add_frame(client_id, frame)

        return jsonify({
            "status": "success",
            "frame_count": frame_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/record/start", methods=["POST"])
def start_record():
    data = request.get_json(silent=True) or {}
    client_id = data.get("clientId") or _get_client_id()
    fps = int(data.get("fps", 10))
    max_seconds = int(data.get("maxSeconds", 120))  # default 2 minutes
    rec_mgr.start(client_id=client_id, fps=fps, max_seconds=max_seconds)
    return jsonify({"status": "started", "clientId": client_id, "fps": fps, "maxSeconds": max_seconds})


@bp.route("/record/stop", methods=["POST"])
def stop_record():
    data = request.get_json(silent=True) or {}
    client_id = data.get("clientId") or _get_client_id()
    url, doc_id = rec_mgr.stop(client_id)
    return jsonify({"status": "stopped", "clientId": client_id, "publicUrl": url, "docId": doc_id})


@bp.route("/recordings", methods=["GET"])
def list_recordings():
    """
    Simple admin listing endpoint (server-side).
    For production, add pagination / auth.
    """
    db = get_db()
    docs = db.collection("recordings").order_by("createdAt", direction="DESCENDING").limit(50).stream()
    items = []
    for d in docs:
        it = d.to_dict()
        it["id"] = d.id
        # Firestore returns Timestamp; make ISO string if present
        if "createdAt" in it and hasattr(it["createdAt"], "isoformat"):
            it["createdAt"] = it["createdAt"].isoformat()
        items.append(it)
    return jsonify({"items": items})


@bp.route("/latest_frame")
def get_latest_frame():
    latest = received_frames[-1] if received_frames else None
    return jsonify({
        "frame_data": latest["frame_data"] if latest else None,
        "frame_count": frame_count,
        "connected_clients": connected_clients
    })


@bp.route("/stats")
def stats():
    total_data = sum(f["original_size"] for f in received_frames)
    avg = total_data / len(received_frames) if received_frames else 0
    return jsonify({
        "total_frames": frame_count,
        "frames_stored": len(received_frames),
        "avg_frame_size": avg
    })

@bp.route("/client")
def client_page():
    return render_template("client.html")



@bp.route("/clients")
def get_clients():
    """Return a list of currently active/connected clients (recently seen)."""
    try:
        now = time.time()
        # Keep only clients seen in the last 10 seconds
        active_clients = [
            cid for cid, last_seen in connected_clients.items()
            if now - last_seen < 10
        ]
        return jsonify({"clients": sorted(active_clients)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route("/test")
def test():
    return jsonify({
        "status": "running",
        "version": "2.1",
        "timestamp": datetime.now().isoformat()
    })
