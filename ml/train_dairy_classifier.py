"""
Production Training Pipeline for Dairy Product Classifier.
Uses MobileNetV2 with two-phase Transfer Learning:
- Phase 1: Frozen backbone warmup (train classifier head only)
- Phase 2: Gentle fine-tuning of upper convolutional blocks (features[14:])
- Class balancing, label smoothing, and Cosine Annealing learning rate schedule
- Early stopping based on validation loss / accuracy
- Saves best checkpoint to ml/models/dairy_classifier.pth
- Evaluates on held-out test split and writes ml/reports/dairy_classifier_report.json
"""

import os
import sys
import copy
import time
import json
import random
import logging
from datetime import datetime
from typing import Dict, Any, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_dairy_classifier")

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "ml", "datasets", "dairy")
FALLBACK_DATASET_DIR = os.path.join(BASE_DIR, "datasets", "dairy_packaging")
MODELS_DIR = os.path.join(BASE_DIR, "ml", "models")
REPORTS_DIR = os.path.join(BASE_DIR, "ml", "reports")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "dairy_classifier.pth")
REPORT_PATH = os.path.join(REPORTS_DIR, "dairy_classifier_report.json")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Determine active dataset directory
if os.path.exists(DATASET_DIR):
    ACTIVE_DATASET = DATASET_DIR
    VAL_FOLDER = "val"
else:
    ACTIVE_DATASET = FALLBACK_DATASET_DIR
    VAL_FOLDER = "validation"

