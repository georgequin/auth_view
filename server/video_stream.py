# server/video_stream.py
import cv2
import numpy as np
import base64
import time
from typing import Tuple, Dict, Any

# Shared storage (could be replaced later by Redis or a DB)
frame_count = 0
received_frames = []
MAX_FRAMES_STORED = 50


def process_frame(image_data: bytes) -> Tuple[str, Dict[str, Any]]:
    """
    Process an uploaded image, convert it to grayscale, and return base64 JPEG + metadata.
    """
    global frame_count, received_frames

    # Convert to numpy and decode image
    nparr = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Failed to decode image")

    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # Encode as JPEG
    success, buffer = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("Failed to encode image")

    frame_base64 = base64.b64encode(buffer).decode('utf-8')

    # Update counters
    frame_count += 1
    frame_info = {
        "frame_data": frame_base64,
        "timestamp": time.time(),
        "frame_number": frame_count,
        "original_size": len(image_data),
        "processed_size": len(buffer)
    }

    received_frames.append(frame_info)
    if len(received_frames) > MAX_FRAMES_STORED:
        received_frames.pop(0)

    return frame_base64, frame_info


def get_latest_frame():
    """
    Return the most recent frame and global stats.
    """
    global frame_count, received_frames
    latest = received_frames[-1] if received_frames else None
    return {
        "frame_data": latest["frame_data"] if latest else None,
        "frame_count": frame_count,
        "total_frames_stored": len(received_frames)
    }


def get_all_frames():
    """
    Returns all stored frames (for debugging or playback).
    """
    return received_frames
