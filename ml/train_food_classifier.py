"""
Train Food Classifier using MobileNetV2 Transfer Learning on New archive(1) Dataset.
Trains on dataset/food_splits/{train, val, test}.
Classes: 15 food and dairy classes + unknown.
Saves model checkpoint to ml/models/food_classifier.pth with full evaluation metrics.
"""

import os
import time
import copy
import json
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_food_classifier")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "food_splits")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models")
REPORTS_DIR = os.path.join(BASE_DIR, "ml", "reports")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

CHECKPOINT_PATH = os.path.join(MODEL_DIR, "food_classifier.pth")
REPORT_PATH = os.path.join(REPORTS_DIR, "food_classifier_report.json")

def train_food_model(epochs: int = 3, batch_size: int = 32, lr: float = 0.001):
    train_dir = os.path.join(DATASET_DIR, "train")
    val_dir = os.path.join(DATASET_DIR, "val")
    test_dir = os.path.join(DATASET_DIR, "test")

    train_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    eval_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=eval_transforms)
    test_dataset = datasets.ImageFolder(test_dir, transform=eval_transforms)

    classes = train_dataset.classes
    class_to_idx = train_dataset.class_to_idx
    num_classes = len(classes)
    logger.info(f"Loaded {len(train_dataset)} train, {len(val_dataset)} val, {len(test_dataset)} test samples across {num_classes} classes: {classes}")

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # MobileNetV2 pretrained backbone
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    for param in model.features[:-4].parameters():
        param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, num_classes)
    )
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=1e-4)

    best_wts = copy.deepcopy(model.state_dict())
    best_val_acc = 0.0

    t0 = time.time()
    for epoch in range(epochs):
        logger.info(f"=== Epoch {epoch+1}/{epochs} ===")
        model.train()
        running_loss = 0.0
        running_corrects = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            _, preds = torch.max(outputs, 1)
            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data).item()

        epoch_loss = running_loss / len(train_dataset)
        epoch_acc = float(running_corrects) / len(train_dataset)
        logger.info(f"Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

        # Validation
        model.eval()
        val_loss = 0.0
        val_corrects = 0

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                _, preds = torch.max(outputs, 1)
                val_loss += loss.item() * inputs.size(0)
                val_corrects += torch.sum(preds == labels.data).item()

        val_epoch_loss = val_loss / len(val_dataset)
        val_epoch_acc = float(val_corrects) / len(val_dataset)
        logger.info(f"Val Loss: {val_epoch_loss:.4f} Acc: {val_epoch_acc:.4f}")

        if val_epoch_acc > best_val_acc:
            best_val_acc = val_epoch_acc
            best_wts = copy.deepcopy(model.state_dict())

    train_time = time.time() - t0
    logger.info(f"Training completed in {train_time/60:.2f} mins. Best Val Acc: {best_val_acc:.4f}")

    # Load best weights
    model.load_state_dict(best_wts)

    # Test Evaluation
    model.eval()
    y_true = []
    y_pred = []
    test_loss = 0.0
    test_corrects = 0

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            _, preds = torch.max(outputs, 1)
            test_loss += loss.item() * inputs.size(0)
            test_corrects += torch.sum(preds == labels.data).item()
            y_true.extend(labels.cpu().numpy().tolist())
            y_pred.extend(preds.cpu().numpy().tolist())

    test_acc = float(test_corrects) / len(test_dataset)
    report = classification_report(y_true, y_pred, target_names=classes, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred).tolist()

    logger.info(f"\nFood Model Test Accuracy: {test_acc:.4f}")
    logger.info("\nClassification Report:\n" + classification_report(y_true, y_pred, target_names=classes, zero_division=0))

    # Save Checkpoint
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "classes": classes,
        "class_to_idx": class_to_idx,
        "best_val_acc": float(best_val_acc),
        "test_acc": float(test_acc),
        "architecture": "MobileNetV2",
        "dataset_source": "archive(1) + food_dairy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    torch.save(checkpoint, CHECKPOINT_PATH)
    logger.info(f"Saved new Food Classifier checkpoint to: {CHECKPOINT_PATH}")

    # Save Report
    full_report = {
        "dataset": "archive(1) + food_dairy",
        "num_train_samples": len(train_dataset),
        "num_val_samples": len(val_dataset),
        "num_test_samples": len(test_dataset),
        "classes": classes,
        "class_to_idx": class_to_idx,
        "best_val_accuracy": float(best_val_acc),
        "test_accuracy": float(test_acc),
        "classification_report": report,
        "confusion_matrix": cm,
        "training_time_minutes": round(train_time / 60, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(full_report, f, indent=2)
    logger.info(f"Saved Food report to: {REPORT_PATH}")

    return checkpoint, full_report

if __name__ == "__main__":
    train_food_model(epochs=3, batch_size=32, lr=0.001)
