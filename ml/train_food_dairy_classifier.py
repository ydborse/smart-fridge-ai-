"""
Training script for Model 1: Food and Packaged Dairy Classifier.
Supports 11 classes:
['apple', 'banana', 'broccoli', 'capsicum', 'orange', 'packaged_milk',
 'packaged_paneer', 'packaged_yogurt', 'strawberry', 'tomato', 'unknown']

Uses MobileNetV2 with transfer learning, robust data augmentation,
and evaluates per-class Precision, Recall, F1, and Confusion Matrix.
Saves model to ml/models/food_classifier.pth.
"""

import os
import shutil
import time
import json
import logging
from datetime import datetime
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_food_dairy")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "food_dairy_dataset")
MODELS_DIR = os.path.join(BASE_DIR, "ml", "models")
REPORTS_DIR = os.path.join(BASE_DIR, "ml", "reports")
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "food_classifier.pth")
LEGACY_BACKUP_PATH = os.path.join(MODELS_DIR, "food_classifier_legacy.pth")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Preserve legacy checkpoint if present and not already backed up
if os.path.exists(CHECKPOINT_PATH) and not os.path.exists(LEGACY_BACKUP_PATH):
    shutil.copy2(CHECKPOINT_PATH, LEGACY_BACKUP_PATH)
    logger.info(f"Preserved legacy checkpoint to {LEGACY_BACKUP_PATH}")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Data transforms
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

eval_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def train_model():
    train_dir = os.path.join(DATASET_DIR, "train")
    val_dir = os.path.join(DATASET_DIR, "val")
    test_dir = os.path.join(DATASET_DIR, "test")

    train_ds = datasets.ImageFolder(train_dir, transform=train_transform)
    val_ds = datasets.ImageFolder(val_dir, transform=eval_transform)
    test_ds = datasets.ImageFolder(test_dir, transform=eval_transform)

    class_names = train_ds.classes
    num_classes = len(class_names)
    logger.info(f"Classes ({num_classes}): {class_names}")

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=32, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=32, shuffle=False, num_workers=0)

    # Initialize MobileNetV2 with default ImageNet pretrained weights
    logger.info("Loading MobileNetV2 pretrained backbone...")
    weights = models.MobileNet_V2_Weights.DEFAULT
    model = models.mobilenet_v2(weights=weights)

    # Freeze base layers 0 through 13, fine-tune upper layers 14+ and classifier
    for param in model.features[:14].parameters():
        param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes)
    )
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=0.001,
        weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10)

    best_val_acc = 0.0
    best_weights = None

    epochs = 10
    logger.info(f"Starting training for {epochs} epochs on {len(train_ds)} training images...")

    for epoch in range(1, epochs + 1):
        t0 = time.time()
        model.train()
        train_loss, train_correct = 0.0, 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            train_correct += (outputs.argmax(dim=1) == labels).sum().item()

        scheduler.step()

        # Validation
        model.eval()
        val_loss, val_correct = 0.0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                val_correct += (outputs.argmax(dim=1) == labels).sum().item()

        train_acc = train_correct / len(train_ds)
        val_acc = val_correct / len(val_ds)
        elapsed = time.time() - t0

        logger.info(
            f"Epoch {epoch:02d}/{epochs:02d} [{elapsed:.1f}s] - "
            f"Train Loss: {train_loss/len(train_ds):.4f}, Acc: {train_acc*100:.2f}% | "
            f"Val Loss: {val_loss/len(val_ds):.4f}, Acc: {val_acc*100:.2f}%"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_weights = model.state_dict().copy()

    # Load best weights
    if best_weights is not None:
        model.load_state_dict(best_weights)
        logger.info(f"Loaded best model weights with Val Acc: {best_val_acc*100:.2f}%")

    # Final evaluation on held-out test split
    logger.info("Evaluating on held-out test set...")
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            preds = outputs.argmax(dim=1).cpu().numpy()
            y_pred.extend(preds)
            y_true.extend(labels.numpy())

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    test_acc = float((y_true == y_pred).mean())

    report_dict = classification_report(y_true, y_pred, target_names=class_names, output_dict=True)
    report_text = classification_report(y_true, y_pred, target_names=class_names)
    cm = confusion_matrix(y_true, y_pred).tolist()

    logger.info(f"\nTest Accuracy: {test_acc*100:.2f}%\n" + report_text)

    # Save model checkpoint
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "classes": class_names,
        "num_classes": num_classes,
        "architecture": "mobilenet_v2",
        "timestamp": datetime.utcnow().isoformat(),
        "test_accuracy": test_acc,
        "val_accuracy": best_val_acc
    }
    torch.save(checkpoint, CHECKPOINT_PATH)
    logger.info(f"Model saved to {CHECKPOINT_PATH}")

    # Save detailed evaluation report
    report_output = {
        "timestamp": datetime.utcnow().isoformat(),
        "architecture": "mobilenet_v2",
        "classes": class_names,
        "num_classes": num_classes,
        "train_samples": len(train_ds),
        "val_samples": len(val_ds),
        "test_samples": len(test_ds),
        "val_accuracy": round(best_val_acc, 4),
        "test_accuracy": round(test_acc, 4),
        "classification_report": report_dict,
        "confusion_matrix": cm
    }
    with open(os.path.join(REPORTS_DIR, "food_dairy_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report_output, f, indent=2)

    return report_output

if __name__ == "__main__":
    train_model()
