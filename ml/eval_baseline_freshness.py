import os
import sys
import json
import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np
from PIL import Image

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 1. Load Model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model_path = os.path.join(BASE_DIR, 'ml', 'models', 'freshness_classifier.pth')
ckpt = torch.load(model_path, map_location=device)
classes = ckpt.get('classes', ['fresh', 'overripe', 'ripe', 'rotten'])

model = models.mobilenet_v2(weights=None)
model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(classes))
model.load_state_dict(ckpt.get('model_state_dict', ckpt))
model = model.to(device)
model.eval()

# 2. Evaluate on held-out test dataset
test_dir = os.path.join(BASE_DIR, 'dataset', 'freshness_splits', 'test')
eval_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

test_ds = datasets.ImageFolder(test_dir, transform=eval_transforms)
test_loader = DataLoader(test_ds, batch_size=32, shuffle=False)

all_preds = []
all_targets = []
all_probs = []

with torch.inference_mode():
    for images, targets in test_loader:
        images = images.to(device)
        outputs = model(images)
        probs = torch.softmax(outputs, dim=1)
        preds = torch.argmax(probs, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_targets.extend(targets.numpy())
        all_probs.extend(probs.cpu().numpy())

all_preds = np.array(all_preds)
all_targets = np.array(all_targets)
all_probs = np.array(all_probs)

report = classification_report(all_targets, all_preds, target_names=test_ds.classes, output_dict=True)
cm = confusion_matrix(all_targets, all_preds)

print('=== Current Freshness Model Test Metrics ===')
print('Classes:', test_ds.classes)
for c in test_ds.classes:
    p = report[c]['precision']
    r = report[c]['recall']
    f1 = report[c]['f1-score']
    sup = report[c]['support']
    print(f"{c:10s} - Precision: {p:.3f}, Recall: {r:.3f}, F1: {f1:.3f}, Support: {sup}")
print('Macro F1:', report['macro avg']['f1-score'])
print('Accuracy:', report['accuracy'])
print('\nConfusion Matrix:\n', cm)

# False-fresh calculation: truly overripe or rotten predicted as fresh
overripe_idx = test_ds.class_to_idx['overripe']
rotten_idx = test_ds.class_to_idx['rotten']
fresh_idx = test_ds.class_to_idx['fresh']

spoiled_mask = (all_targets == overripe_idx) | (all_targets == rotten_idx)
false_fresh_count = int(np.sum((all_preds[spoiled_mask] == fresh_idx)))
total_spoiled = int(np.sum(spoiled_mask))
false_fresh_rate = float(false_fresh_count / total_spoiled if total_spoiled > 0 else 0)

rotten_mask = (all_targets == rotten_idx)
rotten_recall = float(np.sum((all_preds[rotten_mask] == rotten_idx)) / np.sum(rotten_mask))

print(f'\nTotal truly spoiled (Overripe + Rotten): {total_spoiled}')
print(f'False Fresh count (Spoiled predicted as Fresh): {false_fresh_count} ({false_fresh_rate*100:.2f}%)')
print(f'Rotten Recall: {rotten_recall*100:.2f}%')

# 3. Raw outputs on user uploaded capsicum image(s)
user_img_paths = [
    os.path.join(BASE_DIR, 'storage', 'uploads', '514935fc11894dd8960040d55f82e281_Screenshot 2026-10-11 182958.png'),
    os.path.join(BASE_DIR, 'storage', 'uploads', '918176bc0770432eb71efc4749f85471_Screenshot 2026-10-11 182928.png'),
    os.path.join(BASE_DIR, 'storage', 'uploads', '4276245b967d4a02ae55e7914a0c5bbd_Screenshot 2026-10-11 224226.png')
]

capsicum_results = {}
for uip in user_img_paths:
    if os.path.exists(uip):
        img = Image.open(uip).convert('RGB')
        t = eval_transforms(img).unsqueeze(0).to(device)
        with torch.inference_mode():
            out = model(t)
            probs = torch.softmax(out, dim=1)[0].cpu().numpy()
            capsicum_results[os.path.basename(uip)] = {c: float(p) for c, p in zip(classes, probs)}
            print(f'\nUser Image: {os.path.basename(uip)}')
            for c, p in zip(classes, probs):
                print(f'  {c:10s}: {p*100:.2f}%')

# Save report
baseline_report = {
    'architecture': 'MobileNetV2',
    'checkpoint_path': 'ml/models/freshness_classifier.pth',
    'classes': test_ds.classes,
    'accuracy': float(report['accuracy']),
    'macro_f1': float(report['macro avg']['f1-score']),
    'per_class': report,
    'confusion_matrix': cm.tolist(),
    'false_fresh_rate': float(false_fresh_rate),
    'false_fresh_count': int(false_fresh_count),
    'total_spoiled': int(total_spoiled),
    'rotten_recall': float(rotten_recall),
    'user_capsicum_evaluations': capsicum_results
}

out_report_path = os.path.join(BASE_DIR, 'ml', 'reports', 'baseline_freshness_report.json')
with open(out_report_path, 'w') as f:
    json.dump(baseline_report, f, indent=2)
print(f'\nBaseline report saved to {out_report_path}')
