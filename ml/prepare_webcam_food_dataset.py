
from pathlib import Path
from collections import defaultdict
import hashlib
import random
import shutil

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = (
    BASE_DIR
    / "dataset"
    / "external_fruits_vegetables"
    / "Fruits_Vegetables_Dataset(12000)"
)
OUTPUT_DIR = BASE_DIR / "dataset" / "webcam_food_splits"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
RANDOM_SEED = 42

CLASS_ALIASES = {
    "apple": "apple",
    "banana": "banana",
    "mango": "mango",
    "orange": "orange",
    "strawberry": "strawberry",
    "bellpepper": "capsicum",
    "carrot": "carrot",
    "cucumber": "cucumber",
    "potato": "potato",
    "tomato": "tomato",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(
            f"Dataset folder not found: {SOURCE_DIR}"
        )

    # Never silently overwrite an earlier prepared dataset.
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"{OUTPUT_DIR} already exists. "
            "Keep it safe and inspect it before preparing again."
        )

    rng = random.Random(RANDOM_SEED)
    images_by_class = defaultdict(list)
    seen_hashes = set()
    duplicate_count = 0
    invalid_count = 0

    # Read the original Fresh*/Rotten* folders.
    for group in ("Fruits", "Vegetables"):
        group_dir = SOURCE_DIR / group

        if not group_dir.is_dir():
            raise FileNotFoundError(
                f"Expected folder not found: {group_dir}"
            )

        for condition_dir in sorted(group_dir.iterdir()):
            if not condition_dir.is_dir():
                continue

            folder_name = condition_dir.name

            if folder_name.startswith("Fresh"):
                food_name = folder_name[len("Fresh"):]
            elif folder_name.startswith("Rotten"):
                food_name = folder_name[len("Rotten"):]
            else:
                print(f"Skipping unexpected folder: {folder_name}")
                continue

            food_name = food_name.lower()
            class_name = CLASS_ALIASES.get(food_name)

            if class_name is None:
                print(f"Skipping unmapped class: {folder_name}")
                continue

            for path in condition_dir.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                try:
                    # Verify that the file is a readable image.
                    with Image.open(path) as image:
                        image.verify()

                    digest = sha256_file(path)

                except Exception as error:
                    invalid_count += 1
                    print(f"Skipping unreadable image: {path.name} ({error})")
                    continue

                if digest in seen_hashes:
                    duplicate_count += 1
                    continue

                seen_hashes.add(digest)
                images_by_class[class_name].append((path, digest))

    expected_classes = set(CLASS_ALIASES.values())
    missing_classes = expected_classes - set(images_by_class)

    if missing_classes:
        raise RuntimeError(
            f"No usable images found for classes: {sorted(missing_classes)}"
        )

    # Validate all classes before creating the output directory.
    for class_name in sorted(expected_classes):
        count = len(images_by_class[class_name])
        if count < 100:
            raise RuntimeError(
                f"Only {count} unique images for {class_name}; "
                "inspect the dataset before proceeding."
            )

    OUTPUT_DIR.mkdir(parents=True)

    for split in ("train", "val", "test"):
        for class_name in sorted(expected_classes):
            (OUTPUT_DIR / split / class_name).mkdir(
                parents=True, exist_ok=True
            )

    print("\nPreparing balanced food-identification splits:")

    for class_name in sorted(expected_classes):
        records = images_by_class[class_name]
        rng.shuffle(records)

        total = len(records)
        train_end = int(total * 0.70)
        val_end = train_end + int(total * 0.15)

        split_records = {
            "train": records[:train_end],
            "val": records[train_end:val_end],
            "test": records[val_end:],
        }

        for split, split_images in split_records.items():
            destination = OUTPUT_DIR / split / class_name

            for source, digest in split_images:
                filename = f"{digest[:16]}{source.suffix.lower()}"
                shutil.copy2(source, destination / filename)

        print(
            f"{class_name:12} "
            f"train={len(split_records['train']):4} "
            f"val={len(split_records['val']):3} "
            f"test={len(split_records['test']):3} "
            f"total={total:4}"
        )

    print(f"\nExact duplicates skipped: {duplicate_count}")
    print(f"Unreadable images skipped: {invalid_count}")
    print(f"Prepared dataset: {OUTPUT_DIR}")
    print("Original image folders were not modified.")


if __name__ == "__main__":
    main()
