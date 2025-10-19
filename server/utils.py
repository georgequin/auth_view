import base64
import datetime


def b64_to_bytes(data: str) -> bytes:
    """Decode base64 string to bytes."""
    return base64.b64decode(data.encode('utf-8'))


def bytes_to_b64(data: bytes) -> str:
    """Encode bytes to base64 string."""
    return base64.b64encode(data).decode('utf-8')


def log_event(message: str):
    """Simple timestamped console logger."""
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
