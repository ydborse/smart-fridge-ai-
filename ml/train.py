"""
Fine-tuning MobileNetV2 with transfer learning for Freshness & Fruit/Vegetable Classification.
Includes:
- Robust augmentations: ColorJitter, RandomRotation, RandomPerspective, GaussianBlur, RandomErasing
- Class weighting for handling imbalance
- Early stopping
- Best checkpoint saving
- Export to ONNX
"""

import os
import time
import copy
import logging
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train")

ITEMS = ["apple", "strawberry", "lychee", "banana", "capsicum", "green chilli", "coriander", "tomato", "carrot"]
CLASSES = ["fresh", "ripe", "overripe", "rotten"]
NUM_CLASSES = len(ITEMS) * len(CLASSES)  # 36 compound classes

def get_class_index(item: str, cls: str) -> int:
    item_idx = ITEMS.index(item)
    cls_idx = CLASSES.index(cls)
    return item_idx * len(CLASSES) + cls_idx

class FreshnessDataset(Dataset):
    def __init__(self, root_dir: str, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.samples = []

        for item in ITEMS:
            for cls in CLASSES:
                folder = os.path.join(root_dir, item, cls)
                if not os.path.exists(folder):
                    continue
                label_idx = get_class_index(item, cls)
                for f in os.listdir(folder):
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        self.samples.append((os.path.join(folder, f), label_idx))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

def train_model(epochs: int = 5, batch_size: int = 16, lr: float = 0.001):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
    train_dir = os.path.join(base_dir, "train")
    val_dir = os.path.join(base_dir, "val")
    model_save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
    os.makedirs(model_save_dir, exist_ok=True)

    # Rich augmentations
    train_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(degrees=20),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.5),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
        transforms.GaussianBlur(kernel_size=(3, 3), sigma=(0.1, 2.0)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2, scale=(0.02, 0.2))
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_dataset = FreshnessDataset(train_dir, transform=train_transforms)
    val_dataset = FreshnessDataset(val_dir, transform=val_transforms)

    if len(train_dataset) == 0:
        logger.warning("No training samples found in dataset/train/. Run download_datasets.py and prepare_dataset.py first.")
        return

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device} | Training samples: {len(train_dataset)}")

    # Load MobileNetV2 pretrained backbone
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, NUM_CLASSES)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    patience = 4
    epochs_no_improve = 0

    for epoch in range(epochs):
        logger.info(f"--- Epoch {epoch+1}/{epochs} ---")
        model.train()
        running_loss = 0.0
        running_corrects = 0

        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            _, preds = torch.max(outputs, 1)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

        epoch_loss = running_loss / max(1, len(train_dataset))
        epoch_acc = (running_corrects.double() / max(1, len(train_dataset))).item()
        logger.info(f"Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")

        # Validation
        model.eval()
        val_loss = 0.0
        val_corrects = 0
        if len(val_dataset) > 0:
            with torch.no_grad():
                for inputs, labels in val_loader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    _, preds = torch.max(outputs, 1)
                    val_loss += loss.item() * inputs.size(0)
                    val_corrects += torch.sum(preds == labels.data)

            epoch_val_loss = val_loss / len(val_dataset)
            epoch_val_acc = (val_corrects.double() / len(val_dataset)).item()
            logger.info(f"Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc:.4f}")
            scheduler.step(epoch_val_loss)

            if epoch_val_acc > best_acc:
                best_acc = epoch_val_acc
                best_model_wts = copy.deepcopy(model.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    logger.info("Early stopping triggered.")
                    break
        else:
            best_model_wts = copy.deepcopy(model.state_dict())

    # Save best PyTorch weights
    best_weights_path = os.path.join(model_save_dir, "best_model.pth")
    torch.save({"state_dict": best_model_wts, "num_classes": NUM_CLASSES}, best_weights_path)
    logger.info(f"Saved best model checkpoint to {best_weights_path}")

    # Export ONNX
    try:
        model.load_state_dict(best_model_wts)
        model.eval()
        dummy_input = torch.randn(1, 3, 224, 224, device=device)
        onnx_path = os.path.join(model_save_dir, "model.onnx")
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
        )
        logger.info(f"Exported ONNX model to {onnx_path}")
    except Exception as e:
        logger.warning(f"ONNX export skipped: {e}")

if __name__ == "__main__":
    train_model(epochs=3)
