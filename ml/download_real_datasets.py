"""
Download authentic produce and freshness datasets from HuggingFace and extract them
into structured dataset folders on Drive E: (no heavy drive C usage).
Extracts:
1. Fresh vs Rotten produce from jojogo9/freshness (real apples, bananas, oranges)
2. Produce items from PedroSampaio/fruits-360 (strawberry, tomato, capsicum, apple, banana, lychee)
3. Broccoli from mlnomad/imnet1k_broccoli
4. User upload rotten samples
"""

import os
import io
import json
import logging
import urllib.request
import pyarrow.parquet as pq
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_real_datasets")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
RAW_DIR = os.path.join(BASE_DIR, "real_raw")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def download_file(url: str, dest_path: str):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        logger.info(f"File already downloaded: {dest_path} ({os.path.getsize(dest_path)/(1024*1024):.2f} MB)")
        return
    logger.info(f"Downloading {url} to {dest_path}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest_path, "wb") as f:
        total = 0
        while True:
            chunk = resp.read(1024 * 512)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (10 * 1024 * 1024) < 1024 * 512:
                logger.info(f"Downloaded {total/(1024*1024):.1f} MB...")
    logger.info(f"Finished downloading {dest_path} ({os.path.getsize(dest_path)/(1024*1024):.2f} MB)")

def extract_freshness_dataset():
    """Extracts real fresh and rotten produce from jojogo9/freshness"""
    test_parquet = os.path.join(DOWNLOADS_DIR, "freshness_test.parquet")
    download_file(
        "https://huggingface.co/datasets/jojogo9/freshness/resolve/main/dataset_100/test.parquet",
        test_parquet
    )

    logger.info("Extracting freshness test parquet images...")
    table = pq.read_table(test_parquet)
    labels = {
        0: ("orange", "rotten"),
        1: ("banana", "rotten"),
        2: ("apple", "rotten"),
        3: ("orange", "fresh"),
        4: ("banana", "fresh"),
        5: ("apple", "fresh")
    }

    count = 0
    for i in range(len(table)):
        lbl = table["label"][i].as_py()
        if lbl in labels:
            item, freshness = labels[lbl]
            out_dir = os.path.join(RAW_DIR, item, freshness)
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, f"hf_{freshness}_{i:05d}.jpg")
            if not os.path.exists(out_file):
                img_bytes = table["image"][i]["bytes"].as_py()
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img.save(out_file, quality=92)
                count += 1
    logger.info(f"Extracted {count} images from freshness dataset.")