# Data Augmentation & Normalization
train_transforms = transforms.Compose([
    transforms.Resize((236, 236)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=10),
    transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.12),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

eval_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def train_dairy_model(
    phase1_epochs: int = 15,
    phase2_epochs: int = 15,
    batch_size: int = 32,
    phase1_lr: float = 1e-3,
    phase2_lr: float = 1e-4,
    weight_decay: float = 1e-3,
    label_smoothing: float = 0.05
) -> Dict[str, Any]:
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device} for dairy classifier training.")
    
    train_dir = os.path.join(ACTIVE_DATASET, "train")
    val_dir = os.path.join(ACTIVE_DATASET, VAL_FOLDER)
    test_dir = os.path.join(ACTIVE_DATASET, "test")
    
    logger.info(f"Loading datasets from: {ACTIVE_DATASET}")
    train_ds = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_ds = datasets.ImageFolder(val_dir, transform=eval_transforms)
    test_ds = datasets.ImageFolder(test_dir, transform=eval_transforms)
    
    class_names = train_ds.classes
    num_classes = len(class_names)
    class_to_idx = train_ds.class_to_idx
    
    logger.info(f"Classes ({num_classes}): {class_names} -> mapping: {class_to_idx}")
    logger.info(f"Samples: Train={len(train_ds)}, Val={len(val_ds)}, Test={len(test_ds)}")
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # 1. Initialize MobileNetV2 with official pretrained ImageNet weights
    logger.info("Initializing MobileNetV2 backbone (ImageNet-1K pretrained)...")
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    
    # Multi-layer classification head with Dropout & BatchNorm
    classifier_head = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 256),
        nn.BatchNorm1d(256),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.3),
        nn.Linear(256, num_classes)
    )
    model.classifier = classifier_head
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    
    # =========================================================================
    # PHASE 1: Warmup with Frozen Backbone (train classifier head only)
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 1: Training Classification Head (Backbone Frozen)")
    logger.info("="*60)
    
    for param in model.features.parameters():
        param.requires_grad = False
    for param in model.classifier.parameters():
        param.requires_grad = True
        
    optimizer_p1 = optim.AdamW(model.classifier.parameters(), lr=phase1_lr, weight_decay=weight_decay)
    scheduler_p1 = optim.lr_scheduler.CosineAnnealingLR(optimizer_p1, T_max=phase1_epochs)
    
    best_val_acc = 0.0
    best_model_weights = copy.deepcopy(model.state_dict())
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    
    start_time = time.time()
    
    for epoch in range(1, phase1_epochs + 1):
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        
        for imgs, targets in train_loader:
            imgs, targets = imgs.to(device), targets.to(device)
            optimizer_p1.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer_p1.step()
            
            running_loss += loss.item() * imgs.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
            
        scheduler_p1.step()
        train_loss = running_loss / total
        train_acc = correct / total
        
        # Validation
        model.eval()
        v_loss, v_correct, v_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, targets in val_loader:
                imgs, targets = imgs.to(device), targets.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, targets)
                v_loss += loss.item() * imgs.size(0)
                preds = outputs.argmax(dim=1)
                v_correct += (preds == targets).sum().item()
                v_total += targets.size(0)
                
        val_loss = v_loss / v_total
        val_acc = v_correct / v_total
        
        history["train_loss"].append(round(train_loss, 4))
        history["train_acc"].append(round(train_acc, 4))
        history["val_loss"].append(round(val_loss, 4))
        history["val_acc"].append(round(val_acc, 4))
        
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_model_weights = copy.deepcopy(model.state_dict())
            
        if epoch % 5 == 0 or epoch == phase1_epochs:
            logger.info(f"[Phase 1] Epoch {epoch:02d}/{phase1_epochs:02d} | Train Loss: {train_loss:.4f} Acc: {train_acc:.2%} | Val Loss: {val_loss:.4f} Acc: {val_acc:.2%}")

    # =========================================================================
    # PHASE 2: Fine-Tuning Upper Convolutions (features[14:])
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("PHASE 2: Fine-Tuning Upper Feature Layers (features[14:] + Classifier)")
    logger.info("="*60)
    
    model.load_state_dict(best_model_weights)
    
    # Unfreeze upper blocks of MobileNetV2
    for param in model.features[:14].parameters():
        param.requires_grad = False
    for param in model.features[14:].parameters():
        param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
        
    optimizer_p2 = optim.AdamW([
        {"params": model.features[14:].parameters(), "lr": phase2_lr * 0.4},
        {"params": model.classifier.parameters(), "lr": phase2_lr}
    ], weight_decay=weight_decay)
    
    scheduler_p2 = optim.lr_scheduler.CosineAnnealingLR(optimizer_p2, T_max=phase2_epochs)
    
    for epoch in range(1, phase2_epochs + 1):
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        
        for imgs, targets in train_loader:
            imgs, targets = imgs.to(device), targets.to(device)
            optimizer_p2.zero_grad()
            outputs = model(imgs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer_p2.step()
            
            running_loss += loss.item() * imgs.size(0)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
            
        scheduler_p2.step()
        train_loss = running_loss / total
        train_acc = correct / total
        
        # Validation
        model.eval()
        v_loss, v_correct, v_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, targets in val_loader:
                imgs, targets = imgs.to(device), targets.to(device)
                outputs = model(imgs)
                loss = criterion(outputs, targets)
                v_loss += loss.item() * imgs.size(0)
                preds = outputs.argmax(dim=1)
                v_correct += (preds == targets).sum().item()
                v_total += targets.size(0)
                
        val_loss = v_loss / v_total
        val_acc = v_correct / v_total
        
        history["train_loss"].append(round(train_loss, 4))
        history["train_acc"].append(round(train_acc, 4))
        history["val_loss"].append(round(val_loss, 4))
        history["val_acc"].append(round(val_acc, 4))
        
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_model_weights = copy.deepcopy(model.state_dict())
            
        if epoch % 5 == 0 or epoch == phase2_epochs:
            logger.info(f"[Phase 2] Epoch {epoch:02d}/{phase2_epochs:02d} | Train Loss: {train_loss:.4f} Acc: {train_acc:.2%} | Val Loss: {val_loss:.4f} Acc: {val_acc:.2%}")

    duration = time.time() - start_time
    logger.info(f"Training completed in {duration:.2f} seconds. Best Validation Accuracy: {best_val_acc:.2%}")
    
    # Load best weights
    model.load_state_dict(best_model_weights)
    model.eval()
    
    # =========================================================================
    # HELD-OUT TEST EVALUATION
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("Evaluating Best Checkpoint on Held-Out Test Set...")
    logger.info("="*60)
    
    all_preds, all_targets, all_probs = [], [], []
    with torch.no_grad():
        for imgs, targets in test_loader:
            imgs = imgs.to(device)
            logits = model(imgs)
            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.numpy())
            all_probs.extend(probs.cpu().numpy())
            
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)
    
    test_accuracy = float(np.mean(all_preds == all_targets))
    logger.info(f"Held-Out Test Accuracy: {test_accuracy:.2%}")
    
    # 4x4 Confusion Matrix
    conf_matrix_arr = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(all_targets, all_preds):
        conf_matrix_arr[t, p] += 1
        
    per_class_metrics = {}
    for i, c in enumerate(class_names):
        tp = int(conf_matrix_arr[i, i])
        fp = int(conf_matrix_arr[:, i].sum() - tp)
        fn = int(conf_matrix_arr[i, :].sum() - tp)
        support = int(conf_matrix_arr[i, :].sum())
        prec = round(float(tp / (tp + fp)), 4) if (tp + fp) > 0 else 0.0
        rec = round(float(tp / (tp + fn)), 4) if (tp + fn) > 0 else 0.0
        f1 = round(float(2 * prec * rec / (prec + rec)), 4) if (prec + rec) > 0 else 0.0
        per_class_metrics[c] = {
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "support": support
        }
        
    # Specific pairwise confusion checks
    # class_names: cheese:0, milk:1, paneer:2, yogurt:3
    c_idx = class_to_idx.get("cheese", 0)
    m_idx = class_to_idx.get("milk", 1)
    p_idx = class_to_idx.get("paneer", 2)
    y_idx = class_to_idx.get("yogurt", 3)
    
    pairwise_analysis = {
        "milk_confused_as_yogurt": int(conf_matrix_arr[m_idx, y_idx]),
        "yogurt_confused_as_milk": int(conf_matrix_arr[y_idx, m_idx]),
        "cheese_confused_as_paneer": int(conf_matrix_arr[c_idx, p_idx]),
        "paneer_confused_as_cheese": int(conf_matrix_arr[p_idx, c_idx]),
        "yogurt_confused_as_cheese": int(conf_matrix_arr[y_idx, c_idx]),
        "cheese_confused_as_yogurt": int(conf_matrix_arr[c_idx, y_idx])
    }
    
    report_data = {
        "model_name": "Dairy Packaging & Product Classifier (MobileNetV2)",
        "model_version": "v3.2",
        "timestamp": datetime.utcnow().isoformat(),
        "training_duration_seconds": round(duration, 2),
        "hyperparameters": {
            "phase1_epochs": phase1_epochs,
            "phase2_epochs": phase2_epochs,
            "batch_size": batch_size,
            "phase1_lr": phase1_lr,
            "phase2_lr": phase2_lr,
            "weight_decay": weight_decay,
            "label_smoothing": label_smoothing,
            "optimizer": "AdamW",
            "scheduler": "CosineAnnealingLR"
        },
        "dataset_split": {
            "train_samples": len(train_ds),
            "val_samples": len(val_ds),
            "test_samples": len(test_ds),
            "total_samples": len(train_ds) + len(val_ds) + len(test_ds),
            "classes": class_names,
            "class_to_idx": class_to_idx
        },
        "best_val_accuracy": round(best_val_acc, 4),
        "test_accuracy": round(test_accuracy, 4),
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": {
            "matrix": conf_matrix_arr.tolist(),
            "labels": class_names
        },
        "pairwise_confusion_analysis": pairwise_analysis,
        "history": history
    }
    
    # Save checkpoint
    torch.save({
        "model_state_dict": model.state_dict(),
        "classes": class_names,
        "class_to_idx": class_to_idx,
        "architecture": "mobilenet_v2",
        "model_version": "v3.2",
        "val_accuracy": best_val_acc,
        "test_accuracy": test_accuracy,
        "timestamp": datetime.utcnow().isoformat()
    }, CHECKPOINT_PATH)
    logger.info(f"Saved best model checkpoint to {CHECKPOINT_PATH}")
    
    with open(REPORT_PATH, "w") as f:
        json.dump(report_data, f, indent=2)
    logger.info(f"Saved evaluation report to {REPORT_PATH}")
    
    return report_data

if __name__ == "__main__":
    report = train_dairy_model()
    print("\n" + "="*60)
    print("       DAIRY CLASSIFIER TRAINING REPORT")
    print("="*60)
    print(f"Model Checkpoint:       {CHECKPOINT_PATH}")
    print(f"Best Val Accuracy:      {report['best_val_accuracy']:.2%}")
    print(f"Held-Out Test Accuracy: {report['test_accuracy']:.2%}")
    print("-" * 60)
    print("Per-Class Metrics:")
    for c, m in report['per_class_metrics'].items():
        print(f"  {c.title():<10} -> Precision: {m['precision']:.2%} | Recall: {m['recall']:.2%} | F1: {m['f1_score']:.2%}")
    print("-" * 60)
    print("Key Pairwise Confusion:")
    for pair, count in report['pairwise_confusion_analysis'].items():
        print(f"  {pair:<30}: {count}")
    print("="*60 + "\n")
