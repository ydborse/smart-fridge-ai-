"""
Splits the extracted authentic images into reproducible train/val/test splits (70/15/15)
for TWO independent datasets:
1. Food Item Dataset (dataset/food_dataset/{train,val,test})
2. Freshness Stage Dataset (dataset/freshness_dataset/{train,val,test})
"""

import os
import shutil
import random
import logging
from PIL import Image, ImageEnhance

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_real_dataset")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
RAW_DIR = os.path.join(BASE_DIR, "real_raw")
FOOD_SPLIT_DIR = os.path.join(BASE_DIR, "food_dataset")
FRESH_SPLIT_DIR = os.path.join(BASE_DIR, "freshness_dataset")

# Fixed seed for reproducibility
random.seed(42)

def prepare_food_dataset():
    """Builds train/val/test splits for food item classification."""
    logger.info("Preparing Food Item dataset splits...")
    if os.path.exists(FOOD_SPLIT_DIR):
        shutil.rmtree(FOOD_SPLIT_DIR)

    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(FOOD_SPLIT_DIR, split), exist_ok=True)

    items = sorted(os.listdir(RAW_DIR))
    summary = {}

    for item in items:
        item_path = os.path.join(RAW_DIR, item)
        if not os.path.isdir(item_path):
            continue

        all_item_files = []
        for sub in os.listdir(item_path):
            sub_path = os.path.join(item_path, sub)
            if os.path.isdir(sub_path):
                for f in os.listdir(sub_path):
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        all_item_files.append(os.path.join(sub_path, f))

        random.shuffle(all_item_files)
        n = len(all_item_files)
        if n == 0:
            continue

        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        splits_map = {
            "train": all_item_files[:n_train],
            "val": all_item_files[n_train:n_train + n_val],
            "test": all_item_files[n_train + n_val:]
        }

        for split, files in splits_map.items():
            dest_dir = os.path.join(FOOD_SPLIT_DIR, split, item)
            os.makedirs(dest_dir, exist_ok=True)
            for f in files:
                shutil.copy2(f, os.path.join(dest_dir, os.path.basename(f)))

        summary[item] = {
            "train": len(splits_map["train"]),
            "val": len(splits_map["val"]),
            "test": len(splits_map["test"]),
            "total": n
        }

    logger.info("Food Item Dataset Summary:")
    for item, s in summary.items():
        logger.info(f"  {item:12s}: train={s['train']:4d}, val={s['val']:3d}, test={s['test']:3d} (total={s['total']:4d})")

def prepare_freshness_dataset():
    """Builds train/val/test splits for 4 freshness stages: Fresh, Ripe, Overripe, Rotten."""
    logger.info("Preparing Freshness Stage dataset splits...")
    if os.path.exists(FRESH_SPLIT_DIR):
        shutil.rmtree(FRESH_SPLIT_DIR)

    stages = ["fresh", "ripe", "overripe", "rotten"]
    for split in ["train", "val", "test"]:
        for stage in stages:
            os.makedirs(os.path.join(FRESH_SPLIT_DIR, split, stage), exist_ok=True)

    stage_files = {"fresh": [], "ripe": [], "overripe": [], "rotten": []}

    # 1. Real rotten images across all items
    for item in os.listdir(RAW_DIR):
        item_path = os.path.join(RAW_DIR, item)
        if not os.path.isdir(item_path):
            continue

        rotten_dir = os.path.join(item_path, "rotten")
        if os.path.exists(rotten_dir):
            for f in os.listdir(rotten_dir):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    stage_files["rotten"].append(os.path.join(rotten_dir, f))

        fresh_dir = os.path.join(item_path, "fresh")
        if os.path.exists(fresh_dir):
            for f in os.listdir(fresh_dir):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    stage_files["fresh"].append(os.path.join(fresh_dir, f))

    # 2. Add ripe samples from produce_raw
    for item in ["strawberry", "banana", "orange", "tomato"]:
        p_dir = os.path.join(BASE_DIR, "produce_raw", item)
        if os.path.exists(p_dir):
            for f in os.listdir(p_dir):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    stage_files["ripe"].append(os.path.join(p_dir, f))

    random.shuffle(stage_files["fresh"])
    needed_ripe = max(0, 500 - len(stage_files["ripe"]))
    if needed_ripe > 0:
        stage_files["ripe"].extend(stage_files["fresh"][:needed_ripe])
        stage_files["fresh"] = stage_files["fresh"][needed_ripe:]

    # 3. Overripe
    overripe_dir = os.path.join(BASE_DIR, "overripe_generated")
    if os.path.exists(overripe_dir):
        for f in os.listdir(overripe_dir):
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                stage_files["overripe"].append(os.path.join(overripe_dir, f))

    # 4. Cap and split 70 / 15 / 15
    summary = {}
    for stage in stages:
        files = list(dict.fromkeys(stage_files[stage]))
        random.shuffle(files)
        files = files[:500]
        n = len(files)
        n_train = max(1, int(n * 0.70))
        n_val = max(1, int(n * 0.15))

        train_files = files[:n_train]
        val_files = files[n_train:n_train + n_val]
        test_files = files[n_train + n_val:]

        for idx, f in enumerate(train_files):
            ext = os.path.splitext(f)[1]
            dest_name = f"{stage}_train_{idx:04d}{ext}"
            shutil.copy2(f, os.path.join(FRESH_SPLIT_DIR, "train", stage, dest_name))

        for idx, f in enumerate(val_files):
            ext = os.path.splitext(f)[1]
            dest_name = f"{stage}_val_{idx:04d}{ext}"
            shutil.copy2(f, os.path.join(FRESH_SPLIT_DIR, "val", stage, dest_name))

        for idx, f in enumerate(test_files):
            ext = os.path.splitext(f)[1]
            dest_name = f"{stage}_test_{idx:04d}{ext}"
            shutil.copy2(f, os.path.join(FRESH_SPLIT_DIR, "test", stage, dest_name))

        summary[stage] = {
            "train": len(train_files),
            "val": len(val_files),
            "test": len(test_files),
            "total": n
        }
        logger.info(f"  {stage:10s}: train={len(train_files):4d}, val={len(val_files):3d}, test={len(test_files):3d} (total={n:4d})")

if __name__ == "__main__":
    prepare_food_dataset()
    prepare_freshness_dataset()
    logger.info("Dataset preparation complete!")
