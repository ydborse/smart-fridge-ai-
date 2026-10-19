import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image
import numpy as np
import torch
import torchvision.transforms as transforms
from app.config import settings
from app.models import ShelfLifeDefault, Zone
from app.services.ocr_service import ocr_engine
from app.services.dairy_classifier import dairy_service
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SUPPORTED_ITEMS = [
    "apple", "banana", "broccoli", "capsicum", "carrot", "onion", "orange",
    "packaged_milk", "packaged_paneer", "packaged_yogurt", "potato",
    "strawberry", "tomato", "unknown",
    "green chilli", "coriander", "cucumber", "lychee",
    "cheese", "packaged_cheese"
]

DAIRY_ITEMS = {
    "packaged_milk", "packaged_paneer", "packaged_yogurt", "packaged_cheese",
    "milk", "paneer", "yogurt", "curd", "dahi", "cheese"
}

FRESHNESS_CLASSES = ["Fresh", "Ripe", "Overripe", "Rotten", "Uncertain"]

# Default shelf lives in days
DEFAULT_SHELF_LIFE = {
    "apple": 21,
    "strawberry": 5,
    "lychee": 7,
    "banana": 5,
    "capsicum": 10,
    "green chilli": 14,
    "coriander": 5,
    "tomato": 7,
    "carrot": 28,
    "broccoli": 7,
    "orange": 21,
    "cucumber": 10,
    "potato": 28,
    "onion": 30,
    "packaged_milk": 5,
    "packaged_paneer": 7,
    "packaged_yogurt": 10,
    "packaged_cheese": 14,
    "milk": 5,
    "paneer": 7,
    "yogurt": 10,
    "cheese": 14,
    "curd": 7,
    "dahi": 7,
    "unknown": 0
}

ITEM_CATEGORIES = {
    "apple": ("Fruits", "fruit", "middle_shelf"),
    "strawberry": ("Fruits", "fruit", "top_shelf"),
    "lychee": ("Fruits", "fruit", "middle_shelf"),
    "banana": ("Fruits", "fruit", "top_shelf"),
    "orange": ("Fruits", "fruit", "middle_shelf"),
    "capsicum": ("Vegetables", "vegetable", "vegetable_drawer"),
    "green chilli": ("Vegetables", "vegetable", "vegetable_drawer"),
    "coriander": ("Vegetables", "vegetable", "vegetable_drawer"),
    "tomato": ("Vegetables", "vegetable", "middle_shelf"),
    "carrot": ("Vegetables", "vegetable", "vegetable_drawer"),
    "broccoli": ("Vegetables", "vegetable", "vegetable_drawer"),
    "cucumber": ("Vegetables", "vegetable", "vegetable_drawer"),
    "potato": ("Vegetables", "vegetable", "vegetable_drawer"),
    "onion": ("Vegetables", "vegetable", "vegetable_drawer"),
    "packaged_milk": ("Dairy", "packaged", "bottom_shelf"),
    "packaged_paneer": ("Dairy", "packaged", "middle_shelf"),
    "packaged_yogurt": ("Dairy", "packaged", "top_shelf"),
    "packaged_cheese": ("Dairy", "packaged", "middle_shelf"),
    "milk": ("Dairy", "packaged", "bottom_shelf"),
    "paneer": ("Dairy", "packaged", "middle_shelf"),
    "yogurt": ("Dairy", "packaged", "top_shelf"),
    "cheese": ("Dairy", "packaged", "middle_shelf"),
    "curd": ("Dairy", "packaged", "top_shelf"),
    "dahi": ("Dairy", "packaged", "top_shelf"),
    "unknown": ("Other", "other", "middle_shelf")
}

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

