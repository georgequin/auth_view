
import time
from video_stream import received_frames, frame_count

connected_clients = 0
server_start_time = time.time()


def compute_stats():
    """
    Calculate overall server and frame stats.
    """
    total_data = sum(f["original_size"] for f in received_frames)
    avg_frame_size = total_data / len(received_frames) if received_frames else 0

    return {
        "total_frames": frame_count,
        "frames_stored": len(received_frames),
        "total_data_received": total_data,
        "average_frame_size": avg_frame_size,
        "server_uptime": time.time() - server_start_time,
        "connected_clients": connected_clients
    }


def increment_clients():
    global connected_clients
    connected_clients += 1


def decrement_clients():
    global connected_clients
    if connected_clients > 0:
        connected_clients -= 1
