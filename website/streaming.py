import io, time
from PIL import ImageGrab


def generate_frames():
    while True:
        try:
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
                   + buf.getvalue() + b"\r\n")
            time.sleep(0.05)
        except Exception as e:
            print("[stream]", e)
            time.sleep(0.5)
