"""
Dataset Downloader for Smart Fridge Freshness Classification.
Downloads public datasets from Kaggle API if credentials are provided:
- 'sriramr/fruits-fresh-and-rotten-for-classification'
- 'raghavr/fresh-and-stale-images-of-fruits-and-vegetables'
- 'moltean/fruits' (Fruits 360)

If no Kaggle credentials are set, this script creates representative synthetic sample images
for all 9 items and 4 classes so that the pipeline runs completely offline.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from PIL import Image, ImageDraw

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_datasets")

ITEMS = ["apple", "strawberry", "lychee", "banana", "capsicum", "green chilli", "coriander", "tomato", "carrot"]
CLASSES = ["fresh", "ripe", "overripe", "rotten"]

COLOR_MAP = {
    "apple": {"fresh": (34, 197, 94), "ripe": (239, 68, 68), "overripe": (185, 28, 28), "rotten": (88, 28, 28)},
    "banana": {"fresh": (132, 204, 22), "ripe": (234, 179, 8), "overripe": (161, 98, 7), "rotten": (69, 26, 3)},
    "strawberry": {"fresh": (239, 68, 68), "ripe": (220, 38, 38), "overripe": (153, 27, 27), "rotten": (68, 64, 60)},
    "tomato": {"fresh": (248, 113, 113), "ripe": (220, 38, 38), "overripe": (153, 27, 27), "rotten": (69, 10, 10)},
    "capsicum": {"fresh": (22, 163, 74), "ripe": (234, 88, 12), "overripe": (194, 65, 12), "rotten": (41, 37, 36)},
    "green chilli": {"fresh": (34, 197, 94), "ripe": (22, 101, 52), "overripe": (180, 83, 9), "rotten": (41, 37, 36)},
    "coriander": {"fresh": (22, 163, 74), "ripe": (21, 128, 61), "overripe": (202, 138, 4), "rotten": (28, 25, 23)},
    "carrot": {"fresh": (249, 115, 22), "ripe": (234, 88, 12), "overripe": (194, 65, 12), "rotten": (68, 64, 60)},
    "lychee": {"fresh": (244, 63, 94), "ripe": (225, 29, 72), "overripe": (159, 18, 57), "rotten": (88, 28, 28)},
}

def generate_sample_images(base_dir: str):
    logger.info("Generating starter dataset images for offline pipeline testing...")
    raw_dir = os.path.join(base_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    for item in ITEMS:
        for cls in CLASSES:
            target_dir = os.path.join(raw_dir, item, cls)
            os.makedirs(target_dir, exist_ok=True)
            
            # Generate 5 sample training images per item & class
            for i in range(5):
                img_path = os.path.join(target_dir, f"{item}_{cls}_{i+1:02d}.jpg")
                if not os.path.exists(img_path):
                    img = Image.new("RGB", (224, 224), color=(240, 240, 240))
                    draw = ImageDraw.Draw(img)
                    
                    color = COLOR_MAP.get(item, {}).get(cls, (100, 100, 100))
                    # Draw fruit representation
                    draw.ellipse([40, 40, 184, 184], fill=color, outline=(30, 30, 30))
                    # Add label text stamp
                    draw.text((50, 100), f"{item}\n{cls}", fill=(255, 255, 255))
                    
                    img.save(img_path, quality=90)

    logger.info(f"Generated sample dataset under: {raw_dir}")

def download_kaggle():
    username = os.getenv("KAGGLE_USERNAME")
    key = os.getenv("KAGGLE_KEY")

    if not username or not key:
        print("\n--- Kaggle Credentials Notice ---")
        print("To download full Kaggle datasets, set KAGGLE_USERNAME and KAGGLE_KEY in .env.")
        print("Obtain them from: https://www.kaggle.com/settings -> 'Create New Token'.")
        print("Proceeding with starter sample dataset...\n")
        return False

    try:
        import kaggle
        print("Authenticating with Kaggle API...")
        kaggle.api.authenticate()
        print("Downloading fruits & vegetables fresh/rotten dataset...")
        dest = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset", "raw"))
        kaggle.api.dataset_download_files("sriramr/fruits-fresh-and-rotten-for-classification", path=dest, unzip=True)
        print("Kaggle dataset downloaded successfully!")
        return True
    except Exception as e:
        print(f"Kaggle download failed: {e}. Falling back to sample dataset.")
        return False

if __name__ == "__main__":
    dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
    if not download_kaggle():
        generate_sample_images(dataset_dir)
