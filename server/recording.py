# import cv2
# import os
# import threading
# import time
# import uuid
# from datetime import datetime
# from typing import Optional, Tuple
# import numpy as np
#
# from .firebase_service import upload_file, save_record_metadata
#
# # Directory for temporary MP4 files
# RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "recordings_tmp")
# os.makedirs(RECORDINGS_DIR, exist_ok=True)
#
#
# class Recorder:
#     """
#     Per-client video recorder.
#     Collects frames (BGR numpy arrays),
#     encodes to MP4 using cv2.VideoWriter,
#     auto-stops after max_seconds,
#     and uploads asynchronously to Firebase.
#     """
#
#     def __init__(self, client_id: str, fps: int = 10, max_seconds: Optional[int] = None):
#         self.client_id = client_id
#         self.fps = fps
#         self.max_seconds = max_seconds
#         self._writer: Optional[cv2.VideoWriter] = None
#         self._path_local: Optional[str] = None
#         self._frames = 0
#         self._w = None
#         self._h = None
#         self._start_ts: Optional[float] = None
#         self._lock = threading.Lock()
#         self._timer: Optional[threading.Timer] = None
#         self._active = False
#         self._thumbnail_path = None
#
#     # ------------------------------------------------------------------ #
#     def start(self):
#         """Start recording and optionally schedule auto-stop."""
#         with self._lock:
#             if self._active:
#                 print(f"[Recorder] {self.client_id} already recording.")
#                 return
#             self._active = True
#             self._start_ts = time.time()
#             print(f"[Recorder] Started recording for {self.client_id}")
#             if self.max_seconds and self.max_seconds > 0:
#                 self._timer = threading.Timer(self.max_seconds, self.stop_and_upload)
#                 self._timer.start()
#
#     # ------------------------------------------------------------------ #
#     def add_frame(self, frame_bgr):
#         """Add a frame to the buffer, initializing writer lazily."""
#         with self._lock:
#             if not self._active or frame_bgr is None or not isinstance(frame_bgr, np.ndarray):
#                 return
#
#             # Normalize color format
#             if len(frame_bgr.shape) == 2:  # grayscale
#                 frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_GRAY2BGR)
#             elif frame_bgr.shape[2] == 4:  # RGBA → BGR
#                 frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_RGBA2BGR)
#
#             h, w = frame_bgr.shape[:2]
#
#             # Lazily initialize writer on first frame
#             if self._writer is None:
#                 h, w = frame_bgr.shape[:2]
#                 self._h, self._w = h, w
#                 filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self.client_id}_{uuid.uuid4().hex}.mp4"
#                 self._path_local = os.path.join(RECORDINGS_DIR, filename)
#
#                 # --- FIX: force width,height order explicitly ---
#                 frame_size = (int(w), int(h))
#
#                 # Prefer mp4v for Windows compatibility
#                 fourcc = cv2.VideoWriter_fourcc(*"mp4v")
#                 self._writer = cv2.VideoWriter(self._path_local, fourcc, float(self.fps), frame_size)
#                 if not self._writer.isOpened():
#                     raise RuntimeError(f"Failed to open VideoWriter for {frame_size}")
#
#                 print(f"[Recorder] Writer created: {self._path_local} {frame_size}@{self.fps}fps")
#
#             # Enforce consistent frame size
#             if (h, w) != (self._h, self._w):
#                 frame_bgr = cv2.resize(frame_bgr, (self._w, self._h))
#
#             # Save thumbnail from first frame
#             if self._frames == 0:
#                 thumb_name = os.path.splitext(self._path_local)[0] + "_thumb.jpg"
#                 cv2.imwrite(thumb_name, frame_bgr)
#                 self._thumbnail_path = thumb_name
#
#             print(
#                 f"[DEBUG] Frame shape: {frame_bgr.shape}, dtype: {frame_bgr.dtype}, writer: {self._writer is not None}")
#             # Write frame
#             self._writer.write(frame_bgr)
#             self._frames += 1
#
#     # ------------------------------------------------------------------ #
#     def _background_upload(self, duration):
#         """Handle Firebase upload + metadata in a background thread."""
#         try:
#             dest_path = f"recordings/{os.path.basename(self._path_local)}"
#             public_url = upload_file(self._path_local, dest_path)
#
#             thumb_url = None
#             if self._thumbnail_path and os.path.exists(self._thumbnail_path):
#                 thumb_dest = f"recordings/thumbnails/{os.path.basename(self._thumbnail_path)}"
#                 thumb_url = upload_file(self._thumbnail_path, thumb_dest)
#
#             # Save metadata
#             save_record_metadata({
#                 "clientId": self.client_id,
#                 "createdAt": datetime.utcnow(),
#                 "durationSec": duration,
#                 "fps": self.fps,
#                 "frameCount": self._frames,
#                 "storagePath": dest_path,
#                 "publicUrl": public_url,
#                 "thumbnailUrl": thumb_url,
#                 "width": self._w,
#                 "height": self._h,
#             })
#
#             print(f"[Recorder] Upload complete for {self.client_id}: {public_url}")
#
#         except Exception as e:
#             print(f"[Recorder] Upload error for {self.client_id}: {e}")
#
#         finally:
#             # Clean local temp files
#             for f in [self._path_local, self._thumbnail_path]:
#                 if f and os.path.exists(f):
#                     try:
#                         os.remove(f)
#                     except OSError:
#                         pass
#
#     # ------------------------------------------------------------------ #
#     def stop_and_upload(self) -> Tuple[Optional[str], Optional[str]]:
#         """Stop recording and trigger background upload."""
#         with self._lock:
#             if not self._active:
#                 print(f"[Recorder] No active recording for {self.client_id}")
#                 return None, None
#             self._active = False
#
#             if self._timer:
#                 self._timer.cancel()
#                 self._timer = None
#
#             if not self._writer:
#                 print("[Recorder] No writer initialized; skipping.")
#                 return None, None
#
#             # Release writer and calculate duration
#             self._writer.release()
#             cap = cv2.VideoCapture(self._path_local)
#             print("[DEBUG] Frames written:", int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
#             print("[DEBUG] FPS:", cap.get(cv2.CAP_PROP_FPS))
#             print("[DEBUG] Frame size:", cap.get(cv2.CAP_PROP_FRAME_WIDTH), "x", cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#             cap.release()
#             self._writer = None
#             duration = round(time.time() - self._start_ts, 2)
#             print(f"[Recorder] Stopped recording {self.client_id} after {duration}s ({self._frames} frames)")
#
#             # Validate file
#             if not self._path_local or not os.path.exists(self._path_local):
#                 print("[Recorder] Output file missing; nothing to upload.")
#                 return None, None
#
#             # Debug check: verify written frames
#             cap = cv2.VideoCapture(self._path_local)
#             frame_count_check = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#             fps_check = cap.get(cv2.CAP_PROP_FPS)
#             cap.release()
#             print(f"[Recorder] Encoded frames: {frame_count_check}, FPS: {fps_check}")
#
#             # Spawn background upload thread
#             t = threading.Thread(target=self._background_upload, args=(duration,), daemon=True)
#             t.start()
#
#             return None, None
#
#     # ------------------------------------------------------------------ #
#     @property
#     def active(self) -> bool:
#         with self._lock:
#             return self._active
#
#
# # ====================================================================== #
# class RecordingManager:
#     """Manages multiple Recorder instances (one per client)."""
#
#     def __init__(self):
#         self._by_client = {}
#         self._lock = threading.Lock()
#
#     def start(self, client_id: str, fps: int = 10, max_seconds: Optional[int] = None):
#         with self._lock:
#             rec = self._by_client.get(client_id)
#             if rec and rec.active:
#                 print(f"[RecordingManager] {client_id} already active.")
#                 return
#             rec = Recorder(client_id=client_id, fps=fps, max_seconds=max_seconds)
#             rec.start()
#             self._by_client[client_id] = rec
#
#     def add_frame(self, client_id: str, frame_bgr):
#         with self._lock:
#             rec = self._by_client.get(client_id)
#             if rec and rec.active:
#                 rec.add_frame(frame_bgr)
#
#     def stop(self, client_id: str):
#         with self._lock:
#             rec = self._by_client.get(client_id)
#             if not rec:
#                 print(f"[RecordingManager] No recorder found for {client_id}")
#                 return None, None
#             return rec.stop_and_upload()
#
#     def is_active(self, client_id: str) -> bool:
#         with self._lock:
#             rec = self._by_client.get(client_id)
#             return rec.active if rec else False



