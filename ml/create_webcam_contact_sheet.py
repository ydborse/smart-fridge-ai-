from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

folder = Path("/app/storage/uploads")
images = sorted(
    folder.glob("*webcam-*.jpg"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)[:10]

if not images:
    raise SystemExit("No webcam images found.")

cell_w, cell_h = 300, 250
sheet = Image.new("RGB", (cell_w * 2, cell_h * ((len(images) + 1) // 2)), "white")
draw = ImageDraw.Draw(sheet)

for i, path in enumerate(images):
    with Image.open(path) as src:
        thumb = src.convert("RGB")
        thumb.thumbnail((280, 200))

    x = (i % 2) * cell_w
    y = (i // 2) * cell_h
    sheet.paste(thumb, (x + 10, y + 10))
    draw.text((x + 10, y + 215), path.name[:38], fill="black")

output = folder / "webcam_candidate_contact_sheet.jpg"
sheet.save(output)
print(f"Saved contact sheet: {output}")
