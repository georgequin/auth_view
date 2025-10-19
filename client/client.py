# client.py
import cv2
import requests
import time
import sys

SERVER_URL = "http://127.0.0.1:5000"  # <-- change to match your network/server
CLIENT_ID = "CAMERA_01"


def test_server():
    """Check if the Flask server is reachable."""
    try:
        response = requests.get(f"{SERVER_URL}/test", timeout=5)
        if response.status_code == 200:
            print("✅ Server reachable:", response.json())
            return True
        print("❌ Server returned non-200:", response.status_code)
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach server: {e}")
        return False


def open_camera(index=0):
    """Try to open the local camera."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError("Camera not accessible")
    print("✅ Camera opened successfully")
    return cap


def send_frame(frame, frame_id):
    _, buffer = cv2.imencode('.jpg', frame)
    files = {'image': ('frame.jpg', buffer.tobytes(), 'image/jpeg')}
    headers = {"X-Client-ID": CLIENT_ID}
    requests.post(f"{SERVER_URL}/upload", files=files, headers=headers, timeout=3)


def main():
    print("🎥 Starting client streaming session")

    # Step 1: Check server
    if not test_server():
        sys.exit(1)

    # Step 2: Initialize camera
    try:
        cap = open_camera()
    except RuntimeError as e:
        print("❌", e)
        sys.exit(1)

    frame_count = 0
    start_time = time.time()

    # Step 3: Stream frames for 10 seconds (or until 'q' pressed)
    try:
        while (time.time() - start_time) < 1000:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Frame read failed")
                break

            frame_count += 1
            send_frame(frame, frame_count)

            cv2.imshow("Streaming (press Q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        print(f"📊 Stream ended. Sent {frame_count} frames in {int(time.time() - start_time)}s")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
