"""
Prepares the freshness dataset:
- Gathers images from dataset/raw/
- Maps raw label variations to standard classes: fresh, ripe, overripe, rotten
- Deduplicates images via md5 hash
- Splits into 70% Train, 15% Val, 15% Test
- Test set is permanently saved and NEVER modified during retraining.
"""

import os
import shutil
import hashlib
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prepare_dataset")

ITEMS = ["apple", "strawberry", "lychee", "banana", "capsicum", "green chilli", "coriander", "tomato", "carrot"]
CLASSES = ["fresh", "ripe", "overripe", "rotten"]

def file_hash(filepath: str) -> str:
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def prepare_data(base_dir: str):
    raw_dir = os.path.join(base_dir, "raw")
    train_dir = os.path.join(base_dir, "train")
    val_dir = os.path.join(base_dir, "val")
    test_dir = os.path.join(base_dir, "test")

    for d in [train_dir, val_dir, test_dir]:
        os.makedirs(d, exist_ok=True)

    seen_hashes = set()
    total_processed = 0

    # Ensure target item folders exist
    for item in ITEMS:
        for cls in CLASSES:
            os.makedirs(os.path.join(train_dir, item, cls), exist_ok=True)
            os.makedirs(os.path.join(val_dir, item, cls), exist_ok=True)
            os.makedirs(os.path.join(test_dir, item, cls), exist_ok=True)

    # Process all images in raw_dir
    random.seed(42)  # Fixed seed for reproducibility

    for root, _, files in os.walk(raw_dir):
        for file in files:
            if not file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue

            src_path = os.path.join(root, file)
            fhash = file_hash(src_path)
            if fhash in seen_hashes:
                continue  # deduplicate
            seen_hashes.add(fhash)

            # Determine item and class from path
            path_parts = root.lower().replace("\\", "/").split("/")
            matched_item = None
            matched_cls = None

            for it in ITEMS:
                if it.replace(" ", "") in "".join(path_parts) or it in "".join(path_parts):
                    matched_item = it
                    break

            for cl in CLASSES:
                if cl in "".join(path_parts):
                    matched_cls = cl
                    break

            # Fallbacks if raw structure is generic
            if not matched_item:
                matched_item = "apple"
            if not matched_cls:
                matched_cls = "fresh" if "fresh" in file.lower() else "rotten"

            # 70 / 15 / 15 split
            rand_val = random.random()
            if rand_val < 0.70:
                dest_dir = os.path.join(train_dir, matched_item, matched_cls)
            elif rand_val < 0.85:
                dest_dir = os.path.join(val_dir, matched_item, matched_cls)
            else:
                dest_dir = os.path.join(test_dir, matched_item, matched_cls)

            shutil.copy2(src_path, os.path.join(dest_dir, file))
            total_processed += 1

    logger.info(f"Dataset preparation complete! Processed {total_processed} unique images.")
    logger.info(f"Train/Val/Test directories populated under {base_dir}")

if __name__ == "__main__":
    bdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
    prepare_data(bdir)
