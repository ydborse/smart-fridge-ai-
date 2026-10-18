import os
import json
import hashlib
from PIL import Image
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def dhash(image, hash_size=8):
    resized = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    pixels = np.array(resized)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def audit_datasets():
    fresh_dir = os.path.join(BASE_DIR, 'dataset', 'freshness_dataset')
    real_raw_dir = os.path.join(BASE_DIR, 'dataset', 'real_raw')
    produce_raw_dir = os.path.join(BASE_DIR, 'dataset', 'produce_raw')
    
    stages = ['fresh', 'ripe', 'overripe', 'rotten']
    splits = ['train', 'val', 'test']
    
    # 1. Audit freshness_dataset
    print("=== Auditing dataset/freshness_dataset ===")
    split_counts = {s: {st: 0 for st in stages} for s in splits}
    corrupt_files = []
    exact_hashes = {}
    exact_dupes = []
    dhashes = {}
    near_dupes = []
    resolutions = []
    
    for s in splits:
        for st in stages:
            p = os.path.join(fresh_dir, s, st)
            if not os.path.exists(p):
                continue
            for f in os.listdir(p):
                fp = os.path.join(p, f)
                split_counts[s][st] += 1
                try:
                    with open(fp, 'rb') as f_obj:
                        content = f_obj.read()
                        md5 = hashlib.md5(content).hexdigest()
                        if md5 in exact_hashes:
                            exact_dupes.append((fp, exact_hashes[md5]))
                        else:
                            exact_hashes[md5] = fp
                            
                    with Image.open(fp) as im:
                        im.verify()
                    with Image.open(fp) as im:
                        resolutions.append(im.size)
                        dh = dhash(im)
                        if dh in dhashes:
                            near_dupes.append((fp, dhashes[dh]))
                        else:
                            dhashes[dh] = fp
                except Exception as e:
                    corrupt_files.append((fp, str(e)))

    # 2. Food x Condition coverage in dataset/real_raw
    print("=== Auditing dataset/real_raw Food x Condition Coverage ===")
    coverage = {}
    if os.path.exists(real_raw_dir):
        for food in os.listdir(real_raw_dir):
            fp = os.path.join(real_raw_dir, food)
            if os.path.isdir(fp):
                coverage[food] = {
                    'fresh': len(os.listdir(os.path.join(fp, 'fresh'))) if os.path.exists(os.path.join(fp, 'fresh')) else 0,
                    'ripe': 0, # Note: was artificially split in prepare script
                    'overripe': 0, # Note: was artificially synthesized
                    'rotten': len(os.listdir(os.path.join(fp, 'rotten'))) if os.path.exists(os.path.join(fp, 'rotten')) else 0
                }
    
    results = {
        'freshness_dataset_splits': split_counts,
        'total_images': sum(sum(v.values()) for v in split_counts.values()),
        'corrupt_files_count': len(corrupt_files),
        'corrupt_files': corrupt_files[:5],
        'exact_duplicates_count': len(exact_dupes),
        'exact_duplicates_sample': exact_dupes[:5],
        'near_duplicates_count': len(near_dupes),
        'near_duplicates_sample': near_dupes[:5],
        'resolution_min': min(resolutions) if resolutions else None,
        'resolution_max': max(resolutions) if resolutions else None,
        'food_x_condition_coverage': coverage
    }
    
    out_path = os.path.join(BASE_DIR, 'ml', 'reports', 'data_audit_report.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Audit completed. Report saved to {out_path}")
    print(json.dumps(results, indent=2))

if __name__ == '__main__':
    audit_datasets()
