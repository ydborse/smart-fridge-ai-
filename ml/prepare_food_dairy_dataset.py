"""
Prepare and split the unified Food & Dairy recognition dataset:
Classes (11 classes):
1. apple
2. banana
3. broccoli
4. capsicum
5. orange
6. packaged_milk
7. packaged_paneer
8. packaged_yogurt
9. strawberry
10. tomato
11. unknown

Creates reproducible 70 / 15 / 15 Train / Val / Test splits
at dataset/food_dairy_dataset/{train, val, test}.
Saves metadata manifest at dataset/food_dairy_manifest.json.
"""

import os
import shutil
import random
import json
import logging
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_dataset")

random.seed(42)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
DAIRY_RAW = os.path.join(BASE_DIR, "dairy_raw")
PRODUCE_RAW = os.path.join(BASE_DIR, "produce_raw")
EXISTING_RAW = os.path.join(BASE_DIR, "real_raw")
DEST_DATASET = os.path.join(BASE_DIR, "food_dairy_dataset")
MANIFEST_PATH = os.path.join(BASE_DIR, "food_dairy_manifest.json")

TARGET_CLASSES = [
    "apple",
    "banana",
    "broccoli",
    "capsicum",
    "carrot",
    "onion",
    "orange",
    "packaged_milk",
    "packaged_paneer",
    "packaged_yogurt",
    "potato",
    "strawberry",
    "tomato",
    "unknown"
]

def collect_images_for_class(cls_name: str):
    images = []
    # 1. Check dairy raw
    d_dir = os.path.join(DAIRY_RAW, cls_name)
    if os.path.exists(d_dir):
        for f in os.listdir(d_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                images.append(os.path.join(d_dir, f))

    # 2. Check produce raw
    p_dir = os.path.join(PRODUCE_RAW, cls_name)
    if os.path.exists(p_dir):
        for f in os.listdir(p_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                images.append(os.path.join(p_dir, f))

    # 3. Check existing real_raw (for produce to supplement if needed)
    e_dir = os.path.join(EXISTING_RAW, cls_name)
    if os.path.exists(e_dir):
        for root, _, files in os.walk(e_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    images.append(os.path.join(root, f))

    # Deduplicate paths
    unique_images = list(dict.fromkeys(images))
    random.shuffle(unique_images)
    # Cap at 100 images per class to maintain class balance across all 11 classes!
    return unique_images[:100]

def main():
    logger.info("Preparing Food & Dairy dataset...")

    if os.path.exists(DEST_DATASET):
        shutil.rmtree(DEST_DATASET)

    for split in ["train", "val", "test"]:
        for cls in TARGET_CLASSES:
            os.makedirs(os.path.join(DEST_DATASET, split, cls), exist_ok=True)

    manifest = {
        "classes": TARGET_CLASSES,
        "num_classes": len(TARGET_CLASSES),
        "split_ratio": {"train": 0.70, "val": 0.15, "test": 0.15},
        "class_counts": {},
        "splits": {"train": 0, "val": 0, "test": 0}
    }

    total_images = 0

    for cls in TARGET_CLASSES:
        files = collect_images_for_class(cls)
        n = len(files)
        if n == 0:
            logger.warning(f"No images found for class {cls}!")
            continue

        n_train = max(1, int(n * 0.70))
        n_val = max(1, int(n * 0.15))
        train_files = files[:n_train]
        val_files = files[n_train:n_train + n_val]
        test_files = files[n_train + n_val:]

        # Copy images
        for split_name, split_files in [("train", train_files), ("val", val_files), ("test", test_files)]:
            dest_dir = os.path.join(DEST_DATASET, split_name, cls)
            for src in split_files:
                base = os.path.basename(src)
                dest = os.path.join(dest_dir, f"{cls}_{base}")
                shutil.copy2(src, dest)
                manifest["splits"][split_name] += 1

        manifest["class_counts"][cls] = {
            "total": n,
            "train": len(train_files),
            "val": len(val_files),
            "test": len(test_files)
        }
        total_images += n
        logger.info(f"Class '{cls}': {n} total (Train: {len(train_files)}, Val: {len(val_files)}, Test: {len(test_files)})")

    manifest["total_images"] = total_images
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Dataset preparation complete! Total {total_images} images written to {DEST_DATASET}")
    logger.info(f"Manifest written to {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
