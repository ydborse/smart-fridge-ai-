from pathlib import Path
from collections import defaultdict
from PIL import Image
import hashlib
import random
import shutil

BASE = Path(__file__).resolve().parent.parent
DATASET = BASE / "dataset"
EXTERNAL = DATASET / "external_fruits_vegetables" / "Fruits_Vegetables_Dataset(12000)"
OUTPUT = DATASET / "freshness_webcam_splits"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
rng = random.Random(42)

if OUTPUT.exists():
    raise FileExistsError(f"{OUTPUT} already exists; not overwriting it.")

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

sources = [
    DATASET,
    EXTERNAL / "Fruits",
    EXTERNAL / "Vegetables",
]
records = {}
conflicts = set()
duplicates = 0
bad_images = 0

for root in sources:
    if not root.is_dir():
        continue

    for folder in root.iterdir():
        if not folder.is_dir():
            continue

        name = folder.name.lower()
        if name.startswith("fresh"):
            label = "fresh"
        elif name.startswith("rotten"):
            label = "rotten"
        else:
            continue

        # Do not scan previously prepared output folders.
        if folder.name.lower().endswith("_splits"):
            continue

        for path in folder.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            try:
                with Image.open(path) as image:
                    image.verify()
                key = digest(path)
            except Exception:
                bad_images += 1
                continue

            if key in conflicts:
                continue
            if key in records:
                if records[key][0] != label:
                    del records[key]
                    conflicts.add(key)
                else:
                    duplicates += 1
                continue
            records[key] = (label, path)

by_label = defaultdict(list)
for key, (label, path) in records.items():
    by_label[label].append((key, path))

for label in ("fresh", "rotten"):
    if len(by_label[label]) < 100:
        raise RuntimeError(f"Too few usable {label} images: {len(by_label[label])}")

print("Unique image counts:")
for label in ("fresh", "rotten"):
    print(f"  {label}: {len(by_label[label])}")

OUTPUT.mkdir(parents=True)
for split in ("train", "val", "test"):
    for label in ("fresh", "rotten"):
        (OUTPUT / split / label).mkdir(parents=True, exist_ok=True)

for label in ("fresh", "rotten"):
    items = by_label[label]
    rng.shuffle(items)
    n = len(items)
    a, b = int(n * 0.70), int(n * 0.85)
    sets = {
        "train": items[:a],
        "val": items[a:b],
        "test": items[b:],
    }
    for split, entries in sets.items():
        for key, source in entries:
            target = OUTPUT / split / label / f"{key[:20]}{source.suffix.lower()}"
            shutil.copy2(source, target)
        print(f"{split:5} {label:6}: {len(entries)} images")

print(f"\nExact duplicates skipped: {duplicates}")
print(f"Conflicting-label duplicates excluded: {len(conflicts)}")
print(f"Unreadable images skipped: {bad_images}")
print(f"Prepared dataset: {OUTPUT}")
print("Original datasets were not modified.")
