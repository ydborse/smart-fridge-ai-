"""
Dataset acquisition and verification script for:
1. Packaged Dairy Products (Milk, Paneer, Yogurt) from Open Food Facts (ODbL)
2. Real-world produce (Apple, Banana, Orange, Strawberry, Broccoli, Capsicum, Tomato)
3. Non-food / unsupported negative classes (Plate, Refrigerator interior, Onion, Carrot)
4. Real packaging expiry date sample images for OCR evaluation

All downloads stay strictly on Drive E: inside the repository.
"""

import os
import io
import json
import time
import urllib.request
import logging
from PIL import Image
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_dairy")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
DAIRY_DIR = os.path.join(BASE_DIR, "dairy_raw")
PRODUCE_DIR = os.path.join(BASE_DIR, "produce_raw")
OCR_TEST_DIR = os.path.join(BASE_DIR, "ocr_eval_images")

os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(DAIRY_DIR, exist_ok=True)
os.makedirs(PRODUCE_DIR, exist_ok=True)
os.makedirs(OCR_TEST_DIR, exist_ok=True)

USER_AGENT = "SmartFridgeAI/2.0 (contact: dipak@example.com) AcademicResearchBot"

def download_file(url: str, dest_path: str) -> bool:
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return False

def fetch_open_food_facts(category_tag: str, search_term: str, target_class: str, target_count: int = 80):
    """
    Downloads authentic retail packaged food images from Open Food Facts API (ODbL license).
    Uses v2 search API with retry backoff.
    """
    out_dir = os.path.join(DAIRY_DIR, target_class)
    os.makedirs(out_dir, exist_ok=True)

    existing = [f for f in os.listdir(out_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
    if len(existing) >= target_count:
        logger.info(f"Target class '{target_class}' already has {len(existing)} images.")
        return

    logger.info(f"Fetching images for '{target_class}' from Open Food Facts...")
    collected = len(existing)
    page = 1

    manifest_entries = []

    while collected < target_count and page <= 8:
        # Use v2 search with fallback to cgi search
        urls = [
            f"https://world.openfoodfacts.net/api/v2/search?categories_tags_en={category_tag}&page={page}&page_size=40",
            f"https://world.openfoodfacts.org/api/v2/search?categories_tags_en={category_tag}&page={page}&page_size=40",
            f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={urllib.parse.quote(search_term)}&search_simple=1&action=process&json=1&page={page}&page_size=40"
        ]
        data = None
        for u in urls:
            for attempt in range(3):
                try:
                    req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=20) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    break
                except Exception as e:
                    time.sleep(2 ** attempt)
            if data and data.get("products"):
                break

        if not data:
            logger.warning(f"Could not fetch data for page {page}")
            page += 1
            continue

        products = data.get("products", [])
        if not products:
            break

        for prod in products:
            if collected >= target_count:
                break

            img_url = prod.get("image_front_url") or prod.get("image_url")
            if not img_url:
                continue

            barcode = prod.get("code", "")
            brand = prod.get("brands", "Generic")
            name = prod.get("product_name", target_class)

            safe_id = barcode if barcode else f"off_{page}_{collected}"
            file_name = f"{target_class}_{safe_id}.jpg"
            dest = os.path.join(out_dir, file_name)

            if not os.path.exists(dest):
                ok = download_file(img_url, dest)
                if ok:
                    try:
                        with Image.open(dest) as im:
                            im.verify()
                        with Image.open(dest) as im:
                            im = im.convert("RGB")
                            if max(im.size) > 800:
                                im.thumbnail((800, 800), Image.Resampling.LANCZOS)
                            im.save(dest, quality=90)
                        collected += 1
                        manifest_entries.append({
                            "class": target_class,
                            "filename": file_name,
                            "brand": brand,
                            "product_name": name,
                            "barcode": barcode,
                            "source": "OpenFoodFacts",
                            "license": "ODbL"
                        })
                    except Exception:
                        if os.path.exists(dest):
                            os.remove(dest)
                time.sleep(0.1)

        page += 1

    logger.info(f"Collected {collected} images for '{target_class}'.")
    return manifest_entries

def extract_produce_from_parquets():
    """
    Extracts real kitchen/market produce from fruit_veg_test.parquet and mlnomad ImageNet parquets.
    """
    logger.info("Extracting produce images from downloaded parquets...")

    # 1. fruit_veg_test.parquet
    fv_path = os.path.join(DOWNLOADS_DIR, "fruit_veg_test.parquet")
    if os.path.exists(fv_path):
        table = pq.read_table(fv_path)
        meta = json.loads(table.schema.metadata[b'huggingface'].decode('utf-8'))
        label_names = meta['info']['features']['label']['names']

        target_map = {
            "apple": "apple",
            "banana": "banana",
            "orange": "orange",
            "tomato": "tomato",
            "capsicum": "capsicum",
            "bell pepper": "capsicum",
            "onion": "unknown",
            "carrot": "unknown",
            "potato": "unknown",
            "garlic": "unknown",
        }

        for i in range(len(table)):
            lbl_idx = table["label"][i].as_py()
            name = label_names[lbl_idx]
            if name in target_map:
                target_cls = target_map[name]
                out_dir = os.path.join(PRODUCE_DIR, target_cls)
                os.makedirs(out_dir, exist_ok=True)
                dest = os.path.join(out_dir, f"fv_{name}_{i:04d}.jpg")
                if not os.path.exists(dest):
                    raw_bytes = table["image"][i]["bytes"].as_py()
                    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                    img.save(dest, quality=90)

    # 2. broccoli_val.parquet
    broc_path = os.path.join(DOWNLOADS_DIR, "broccoli_val.parquet")
    if os.path.exists(broc_path):
        table = pq.read_table(broc_path)
        out_dir = os.path.join(PRODUCE_DIR, "broccoli")
        os.makedirs(out_dir, exist_ok=True)
        for i in range(min(50, len(table))):
            dest = os.path.join(out_dir, f"broc_imnet_{i:04d}.jpg")
            if not os.path.exists(dest):
                raw_bytes = table["image"][i]["bytes"].as_py()
                img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                img.save(dest, quality=90)

    # 3. mlnomad strawberry & negative classes (refrigerator, plate)
    subsets = {
        "strawberry": ("https://huggingface.co/datasets/mlnomad/imnet1k_strawberry/resolve/main/data/validation-00000-of-00001.parquet", "strawberry"),
        "refrigerator_icebox": ("https://huggingface.co/datasets/mlnomad/imnet1k_refrigerator_icebox/resolve/main/data/validation-00000-of-00001.parquet", "unknown"),
        "plate": ("https://huggingface.co/datasets/mlnomad/imnet1k_plate/resolve/main/data/validation-00000-of-00001.parquet", "unknown")
    }

    for name, (url, target_cls) in subsets.items():
        parquet_file = os.path.join(DOWNLOADS_DIR, f"{name}.parquet")
        ok = download_file(url, parquet_file)
        if ok and os.path.exists(parquet_file):
            try:
                table = pq.read_table(parquet_file)
                out_dir = os.path.join(PRODUCE_DIR, target_cls)
                os.makedirs(out_dir, exist_ok=True)
                for i in range(min(50, len(table))):
                    dest = os.path.join(out_dir, f"{name}_{i:04d}.jpg")
                    if not os.path.exists(dest):
                        raw_bytes = table["image"][i]["bytes"].as_py()
                        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                        img.save(dest, quality=90)
                logger.info(f"Extracted {min(50, len(table))} images from {name}.parquet into '{target_cls}'")
            except Exception as e:
                logger.warning(f"Error extracting {name}.parquet: {e}")

if __name__ == "__main__":
    logger.info("Starting dataset acquisition...")
    # Fetch dairy packaging
    fetch_open_food_facts("milks", "milk", "packaged_milk", target_count=85)
    fetch_open_food_facts("paneer", "paneer", "packaged_paneer", target_count=85)
    fetch_open_food_facts("yogurts", "yogurt", "packaged_yogurt", target_count=85)

    # Extract produce and negative classes
    extract_produce_from_parquets()
    logger.info("Dataset acquisition completed successfully!")