import av
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Optional, Tuple
import numpy as np
import cv2

from .firebase_service import upload_file, save_record_metadata

# Directory for temporary MP4 files
RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "recordings_tmp")
os.makedirs(RECORDINGS_DIR, exist_ok=True)


class Recorder:
    """
    Per-client video recorder using PyAV (FFmpeg backend).
    Encodes to MP4 (H.264) with accurate timestamps and async upload.
    """

    def __init__(self, client_id: str, fps: int = 10, max_seconds: Optional[int] = None):
        self.client_id = client_id
        self.fps = fps
        self.max_seconds = max_seconds
        self._container: Optional[av.container.OutputContainer] = None
        self._stream: Optional[av.video.stream.VideoStream] = None
        self._path_local: Optional[str] = None
        self._frames = 0
        self._w = None
        self._h = None
        self._start_ts: Optional[float] = None
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._active = False
        self._thumbnail_path = None

    # ------------------------------------------------------------------ #
    def start(self):
        """Start recording and optionally schedule auto-stop."""
        with self._lock:
            if self._active:
                print(f"[Recorder] {self.client_id} already recording.")
                return
            self._active = True
            self._start_ts = time.time()
            print(f"[Recorder] Started recording for {self.client_id}")
            if self.max_seconds and self.max_seconds > 0:
                self._timer = threading.Timer(self.max_seconds, self.stop_and_upload)
                self._timer.start()

    # ------------------------------------------------------------------ #
    def add_frame(self, frame_bgr):
        """Add a frame to the video stream."""
        with self._lock:
            if not self._active or frame_bgr is None or not isinstance(frame_bgr, np.ndarray):
                return

            # Normalize frame
            if frame_bgr.ndim == 2:
                frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_GRAY2BGR)
            elif frame_bgr.shape[2] == 4:
                frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_RGBA2BGR)

            h, w = frame_bgr.shape[:2]

            # Lazily initialize writer
            if self._container is None:
                self._h, self._w = h, w
                filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{self.client_id}_{uuid.uuid4().hex}.mp4"
                self._path_local = os.path.join(RECORDINGS_DIR, filename)

                # Create PyAV container + stream
                self._container = av.open(self._path_local, mode="w")
                self._stream = self._container.add_stream("libx264", rate=self.fps)
                self._stream.width = w
                self._stream.height = h
                self._stream.pix_fmt = "yuv420p"
                print(f"[Recorder] PyAV writer created: {self._path_local} ({w}x{h}@{self.fps}fps)")

            # Capture thumbnail on first frame
            if self._frames == 0:
                thumb_name = os.path.splitext(self._path_local)[0] + "_thumb.jpg"
                cv2.imwrite(thumb_name, frame_bgr)
                self._thumbnail_path = thumb_name

            # Convert to RGB (PyAV expects RGB)
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            for packet in self._stream.encode(video_frame):
                self._container.mux(packet)

            self._frames += 1

    # ------------------------------------------------------------------ #
    def _background_upload(self, duration):
        """Handle Firebase upload + metadata in a background thread."""
        try:
            dest_path = f"recordings/{os.path.basename(self._path_local)}"
            public_url = upload_file(self._path_local, dest_path)

            thumb_url = None
            if self._thumbnail_path and os.path.exists(self._thumbnail_path):
                thumb_dest = f"recordings/thumbnails/{os.path.basename(self._thumbnail_path)}"
                thumb_url = upload_file(self._thumbnail_path, thumb_dest)

            save_record_metadata({
                "clientId": self.client_id,
                "createdAt": datetime.utcnow(),
                "durationSec": duration,
                "fps": self.fps,
                "frameCount": self._frames,
                "storagePath": dest_path,
                "publicUrl": public_url,
                "thumbnailUrl": thumb_url,
                "width": self._w,
                "height": self._h,
            })

            print(f"[Recorder] Upload complete for {self.client_id}: {public_url}")

        except Exception as e:
            print(f"[Recorder] Upload error for {self.client_id}: {e}")

        finally:
            # Clean up
            for f in [self._path_local, self._thumbnail_path]:
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass

    # ------------------------------------------------------------------ #
    def stop_and_upload(self) -> Tuple[Optional[str], Optional[str]]:
        """Stop recording and trigger background upload."""
        with self._lock:
            if not self._active:
                print(f"[Recorder] No active recording for {self.client_id}")
                return None, None
            self._active = False

            if self._timer:
                self._timer.cancel()
                self._timer = None

            if self._container is None:
                print("[Recorder] No container initialized; skipping.")
                return None, None

            # Flush encoder and close file properly
            for packet in self._stream.encode():
                self._container.mux(packet)
            self._container.close()

            duration = round(time.time() - self._start_ts, 2)
            print(f"[Recorder] Stopped recording {self.client_id} after {duration}s ({self._frames} frames)")

            if not self._path_local or not os.path.exists(self._path_local):
                print("[Recorder] Output file missing; nothing to upload.")
                return None, None

            # Spawn background upload
            t = threading.Thread(target=self._background_upload, args=(duration,), daemon=True)
            t.start()

            return None, None

    # ------------------------------------------------------------------ #
    @property
    def active(self) -> bool:
        with self._lock:
            return self._active