def extract_fruits_360():
    """Extracts strawberry, tomato, capsicum, carrot, lychee from PedroSampaio/fruits-360 test parquet"""
    f360_parquet = os.path.join(DOWNLOADS_DIR, "fruits360_test.parquet")
    download_file(
        "https://huggingface.co/datasets/PedroSampaio/fruits-360/resolve/main/data/test-00000-of-00001-0d294abe3826b2e6.parquet",
        f360_parquet
    )

    logger.info("Extracting fruits-360 parquet images...")
    table = pq.read_table(f360_parquet)
    # Target item keywords and mapped class names
    target_map = {
        "strawberry": ("strawberry", "fresh"),
        "tomato": ("tomato", "fresh"),
        "pepper green": ("capsicum", "fresh"),
        "pepper red": ("capsicum", "fresh"),
        "pepper orange": ("capsicum", "fresh"),
        "pepper yellow": ("capsicum", "fresh"),
        "lychee": ("lychee", "fresh"),
        "apple braeburn": ("apple", "fresh"),
        "apple golden": ("apple", "fresh"),
        "banana": ("banana", "fresh"),
        "cucumber": ("cucumber", "fresh")
    }

    # Fruits-360 label index map from README
    label_names = [
        "Apple Braeburn", "Apple Crimson Snow", "Apple Golden", "Apple Granny Smith",
        "Apple Pink Lady", "Apple Red", "Apple Red Delicious", "Apple Red Yellow",
        "Apricot", "Avocado", "Avocado ripe", "Banana", "Banana Lady Finger", "Banana Red",
        "Beetroot", "Blueberry", "Cactus fruit", "Cantaloupe", "Carambula", "Cauliflower",
        "Cherry", "Cherry Rainier", "Cherry Wax Black", "Cherry Wax Red", "Cherry Wax Yellow",
        "Chestnut", "Clementine", "Cocos", "Corn", "Corn Husk", "Cucumber Ripe", "Dates",
        "Eggplant", "Fig", "Ginger Root", "Granadilla", "Grape Blue", "Grape Pink", "Grape White",
        "Grapefruit Pink", "Grapefruit White", "Guava", "Hazelnut", "Huckleberry", "Kaki",
        "Kiwi", "Kohlrabi", "Kumquats", "Lemon", "Lemon Meyer", "Limes", "Lychee", "Mandarine",
        "Mango", "Mango Red", "Mangostan", "Maracuja", "Melon Piel de Sapo", "Mulberry",
        "Nectarine", "Nectarine Flat", "Nut Forest", "Nut Pecan", "Onion Red", "Onion Red Peeled",
        "Onion White", "Orange", "Papaya", "Passion Fruit", "Peach", "Peach Flat", "Pear",
        "Pear Abate", "Pear Forelle", "Pear Kaiser", "Pear Monster", "Pear Red", "Pear Stone",
        "Pear Williams", "Pepino", "Pepper Green", "Pepper Orange", "Pepper Red", "Pepper Yellow",
        "Physalis", "Physalis with Husk", "Pineapple", "Pineapple Mini", "Pitahaya Red", "Plum",
        "Pomegranate", "Pomelo Sweetie", "Potato Red", "Potato Red Washed", "Potato Sweet",
        "Potato White", "Quince", "Rambutan", "Raspberry", "Redcurrant", "Salak", "Strawberry",
        "Strawberry Wedge", "Tamarillo", "Tangelo", "Tomato", "Tomato Cherry Red", "Tomato Heart",
        "Tomato Maroon", "Tomato Yellow", "Tomato not Ripened", "Walnut", "Watermelon"
    ]

    count = 0
    item_counts = {}
    for i in range(len(table)):
        lbl_idx = table["label"][i].as_py()
        if lbl_idx < len(label_names):
            name = label_names[lbl_idx].lower()
            matched_item = None
            for key, (mapped_item, freshness) in target_map.items():
                if key in name:
                    matched_item = (mapped_item, freshness)
                    break
            
            if matched_item:
                mapped_item, freshness = matched_item
                # Limit to 150 images per item to keep balance
                item_counts[mapped_item] = item_counts.get(mapped_item, 0) + 1
                if item_counts[mapped_item] <= 150:
                    out_dir = os.path.join(RAW_DIR, mapped_item, freshness)
                    os.makedirs(out_dir, exist_ok=True)
                    out_file = os.path.join(out_dir, f"f360_{freshness}_{i:05d}.jpg")
                    if not os.path.exists(out_file):
                        img_bytes = table["image"][i]["bytes"].as_py()
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                        img.save(out_file, quality=92)
                        count += 1
    logger.info(f"Extracted {count} images from Fruits-360.")

def extract_broccoli():
    """Extracts broccoli images from mlnomad/imnet1k_broccoli"""
    broc_parquet = os.path.join(DOWNLOADS_DIR, "broccoli_val.parquet")
    download_file(
        "https://huggingface.co/datasets/mlnomad/imnet1k_broccoli/resolve/main/data/validation-00000-of-00001.parquet",
        broc_parquet
    )

    logger.info("Extracting broccoli images...")
    table = pq.read_table(broc_parquet)
    out_dir = os.path.join(RAW_DIR, "broccoli", "fresh")
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for i in range(min(100, len(table))):
        out_file = os.path.join(out_dir, f"broc_{i:04d}.jpg")
        if not os.path.exists(out_file):
            img_bytes = table["image"][i]["bytes"].as_py()
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            img.save(out_file, quality=92)
            count += 1
    logger.info(f"Extracted {count} broccoli images.")

def include_user_and_decay_samples():
    """Adds the user uploaded rotten apple and generate realistic decay variations"""
    user_rotten_src = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "storage", "uploads",
        "ce12c2f08c5440a1868f2f0db73adb09_Screenshot 2026-10-10 172539.png"
    ))
    apple_rotten_dir = os.path.join(RAW_DIR, "apple", "rotten")
    os.makedirs(apple_rotten_dir, exist_ok=True)

    if os.path.exists(user_rotten_src):
        img = Image.open(user_rotten_src).convert("RGB")
        img.save(os.path.join(apple_rotten_dir, "user_rotten_apple_01.jpg"), quality=95)
        # Add rotated & flipped variants for data robustness
        for deg in [90, 180, 270]:
            img.rotate(deg).save(os.path.join(apple_rotten_dir, f"user_rotten_apple_rot{deg}.jpg"), quality=95)
        img.transpose(Image.FLIP_LEFT_RIGHT).save(os.path.join(apple_rotten_dir, "user_rotten_apple_fliph.jpg"), quality=95)
        img.transpose(Image.FLIP_TOP_BOTTOM).save(os.path.join(apple_rotten_dir, "user_rotten_apple_flipv.jpg"), quality=95)
        logger.info("Included user rotten apple sample and augmented orientations.")

if __name__ == "__main__":
    logger.info("Starting real dataset downloads and extraction...")
    extract_freshness_dataset()
    extract_fruits_360()
    extract_broccoli()
    include_user_and_decay_samples()
    logger.info("All datasets extracted successfully to dataset/real_raw/!")
