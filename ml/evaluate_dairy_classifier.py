"""
Repeatable Evaluation Script for Dairy Product Classifier.
Evaluates model on held-out test dataset (72 unseen real packaging images)
and on real-world regression packaging samples.

Outputs:
1. Overall Accuracy
2. Per-Class Precision, Recall, and F1-Score
3. 4x4 Confusion Matrix
4. Specific confusion metrics:
   - Milk versus Yogurt
   - Cheese versus Paneer
5. Confidence calibration analysis (Expected Calibration Error / confidence on correct vs errors)
6. Results on user reference yogurt cups and verified milk, cheese, and paneer products
7. Saves comprehensive report to ml/reports/dairy_evaluation_report.json
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import datasets, transforms, models

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_dairy_classifier")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "ml", "datasets", "dairy")
FALLBACK_DATASET_DIR = os.path.join(BASE_DIR, "datasets", "dairy_packaging")
CHECKPOINT_PATH = os.path.join(BASE_DIR, "ml", "models", "dairy_classifier.pth")
BACKUP_CHECKPOINT_PATH = os.path.join(BASE_DIR, "ml", "models", "backup_pre_upgrade", "dairy_classifier.pth")
REPORT_PATH = os.path.join(BASE_DIR, "ml", "reports", "dairy_evaluation_report.json")

# Determine active dataset directory
if os.path.exists(os.path.join(DATASET_DIR, "test")):
    ACTIVE_TEST_DIR = os.path.join(DATASET_DIR, "test")
else:
    ACTIVE_TEST_DIR = os.path.join(FALLBACK_DATASET_DIR, "test")

eval_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def load_classifier(checkpoint_path: str, device: torch.device):
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found at: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location=device)
    classes = ckpt.get("classes", ["cheese", "milk", "paneer", "yogurt"])
    num_classes = len(classes)
    
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 256),
        nn.BatchNorm1d(256),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.3),
        nn.Linear(256, num_classes)
    )
    
    state_dict = ckpt.get("model_state_dict", ckpt)
    try:
        model.load_state_dict(state_dict)
    except Exception:
        # Fallback for simpler 2-layer classifier head
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, num_classes)
        )
        model.load_state_dict(state_dict)
        
    model.to(device)
    model.eval()
    return model, classes

def evaluate_model_on_test_set(model, classes: List[str], test_dir: str, device: torch.device) -> Dict[str, Any]:
    test_ds = datasets.ImageFolder(test_dir, transform=eval_transforms)
    loader = torch.utils.data.DataLoader(test_ds, batch_size=32, shuffle=False)
    
    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
            
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)
    
    acc = float(np.mean(all_preds == all_labels))
    num_classes = len(classes)
    
    # Confusion matrix
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(all_labels, all_preds):
        cm[t, p] += 1
        
    class_to_idx = test_ds.class_to_idx
    per_class = {}
    for c, idx in class_to_idx.items():
        tp = int(cm[idx, idx])
        fp = int(cm[:, idx].sum() - tp)
        fn = int(cm[idx, :].sum() - tp)
        support = int(cm[idx, :].sum())
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "support": support
        }
        
    # Pairwise confusion
    c_i = class_to_idx.get("cheese", 0)
    m_i = class_to_idx.get("milk", 1)
    p_i = class_to_idx.get("paneer", 2)
    y_i = class_to_idx.get("yogurt", 3)
    
    # Confidence calibration metrics
    max_confs = np.max(all_probs, axis=1)
    is_correct = (all_preds == all_labels)
    avg_conf_correct = float(np.mean(max_confs[is_correct])) if np.any(is_correct) else 0.0
    avg_conf_error = float(np.mean(max_confs[~is_correct])) if np.any(~is_correct) else 0.0
    
    # Expected Calibration Error (ECE) with 10 bins
    bins = np.linspace(0, 1, 11)
    ece = 0.0
    for b in range(len(bins) - 1):
        bin_mask = (max_confs > bins[b]) & (max_confs <= bins[b + 1])
        if np.any(bin_mask):
            bin_acc = float(np.mean(is_correct[bin_mask]))
            bin_conf = float(np.mean(max_confs[bin_mask]))
            bin_weight = float(np.sum(bin_mask) / len(all_labels))
            ece += bin_weight * abs(bin_acc - bin_conf)
            
    return {
        "accuracy": round(acc, 4),
        "total_test_samples": len(all_labels),
        "per_class_metrics": per_class,
        "confusion_matrix": {
            "matrix": cm.tolist(),
            "labels": classes
        },
        "pairwise_confusion": {
            "milk_as_yogurt": int(cm[m_i, y_i]),
            "yogurt_as_milk": int(cm[y_i, m_i]),
            "cheese_as_paneer": int(cm[c_i, p_i]),
            "paneer_as_cheese": int(cm[p_i, c_i]),
            "yogurt_as_cheese": int(cm[y_i, c_i]),
            "cheese_as_yogurt": int(cm[c_i, y_i])
        },
        "calibration": {
            "avg_confidence_correct": round(avg_conf_correct, 4),
            "avg_confidence_error": round(avg_conf_error, 4),
            "expected_calibration_error": round(ece, 4)
        }
    }

def evaluate_regression_samples(model, classes: List[str], device: torch.device) -> List[Dict[str, Any]]:
    test_cases = [
        # Milk samples
        ("Amul Taaza Milk Packet", "datasets/dairy_packaging/test/milk/amul/milk_amul_8901262261425.jpg", "milk"),
        ("Mother Dairy Milk Pouch", "datasets/dairy_packaging/test/milk/mother_dairy/milk_mother_dairy_8901648001904.jpg", "milk"),
        ("Nandini Milk Pouch", "datasets/dairy_packaging/test/milk/nandini/milk_nandini_8906036674081.jpg", "milk"),
        ("Milk Plastic Bottle", "storage/uploads/dairy_f6eaab6b5fc84a47a7b9160acc9ce5f1_Screenshot 2026-10-13 214902.png", "milk"),
        
        # Cheese samples
        ("Amul Cheese Block 200g", "datasets/dairy_packaging/test/cheese/amul/cheese_amul_8901262020060.jpg", "cheese"),
        ("Britannia Cheese Slices", "datasets/dairy_packaging/test/cheese/britannia/cheese_britannia_8901063401457.jpg", "cheese"),
        ("Go Cheese Slices", "datasets/dairy_packaging/test/cheese/go_cheese/cheese_go_cheese_8906001023357.jpg", "cheese"),
        ("Cheddar/Mozzarella Package", "datasets/dairy_packaging/test/cheese/other_brands/cheese_other_brands_8904083310112.jpg", "cheese"),
        
        # Yogurt reference samples
        ("Epigamia Greek Yogurt (Unseen)", "datasets/dairy_packaging/test/yogurt/epigamia/yogurt_epigamia_8906059635120.jpg", "yogurt"),
        ("Epigamia Reference Cup", r"C:\Users\dipak\.gemini\antigravity-ide\brain\e2049c4a-8be3-4f79-8839-abebf09ea3f1\.user_uploaded\media_1791915381137.png", "yogurt"),
        ("Milky Mist Reference Cup", r"C:\Users\dipak\.gemini\antigravity-ide\brain\e2049c4a-8be3-4f79-8839-abebf09ea3f1\.user_uploaded\media_1791915381215.png", "yogurt"),
        ("Milky Mist 2-Pack Reference", r"C:\Users\dipak\.gemini\antigravity-ide\brain\e2049c4a-8be3-4f79-8839-abebf09ea3f1\.user_uploaded\media_1791915381309.png", "yogurt"),
        ("Table Shot Cup with Foil", r"C:\Users\dipak\.gemini\antigravity-ide\brain\e2049c4a-8be3-4f79-8839-abebf09ea3f1\.user_uploaded\media_1791915381339.png", "yogurt"),
        
        # Paneer samples
        ("Fresh Paneer (Amul/Mother Dairy)", "datasets/dairy_packaging/test/paneer/paneer_8901042956275.jpg", "paneer"),
        ("Fresh Paneer (ID Fresh)", "datasets/dairy_packaging/test/paneer/paneer_8904063202321.jpg", "paneer"),
    ]
    
    results = []
    for name, path, expected in test_cases:
        resolved_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
        if not os.path.exists(resolved_path):
            results.append({"name": name, "path": path, "status": "FILE_NOT_FOUND"})
            continue
            
        try:
            im = Image.open(resolved_path).convert("RGB")
            t = eval_transforms(im).unsqueeze(0).to(device)
            with torch.no_grad():
                logits = model(t)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                idx = int(np.argmax(probs))
                pred_cat = classes[idx]
                conf = float(probs[idx])
                
            is_pass = (pred_cat == expected)
            all_scores = {classes[i]: round(float(probs[i]), 4) for i in range(len(classes))}
            results.append({
                "name": name,
                "file": os.path.basename(resolved_path),
                "expected": expected,
                "predicted": pred_cat,
                "confidence": round(conf, 4),
                "all_scores": all_scores,
                "pass": is_pass
            })
        except Exception as e:
            results.append({"name": name, "path": path, "error": str(e), "status": "ERROR"})
            
    return results

def run_evaluation():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device} for evaluation.")
    
    # 1. Evaluate Current Active Model
    logger.info(f"Loading current model: {CHECKPOINT_PATH}")
    curr_model, classes = load_classifier(CHECKPOINT_PATH, device)
    curr_results = evaluate_model_on_test_set(curr_model, classes, ACTIVE_TEST_DIR, device)
    
    # 2. Evaluate Baseline / Backup Model if available
    baseline_results = None
    if os.path.exists(BACKUP_CHECKPOINT_PATH):
        try:
            logger.info(f"Loading backup model for before/after comparison: {BACKUP_CHECKPOINT_PATH}")
            base_model, base_classes = load_classifier(BACKUP_CHECKPOINT_PATH, device)
            baseline_results = evaluate_model_on_test_set(base_model, base_classes, ACTIVE_TEST_DIR, device)
        except Exception as e:
            logger.warning(f"Could not evaluate backup model: {e}")
            
    # 3. Evaluate Regression Real-Life Samples
    logger.info("Evaluating real-world packaging regression samples...")
    regression_results = evaluate_regression_samples(curr_model, classes, device)
    
    passed_reg = sum(1 for r in regression_results if r.get("pass") is True)
    total_reg = len(regression_results)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "checkpoint_path": os.path.relpath(CHECKPOINT_PATH, BASE_DIR).replace("\\", "/"),
        "active_model_metrics": curr_results,
        "baseline_model_metrics": baseline_results,
        "regression_samples_summary": {
            "passed": passed_reg,
            "total": total_reg,
            "pass_rate": round(passed_reg / total_reg, 4) if total_reg > 0 else 0.0
        },
        "regression_samples_detail": regression_results
    }
    
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Evaluation report saved to {REPORT_PATH}")
    
    # Print Console Summary
    print("\n" + "="*65)
    print("          DAIRY CLASSIFIER EVALUATION REPORT")
    print("="*65)
    print(f"Held-Out Test Accuracy:       {curr_results['accuracy']:.2%}")
    if baseline_results:
        print(f"Baseline (Prior) Accuracy:    {baseline_results['accuracy']:.2%}")
        delta = curr_results['accuracy'] - baseline_results['accuracy']
        print(f"Accuracy Delta:               {delta:+.2%}")
    print(f"Regression Test Pass Rate:    {passed_reg}/{total_reg} ({passed_reg/total_reg:.1%})")
    print("-" * 65)
    print("Per-Class Metrics (Active Model):")
    for c, m in curr_results["per_class_metrics"].items():
        print(f"  {c.title():<12} -> Precision: {m['precision']:.2%} | Recall: {m['recall']:.2%} | F1: {m['f1_score']:.2%}")
    print("-" * 65)
    print("Critical Pairwise Confusion:")
    for pair, cnt in curr_results["pairwise_confusion"].items():
        print(f"  {pair:<28}: {cnt}")
    print("-" * 65)
    print("Confidence Calibration:")
    cal = curr_results["calibration"]
    print(f"  Avg Conf (Correct Predictions): {cal['avg_confidence_correct']:.2%}")
    print(f"  Avg Conf (Error Predictions):   {cal['avg_confidence_error']:.2%}")
    print(f"  Expected Calibration Error:     {cal['expected_calibration_error']:.4f}")
    print("="*65 + "\n")
    
    return report

if __name__ == "__main__":
    run_evaluation()