# ====================================================================== #
class RecordingManager:
    """Manages multiple Recorder instances (one per client)."""

    def __init__(self):
        self._by_client = {}
        self._lock = threading.Lock()

    def start(self, client_id: str, fps: int = 10, max_seconds: Optional[int] = None):
        with self._lock:
            rec = self._by_client.get(client_id)
            if rec and rec.active:
                print(f"[RecordingManager] {client_id} already active.")
                return
            rec = Recorder(client_id=client_id, fps=fps, max_seconds=max_seconds)
            rec.start()
            self._by_client[client_id] = rec

    def add_frame(self, client_id: str, frame_bgr):
        with self._lock:
            rec = self._by_client.get(client_id)
            if rec and rec.active:
                rec.add_frame(frame_bgr)

    def stop(self, client_id: str):
        with self._lock:
            rec = self._by_client.get(client_id)
            if not rec:
                print(f"[RecordingManager] No recorder found for {client_id}")
                return None, None
            return rec.stop_and_upload()

    def is_active(self, client_id: str) -> bool:
        with self._lock:
            rec = self._by_client.get(client_id)
            return rec.active if rec else False

    def list_clients(self) -> list[str]:
        """Return list of known clients (active or recently started)."""
        with self._lock:
            return list(self._by_client.keys())