class FreshnessModelService:
    def __init__(self):
        self.food_model = None
        self.food_classes = []
        self.webcam_food_model = None
        self.webcam_food_classes = []
        self.freshness_model = None
        self.freshness_classes = []
        self.webcam_freshness_model = None
        self.webcam_freshness_classes = []
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.is_demo_mode = True
        self.load_models()

    def load_models(self):
        import torchvision.models as models

        # 1. Load Model 1: Food Item & Dairy Classifier
        food_path = getattr(settings, "FOOD_MODEL_PATH", None)
        if food_path and os.path.exists(food_path):
            try:
                ckpt = torch.load(food_path, map_location=self.device)
                self.food_classes = ckpt.get("classes", SUPPORTED_ITEMS)
                net = models.mobilenet_v2(weights=None)
                in_f = net.classifier[1].in_features
                net.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.3),
                    torch.nn.Linear(in_f, len(self.food_classes))
                )
                net.load_state_dict(ckpt.get("model_state_dict", ckpt))
                net.to(self.device)
                net.eval()
                self.food_model = net
                logger.info(f"Loaded trained Food & Dairy Classifier ({len(self.food_classes)} classes: {self.food_classes}).")
            except Exception as e:
                logger.warning(f"Could not load Food Classifier from {food_path}: {e}")
                self.food_model = None

        # 2. Load Model 2: Freshness Stage Classifier for Produce
        freshness_path = getattr(settings, "FRESHNESS_MODEL_PATH", None)
        if freshness_path and os.path.exists(freshness_path):
            try:
                ckpt = torch.load(freshness_path, map_location=self.device)
                self.freshness_classes = ckpt.get("classes", [c.lower() for c in FRESHNESS_CLASSES])
                net = models.mobilenet_v2(weights=None)
                in_f = net.classifier[1].in_features
                net.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.2),
                    torch.nn.Linear(in_f, len(self.freshness_classes))
                )
                net.load_state_dict(ckpt.get("model_state_dict", ckpt))
                net.to(self.device)
                net.eval()
                self.freshness_model = net
                logger.info(f"Loaded trained Freshness Classifier ({len(self.freshness_classes)} classes: {self.freshness_classes}).")
            except Exception as e:
                logger.warning(f"Could not load Freshness Classifier from {freshness_path}: {e}")
                self.freshness_model = None

        # 3. Load the separate 10-class webcam produce model.
        webcam_food_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..",
                "ml", "models", "webcam_food_candidate.pth"
            )
        )
        if os.path.exists(webcam_food_path):
            try:
                ckpt = torch.load(webcam_food_path, map_location=self.device)
                self.webcam_food_classes = ckpt.get("classes", [])
                if not self.webcam_food_classes:
                    raise ValueError("Candidate checkpoint has no class list.")

                net = models.mobilenet_v2(weights=None)
                in_f = net.classifier[1].in_features
                net.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.3),
                    torch.nn.Linear(in_f, len(self.webcam_food_classes))
                )
                net.load_state_dict(ckpt.get("model_state_dict", ckpt))
                net.to(self.device)
                net.eval()
                self.webcam_food_model = net
                logger.info(
                    "Loaded webcam produce candidate "
                    f"({len(self.webcam_food_classes)} classes: "
                    f"{self.webcam_food_classes})."
                )
            except Exception as e:
                logger.warning(f"Could not load webcam candidate: {e}")
                self.webcam_food_model = None
                self.webcam_food_classes = []
        else:
            logger.warning(
                f"Webcam candidate checkpoint not found: {webcam_food_path}"
            )

        # Load a separate binary freshness model for webcam recognition.
        webcam_freshness_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "..", "..",
                "ml", "models", "freshness_webcam_candidate.pth"
            )
        )
        if os.path.exists(webcam_freshness_path):
            try:
                ckpt = torch.load(
                    webcam_freshness_path, map_location=self.device
                )
                classes = ckpt.get("classes", ["fresh", "rotten"])
                if not classes:
                    raise ValueError("Candidate freshness checkpoint has no classes.")

                net = models.mobilenet_v2(weights=None)
                in_features = net.classifier[1].in_features
                net.classifier = torch.nn.Sequential(
                    torch.nn.Dropout(p=0.2),
                    torch.nn.Linear(in_features, len(classes))
                )
                net.load_state_dict(ckpt.get("model_state_dict", ckpt))
                net.to(self.device)
                net.eval()
                self.webcam_freshness_model = net
                self.webcam_freshness_classes = classes
                logger.info(
                    "Loaded webcam freshness candidate "
                    f"({classes})."
                )
            except Exception as e:
                logger.warning(f"Could not load webcam freshness candidate: {e}")
                self.webcam_freshness_model = None
                self.webcam_freshness_classes = []
        else:
            logger.warning(
                f"Webcam freshness candidate not found: {webcam_freshness_path}"
            )

        if self.food_model is not None:
            self.is_demo_mode = False

    def calculate_adjusted_shelf_life(self, item_name: str, freshness: str) -> int:
        base_shelf = DEFAULT_SHELF_LIFE.get(item_name.lower(), 7)
        if freshness == "Fresh":
            return base_shelf
        elif freshness == "Ripe":
            return max(2, int(base_shelf * 0.55))
        elif freshness == "Overripe":
            return max(1, int(base_shelf * 0.25))
        elif freshness == "Uncertain":
            return 1
        else:  # Rotten
            return 0

    def _analyze_produce_condition(self, img: Image.Image, item_name: str) -> Tuple[bool, str, float, Optional[str]]:
        """
        Analyzes produce for localized surface defects / necrotic lesions or widespread decay.
        Returns: (has_defect, condition_class, defect_metric, condition_notes)
        """
        arr = np.array(img.resize((160, 160)).convert("RGB")).astype(float)
        h, w, _ = arr.shape

        # Focus analysis on central produce area (15% to 85% of image)
        crop = arr[int(h*0.15):int(h*0.85), int(w*0.15):int(w*0.85)]
        r = crop[:, :, 0]
        g = crop[:, :, 1]
        b = crop[:, :, 2]
        lum = (r + g + b) / 3.0

        item = item_name.lower()

        # 1. Green Produce Localized Necrosis (Capsicum, Broccoli, Cucumber, Green Chilli)
        # Chlorophyll gives dominant green: g > r + 10, g > b + 10
        green_skin = (g > r + 10) & (g > b + 10) & (lum > 25)
        green_ratio = float(np.mean(green_skin))

        # Localized necrotic lesion / sunscald / brown rot:
        # Chlorophyll degradation leads to brownish pigment where R >= G - 5 and Lum < 95
        necrotic_patch = (r >= g - 5) & (r > b + 8) & (lum < 95) & (lum > 20) & (b < 70)
        necrotic_ratio = float(np.mean(necrotic_patch))

        if (green_ratio > 0.12 and necrotic_ratio >= 0.04) or (item in ['capsicum', 'cucumber', 'broccoli', 'green chilli'] and necrotic_ratio >= 0.08):
            pct = round(necrotic_ratio * 100, 1)
            if necrotic_ratio >= 0.15:
                notes = (
                    f"Extensive dark necrotic rot lesion detected on {item} ({pct}% area defect). "
                    "Severe tissue breakdown — do not store or consume."
                )
                return True, "Rotten", necrotic_ratio, notes
            else:
                notes = (
                    f"Visible dark necrotic patch detected on {item} ({pct}% area defect). "
                    "Evidence is consistent with localized sunscald, bruising, or surface damage. "
                    "Model cannot definitively confirm interior spoilage — inspect item before consumption."
                )
                return True, "Uncertain", necrotic_ratio, notes

        # 2. General produce widespread decay / mold / deep rotting breakdown
        # Deep sepia rot across non-green produce: browning / darkening with brownish color signature
        is_sepia_rot = (r > g) & (g > b) & (r < 170) & (r - g < 45) & (g - b > 15) & (b < 70)
        decay_ratio = float(np.mean(is_sepia_rot))

        # Check if this item is naturally bright/orange/red (e.g., orange capsicum, carrot, tomato, apple)
        is_naturally_red_orange = (r.mean() > 130) and (r.mean() > g.mean() * 1.3)
        if not is_naturally_red_orange:
            if decay_ratio >= 0.35:
                return True, "Rotten", decay_ratio, f"Extensive surface decay and tissue breakdown detected ({decay_ratio:.1%})."
            elif decay_ratio >= 0.20:
                return True, "Overripe", decay_ratio, f"Pronounced surface softening or browning detected ({decay_ratio:.1%})."

        return False, "Fresh", 0.0, None

    def predict(
        self, image_path: str, db: Session, use_webcam_model: bool = False
    ) -> Dict[str, Any]:
        """
        Dual-capability inference:
        1. Model 1 (Food Item & Dairy Classifier): Identifies produce / packaged dairy or 'unknown'
        2. If packaged dairy: routes strictly through Model 2 (OCR Date Engine),
           suppresses visual produce freshness, and computes date-based status.
        3. If produce: evaluates visual freshness stage via Freshness Classifier + localized defect detection.
        4. If unknown: flags for user manual check.
        """
        img = Image.open(image_path).convert("RGB")
        tensor = transform(img).unsqueeze(0).to(self.device)

        predictions: List[Dict[str, Any]] = []
        active_model = (
            self.webcam_food_model if use_webcam_model else self.food_model
        )
        active_classes = (
            self.webcam_food_classes if use_webcam_model else self.food_classes
        )
        use_candidate_freshness = (
            use_webcam_model and self.webcam_freshness_model is not None
        )
        active_freshness_model = (
            self.webcam_freshness_model if use_candidate_freshness
            else self.freshness_model
        )
        active_freshness_classes = (
            self.webcam_freshness_classes if use_candidate_freshness
            else self.freshness_classes
        )

        if active_model:
            with torch.inference_mode():
                food_out = active_model(tensor)
                food_probs = torch.softmax(food_out, dim=1)[0].cpu().numpy()
                top_food_indices = np.argsort(food_probs)[::-1][:3]
                pred_item = active_classes[top_food_indices[0]]
                food_conf = float(food_probs[top_food_indices[0]])

                is_dairy = pred_item in DAIRY_ITEMS
                is_unknown = pred_item == "unknown" or (
                    use_webcam_model and food_conf < 0.60
                )

                # Consult specialized Dairy Packaging Classifier when dairy or unknown is suspected
                dairy_condition_note = None
                if (not use_webcam_model) and dairy_service and getattr(dairy_service, "is_loaded", False):
                    try:
                        dairy_res = dairy_service.predict(image_path)
                        d_cat = dairy_res.get("category", "")
                        d_conf = dairy_res.get("confidence", 0.0)

                        if is_dairy:
                            canonical_cat = f"packaged_{d_cat}" if not d_cat.startswith("packaged_") else d_cat
                            pred_item = canonical_cat
                            food_conf = d_conf
                            dairy_condition_note = dairy_res.get("storage_tips")
                        elif is_unknown and d_conf >= 0.52:
                            canonical_cat = f"packaged_{d_cat}" if not d_cat.startswith("packaged_") else d_cat
                            pred_item = canonical_cat
                            food_conf = d_conf
                            is_dairy = True
                            is_unknown = False
                            dairy_condition_note = dairy_res.get("storage_tips")
                    except Exception as e:
                        logger.warning(f"Dairy classifier enhancement skipped: {e}")

                # Route A: Packaged Dairy -> OCR Printed Date Engine
                if is_dairy:
                    ocr_res = ocr_engine.process_image(image_path, product_item=pred_item)
                    top = self._format_prediction(
                        pred_item,
                        freshness=ocr_res.get("date_status", "Uncertain"),
                        confidence=food_conf,
                        db=db,
                        is_dairy=True,
                        is_unknown=False,
                        ocr_data=ocr_res,
                        freshness_confidence=ocr_res.get("confidence", 0.85),
                        condition_notes=dairy_condition_note
                    )
                    predictions.append(top)

                # Route B: Unknown / Unsupported object
                elif is_unknown:
                    top = self._format_prediction(
                        "unknown",
                        freshness="Uncertain",
                        confidence=food_conf,
                        db=db,
                        is_dairy=False,
                        is_unknown=True,
                        freshness_confidence=0.50,
                        condition_notes="Object not recognized as supported produce or dairy. Please verify manually."
                    )
                    predictions.append(top)

                # Route C: Produce
                else:
                    has_defect, defect_stage, defect_metric, defect_notes = self._analyze_produce_condition(img, pred_item)
                    fresh_conf = 0.85

                    if active_freshness_model:
                        fresh_out = active_freshness_model(tensor)
                        fresh_probs = torch.softmax(fresh_out, dim=1)[0].cpu().numpy()
                        top_fresh_idx = int(np.argmax(fresh_probs))
                        raw_fresh = active_freshness_classes[top_fresh_idx].capitalize()
                        fresh_conf = float(fresh_probs[top_fresh_idx])

                        # Low-confidence webcam freshness predictions require manual inspection.
                        if use_webcam_model and fresh_conf < 0.60:
                            final_freshness = "Uncertain"
                            if not defect_notes:
                                defect_notes = (
                                    f"Freshness confidence is low ({fresh_conf:.1%}). "
                                    "Please inspect the item manually."
                                )
                        # A strong Rotten prediction is retained.
                        elif raw_fresh == "Rotten" and fresh_conf >= 0.70:
                            final_freshness = "Rotten"
                            if not defect_notes:
                                defect_notes = (
                                    f"Significant surface decay, fungal breakdown, or rot detected on {pred_item} "
                                    f"({fresh_conf:.1%} confidence). Do not store or consume."
                                )
                        # 2. If severe localized defect detected by computer vision (>= 15% necrotic area), classify Rotten
                        elif has_defect and defect_stage == "Rotten":
                            final_freshness = "Rotten"
                        # 3. If localized defect (4-15% necrotic patch/sunscald) on otherwise fresh-looking produce, flag for inspection
                        elif has_defect:
                            final_freshness = defect_stage  # "Uncertain"
                            fresh_conf = max(fresh_conf, 0.85)
                        # 4. Otherwise use ML model prediction directly
                        else:
                            final_freshness = raw_fresh
                    else:
                        final_freshness = defect_stage if has_defect else "Fresh"
                        fresh_conf = 0.85

                    top = self._format_prediction(
                        pred_item,
                        freshness=final_freshness,
                        confidence=food_conf,
                        db=db,
                        is_dairy=False,
                        is_unknown=False,
                        freshness_confidence=fresh_conf,
                        condition_notes=defect_notes
                    )
                    predictions.append(top)

                # Runner-up predictions
                for idx in top_food_indices[1:]:
                    if use_webcam_model and food_conf < 0.60:
                        break
                    runner_item = active_classes[idx]
                    runner_conf = float(food_probs[idx])
                    if runner_item != "unknown":
                        predictions.append(self._format_prediction(
                            runner_item,
                            freshness="Fresh",
                            confidence=runner_conf,
                            db=db,
                            is_dairy=(runner_item in DAIRY_ITEMS),
                            is_unknown=False,
                            freshness_confidence=0.80
                        ))

        else:
            # Model unavailable or failed to load - do not fabricate a Fresh result
            top = self._format_prediction(
                "unknown",
                "Uncertain",
                0.0,
                db,
                is_unknown=True,
                freshness_confidence=0.0,
                condition_notes="AI model unavailable or failed to load. Please enter food details manually."
            )
            predictions.append(top)

        return {
            "top_prediction": predictions[0],
            "all_predictions": predictions,
            "image_url": f"/storage/uploads/{os.path.basename(image_path)}",
            "is_demo_mode": self.is_demo_mode,
            "disclaimer": "Predictions are assistive and not a food safety guarantee."
        }

    def _format_prediction(
        self,
        item_name: str,
        freshness: str,
        confidence: float,
        db: Session,
        is_dairy: bool = False,
        is_unknown: bool = False,
        ocr_data: Optional[Dict[str, Any]] = None,
        freshness_confidence: Optional[float] = None,
        condition_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        raw_key = item_name.lower()
        cat, item_type, rec_zone_code = ITEM_CATEGORIES.get(raw_key, ("Vegetables", "vegetable", "vegetable_drawer"))
        
        # Check custom DB zone or shelf life if present
        shelf_default = db.query(ShelfLifeDefault).filter(ShelfLifeDefault.item_name == raw_key).first()
        base_shelf = shelf_default.typical_shelf_life_days if shelf_default else DEFAULT_SHELF_LIFE.get(raw_key, 7)
        if shelf_default:
            rec_zone_code = shelf_default.recommended_zone_code

        zone = db.query(Zone).filter(Zone.code == rec_zone_code).first() or db.query(Zone).first()

        ocr_info = ocr_data or {}

        if is_dairy:
            if ocr_info.get("success") and ocr_info.get("original_parsed_date"):
                expiry_date = ocr_info["original_parsed_date"]
                adj_shelf = max(0, (expiry_date.date() - datetime.utcnow().date()).days)
            else:
                adj_shelf = base_shelf
                expiry_date = datetime.utcnow() + timedelta(days=adj_shelf)

            return {
                "item_name": item_name.replace("_", " ").title(),
                "freshness_class": freshness,
                "confidence": round(confidence, 3),
                "freshness_confidence": round(freshness_confidence, 3) if freshness_confidence is not None else round(confidence, 3),
                "condition_notes": condition_notes,
                "typical_shelf_life_days": adj_shelf,
                "suggested_expiry_date": expiry_date,
                "suggested_zone_id": zone.id if zone else 1,
                "suggested_zone_name": zone.name if zone else "Bottom Shelf",
                "category": cat,
                "item_type": item_type,
                "needs_manual_check": (confidence < 0.60) or ocr_info.get("needs_manual_check", False),
                "is_dairy": True,
                "is_unknown": False,
                "brand": ocr_info.get("brand"),
                "extracted_date": ocr_info.get("extracted_date"),
                "date_type": ocr_info.get("date_type"),
                "date_status": ocr_info.get("date_status"),
                "ocr_confidence": ocr_info.get("confidence", 0.0),
                "is_estimated": ocr_info.get("is_estimated", False),
                "detected_text": ocr_info.get("detected_text")
            }

        elif is_unknown:
            return {
                "item_name": "Unknown / Unsupported",
                "freshness_class": "Uncertain",
                "confidence": round(confidence, 3),
                "freshness_confidence": round(freshness_confidence, 3) if freshness_confidence is not None else 0.50,
                "condition_notes": condition_notes,
                "typical_shelf_life_days": 0,
                "suggested_expiry_date": datetime.utcnow(),
                "suggested_zone_id": zone.id if zone else 1,
                "suggested_zone_name": zone.name if zone else "Middle Shelf",
                "category": "Other",
                "item_type": "other",
                "needs_manual_check": True,
                "is_dairy": False,
                "is_unknown": True
            }

        else:
            # Produce
            adj_shelf = self.calculate_adjusted_shelf_life(raw_key, freshness)
            expiry_date = datetime.utcnow() + timedelta(days=adj_shelf)

            return {
                "item_name": item_name.capitalize(),
                "freshness_class": freshness,
                "confidence": round(confidence, 3),
                "freshness_confidence": round(freshness_confidence, 3) if freshness_confidence is not None else None,
                "condition_notes": condition_notes,
                "typical_shelf_life_days": adj_shelf,
                "suggested_expiry_date": expiry_date,
                "suggested_zone_id": zone.id if zone else 1,
                "suggested_zone_name": zone.name if zone else "Vegetable Drawer",
                "category": cat,
                "item_type": item_type,
                "needs_manual_check": (confidence < 0.60) or (freshness == "Uncertain"),
                "is_dairy": False,
                "is_unknown": False
            }

ml_service = FreshnessModelService()
