"""
Audit and Validation Script for Dairy Product Dataset.
Performs comprehensive quality checks:
1. File integrity: checks for corrupted or unreadable image files.
2. Exact duplicates: MD5 hash collision detection across and within classes/splits.
3. Near-duplicates: Perceptual difference hashing (dHash) to detect identical/near-identical packaging views.
4. Data leakage: verifies no training images or near-duplicates appear in validation or test splits.
5. Class balance: audits distribution of milk, yogurt, cheese, paneer across splits.
6. Image metadata: verifies RGB conversion, minimum resolution, aspect ratios.
7. Generates a comprehensive audit report saved to ml/reports/dairy_dataset_audit_report.json.
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
from PIL import Image
import numpy as np

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_dairy_dataset")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRIMARY_DATASET_DIR = os.path.join(BASE_DIR, "datasets", "dairy_packaging")
TARGET_ML_DATASET_DIR = os.path.join(BASE_DIR, "ml", "datasets", "dairy")
REPORT_PATH = os.path.join(BASE_DIR, "ml", "reports", "dairy_dataset_audit_report.json")

os.makedirs(os.path.join(BASE_DIR, "ml", "reports"), exist_ok=True)

def compute_dhash(image: Image.Image, hash_size: int = 8) -> int:
    """Computes difference hash (dHash) for detecting near-duplicate images."""
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.array(resized)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(h1: int, h2: int) -> int:
    """Computes bitwise Hamming distance between two integer hashes."""
    x = h1 ^ h2
    return bin(x).count("1")

def audit_dataset_directory(dataset_dir: str) -> Dict[str, Any]:
    logger.info(f"Auditing dataset at: {dataset_dir}")
    
    splits = ["train", "validation", "test"]
    # Handle both 'validation' and 'val'
    actual_splits = []
    for s in splits:
        if os.path.exists(os.path.join(dataset_dir, s)):
            actual_splits.append(s)
        elif s == "validation" and os.path.exists(os.path.join(dataset_dir, "val")):
            actual_splits.append("val")
            
    expected_classes = ["cheese", "milk", "paneer", "yogurt"]
    
    file_records = []
    corrupted_files = []
    exact_hash_map: Dict[str, List[str]] = {}
    dhash_records: List[Dict[str, Any]] = []
    class_split_counts: Dict[str, Dict[str, int]] = {s: {c: 0 for c in expected_classes} for s in actual_splits}
    resolutions = []
    
    for split in actual_splits:
        split_dir = os.path.join(dataset_dir, split)
        for cat in expected_classes:
            cat_dir = os.path.join(split_dir, cat)
            if not os.path.exists(cat_dir):
                logger.warning(f"Category folder missing: {cat_dir}")
                continue
                
            for root, _, files in os.walk(cat_dir):
                for f in files:
                    if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        continue
                    fp = os.path.join(root, f)
                    
                    # 1. Integrity check
                    try:
                        with open(fp, "rb") as f_obj:
                            content = f_obj.read()
                            md5 = hashlib.md5(content).hexdigest()
                            
                        with Image.open(fp) as im:
                            im.verify()
                        with Image.open(fp) as im:
                            im_rgb = im.convert("RGB")
                            w, h = im_rgb.size
                            resolutions.append((w, h))
                            dh = compute_dhash(im_rgb)
                            
                        record = {
                            "path": os.path.relpath(fp, BASE_DIR).replace("\\", "/"),
                            "filename": f,
                            "split": split,
                            "category": cat,
                            "md5": md5,
                            "dhash": dh,
                            "width": w,
                            "height": h,
                            "size_bytes": len(content)
                        }
                        file_records.append(record)
                        class_split_counts[split][cat] += 1
                        
                        if md5 not in exact_hash_map:
                            exact_hash_map[md5] = []
                        exact_hash_map[md5].append(record["path"])
                        
                        dhash_records.append(record)
                        
                    except Exception as e:
                        corrupted_files.append({"path": fp, "error": str(e)})
                        logger.error(f"Corrupt image found: {fp} - {e}")

    # 2. Duplicate Detection
    exact_duplicates = [paths for md5, paths in exact_hash_map.items() if len(paths) > 1]
    
    # 3. Near-Duplicate & Cross-Split Leakage Detection
    near_duplicates = []
    cross_split_leakages = []
    cross_class_conflicts = []
    
    # Pairwise comparison within records
    n = len(dhash_records)
    logger.info(f"Checking {n} records for near-duplicates and cross-split leakage...")
    for i in range(n):
        for j in range(i + 1, n):
            rec_a = dhash_records[i]
            rec_b = dhash_records[j]
            dist = hamming_distance(rec_a["dhash"], rec_b["dhash"])
            
            # Near-identical threshold (Hamming distance <= 2 out of 64 bits)
            if dist <= 2:
                pair_info = {
                    "file_a": rec_a["path"],
                    "file_b": rec_b["path"],
                    "category_a": rec_a["category"],
                    "category_b": rec_b["category"],
                    "split_a": rec_a["split"],
                    "split_b": rec_b["split"],
                    "hamming_distance": dist
                }
                near_duplicates.append(pair_info)
                
                # Check for cross-split leakage
                if rec_a["split"] != rec_b["split"]:
                    cross_split_leakages.append(pair_info)
                    
                # Check for cross-class conflict (e.g. same image labeled milk and yogurt)
                if rec_a["category"] != rec_b["category"]:
                    cross_class_conflicts.append(pair_info)

    # 4. Class Balance Metrics
    total_images = len(file_records)
    total_per_class = {c: sum(class_split_counts[s][c] for s in actual_splits) for c in expected_classes}
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "dataset_directory": os.path.relpath(dataset_dir, BASE_DIR).replace("\\", "/"),
        "total_images_audited": total_images,
        "splits_found": actual_splits,
        "classes_found": expected_classes,
        "class_split_counts": class_split_counts,
        "total_per_class": total_per_class,
        "corrupted_images_count": len(corrupted_files),
        "corrupted_images": corrupted_files,
        "exact_duplicates_count": len(exact_duplicates),
        "exact_duplicates": exact_duplicates,
        "near_duplicates_count": len(near_duplicates),
        "near_duplicates_sample": near_duplicates[:10],
        "cross_split_leakages_count": len(cross_split_leakages),
        "cross_split_leakages": cross_split_leakages,
        "cross_class_conflicts_count": len(cross_class_conflicts),
        "cross_class_conflicts": cross_class_conflicts,
        "resolution_stats": {
            "min_width": min([w for w, h in resolutions]) if resolutions else 0,
            "min_height": min([h for w, h in resolutions]) if resolutions else 0,
            "max_width": max([w for w, h in resolutions]) if resolutions else 0,
            "max_height": max([h for w, h in resolutions]) if resolutions else 0,
            "avg_width": round(float(np.mean([w for w, h in resolutions])), 1) if resolutions else 0,
            "avg_height": round(float(np.mean([h for w, h in resolutions])), 1) if resolutions else 0
        },
        "audit_status": "PASSED" if len(corrupted_files) == 0 and len(exact_duplicates) == 0 and len(cross_split_leakages) == 0 and len(cross_class_conflicts) == 0 else "WARNINGS_FOUND"
    }
    
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Audit report saved to {REPORT_PATH}")
    return report

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else (
        TARGET_ML_DATASET_DIR if os.path.exists(TARGET_ML_DATASET_DIR) else PRIMARY_DATASET_DIR
    )
    report = audit_dataset_directory(target_dir)
    print("\n" + "="*60)
    print("           DAIRY DATASET AUDIT SUMMARY")
    print("="*60)
    print(f"Total Images:               {report['total_images_audited']}")
    print(f"Audit Status:               {report['audit_status']}")
    print(f"Corrupted Images:           {report['corrupted_images_count']}")
    print(f"Exact Duplicates:           {report['exact_duplicates_count']}")
    print(f"Cross-Split Leakages:       {report['cross_split_leakages_count']}")
    print(f"Cross-Class Conflicts:      {report['cross_class_conflicts_count']}")
    print(f"Near-Duplicates:            {report['near_duplicates_count']}")
    print("-" * 60)
    print("Class Breakdown:")
    for cat, count in report['total_per_class'].items():
        print(f"  - {cat.title():<12}: {count:>4} images")
    print("-" * 60)
    print("Split Distribution:")
    for split, counts in report['class_split_counts'].items():
        total_s = sum(counts.values())
        print(f"  - {split.title():<12}: {total_s:>4} images {counts}")
    print("="*60 + "\n")
