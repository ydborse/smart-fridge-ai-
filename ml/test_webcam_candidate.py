from pathlib import Path
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

model_path = Path("/app/ml/models/webcam_food_candidate.pth")
image_dir = Path("/app/storage/uploads")

if not model_path.exists():
    raise FileNotFoundError(f"Candidate model not found: {model_path}")
if not image_dir.exists():
    raise FileNotFoundError(f"Upload folder not found: {image_dir}")

checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
classes = checkpoint["classes"]

model = models.mobilenet_v2(weights=None)
features = model.classifier[1].in_features
model.classifier = nn.Sequential(
    nn.Dropout(p=0.3),
    nn.Linear(features, len(classes))
)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

images = sorted(
    image_dir.glob("*webcam-*.jpg"),
    key=lambda path: path.stat().st_mtime,
    reverse=True
)[:10]

if not images:
    raise RuntimeError("No webcam JPG images found in the upload folder.")

print(f"Candidate classes: {classes}")
print(f"Testing {len(images)} recent webcam images\n")

with torch.inference_mode():
    for path in images:
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                scores = torch.softmax(model(transform(image).unsqueeze(0)), dim=1)[0]
                values, indices = torch.topk(scores, k=min(3, len(classes)))

            print(path.name)
            for score, index in zip(values.tolist(), indices.tolist()):
                print(f"  {classes[index]}: {score:.1%}")
            print()
        except Exception as error:
            print(f"{path.name}: FAILED — {error}\n")
