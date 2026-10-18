import urllib.request
import json

boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
img_path = r"e:\smart-fridge-AI\smartfridge-main\storage\uploads\ce12c2f08c5440a1868f2f0db73adb09_Screenshot 2026-10-10 172539.png"
with open(img_path, "rb") as f:
    img_bytes = f.read()

part1 = f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"user_apple.png\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8")
part2 = f"\r\n--{boundary}--\r\n".encode("utf-8")
body = part1 + img_bytes + part2

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/predict",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
)

with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())
    print("STATUS:", resp.status)
    print("Top Prediction:", json.dumps(data.get("top_prediction"), indent=2))
    print("Is Demo Mode:", data.get("is_demo_mode"))
