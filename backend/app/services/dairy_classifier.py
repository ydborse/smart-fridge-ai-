import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from PIL import Image
import torch
import torchvision.transforms as transforms
import torchvision.models as models
from app.config import settings

logger = logging.getLogger(__name__)

DAIRY_CLASSES = ["cheese", "milk", "paneer", "yogurt"]

DISPLAY_NAMES = {
    "milk": "Packaged Milk",
    "yogurt": "Yogurt / Curd",
    "paneer": "Packaged Paneer",
    "cheese": "Packaged Cheese",
    "unknown": "Unknown / Non-Dairy"
}

DAIRY_METADATA = {
    "milk": {
        "zone_code": "bottom_shelf",
        "zone_name": "Bottom Shelf",
        "zone_id": 2,
        "shelf_life_days": 5,
        "storage_tips": "Store upright in the coldest section (Bottom Shelf). Avoid door racks to maintain consistent temperature."
    },
    "yogurt": {
        "zone_code": "top_shelf",
        "zone_name": "Top Shelf",
        "zone_id": 1,
        "shelf_life_days": 10,
        "storage_tips": "Keep sealed on the Top Shelf with stable temperature. Consume within 5-7 days after unsealing."
    },
    "paneer": {
        "zone_code": "middle_shelf",
        "zone_name": "Middle Shelf",
        "zone_id": 3,
        "shelf_life_days": 7,
        "storage_tips": "Store packaged paneer on the Middle Shelf. Once unsealed, submerge in fresh water or consume within 48 hours."
    },
    "cheese": {
        "zone_code": "middle_shelf",
        "zone_name": "Middle Shelf",
        "zone_id": 3,
        "shelf_life_days": 14,
        "storage_tips": "Store in the Middle Shelf wrapped in wax paper or airtight container to prevent drying."
    }
}

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

class DairyModelService:
    def __init__(self):
        self.model = None
        self.classes = DAIRY_CLASSES
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "models", "dairy_classifier.pth")
        )
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        """
        Loads the trained MobileNetV2 dairy packaging classifier checkpoint.
        Does not retrain on server startup.
        """
        if not os.path.exists(self.model_path):
            logger.warning(f"Dairy classifier checkpoint not found at {self.model_path}. Service will run in standby.")
            self.model = None
            self.is_loaded = False
            return

        try:
            ckpt = torch.load(self.model_path, map_location=self.device)
            self.classes = ckpt.get("classes", DAIRY_CLASSES)

            net = models.mobilenet_v2(weights=None)
            in_f = net.classifier[1].in_features
            net.classifier = torch.nn.Sequential(
                torch.nn.Dropout(p=0.3),
                torch.nn.Linear(in_f, len(self.classes))
            )
            net.load_state_dict(ckpt.get("model_state_dict", ckpt))
            net.to(self.device)
            net.eval()
            self.model = net
            self.is_loaded = True
            logger.info(f"Loaded Dairy Classifier successfully ({len(self.classes)} classes: {self.classes}).")
        except Exception as e:
            logger.error(f"Error loading dairy classifier checkpoint: {e}")
            self.model = None
            self.is_loaded = False

    def predict(self, image_path: str) -> Dict[str, Any]:
        """
        Runs packaging category inference on uploaded dairy product image.
        Note: Category inference recognizes product packaging type and does NOT determine freshness.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Lazy load if checkpoint became available after initial startup
        if not self.is_loaded:
            self.load_model()

        if self.model is None:
            raise RuntimeError("Dairy Packaging Classifier is not loaded or model file is unavailable.")

        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:
            raise ValueError(f"Corrupted or unsupported image file: {e}")

        tensor = transform(img).unsqueeze(0).to(self.device)

        with torch.inference_mode():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        top_idx = int(probs.argmax())
        top_cat = self.classes[top_idx]
        top_conf = float(probs[top_idx])

        # All scores dictionary
        all_scores = {
            self.classes[i]: round(float(probs[i]), 4)
            for i in range(len(self.classes))
        }

        # Handle low-confidence / non-dairy packaging gracefully
        CONFIDENCE_THRESHOLD = 0.50
        is_low_confidence = top_conf < CONFIDENCE_THRESHOLD

        if is_low_confidence:
            display_name = "Unable to identify confidently"
            storage_tips = (
                "Confidence is low. Please ensure good lighting and upload a clearer packaging image "
                "with the product label and shape clearly visible, or select the category manually."
            )
            guidance = "Unable to identify packaging type confidently. Please upload a clearer image."
        else:
            display_name = DISPLAY_NAMES.get(top_cat, top_cat.title())
            guidance = None
            meta = DAIRY_METADATA.get(top_cat, {
                "zone_code": "middle_shelf",
                "zone_name": "Middle Shelf",
                "zone_id": 1,
                "shelf_life_days": 7,
                "storage_tips": "Store refrigerated in packaging."
            })
            storage_tips = meta["storage_tips"]

        meta = DAIRY_METADATA.get(top_cat, {
            "zone_code": "middle_shelf",
            "zone_name": "Middle Shelf",
            "zone_id": 1,
            "shelf_life_days": 7,
            "storage_tips": "Store refrigerated in packaging."
        })

        now = datetime.utcnow()
        expiry_date = now + timedelta(days=meta["shelf_life_days"])

        return {
            "category": top_cat,
            "display_name": display_name,
            "confidence": round(top_conf, 4),
            "all_scores": all_scores,
            "suggested_shelf": meta["zone_name"],
            "suggested_zone_id": meta["zone_id"],
            "suggested_zone_code": meta["zone_code"],
            "typical_shelf_life_days": meta["shelf_life_days"],
            "suggested_expiry_date": expiry_date.isoformat(),
            "storage_tips": storage_tips,
            "user_guidance": guidance,
            "needs_manual_check": is_low_confidence,
            "is_dairy": True,
            "image_url": f"/storage/uploads/{os.path.basename(image_path)}",
            "freshness_note": "Packaging recognition identifies product category only. Freshness or expiry dates should be verified from package stamps."
        }

dairy_service = DairyModelService()
