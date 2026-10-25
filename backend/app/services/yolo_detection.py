import base64
import logging
import os
import tempfile

import cv2
from sqlalchemy.orm import Session
from ultralytics import YOLO

from app.services.ml_inference import ml_service

logger = logging.getLogger(__name__)

# These are food-related classes available in the pretrained COCO model.
# This does not include every fruit or vegetable.
FOOD_RELATED_CLASSES = {
    "apple",
    "banana",
    "orange",
    "broccoli",
    "carrot",
    "sandwich",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "bottle",
    "wine glass",
    "cup",
    "bowl",
    "tomato",
    "cucumber",
}
# Only accept the existing food classifier's label when it is
# confident enough. This threshold needs real-image validation.
FOOD_CLASSIFICATION_THRESHOLD = 0.45


class YoloDetectionService:
    def __init__(self):
        self.model = None

    def _get_model(self):
        if self.model is None:
            model_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
            logger.info("Loading YOLO model: %s", model_path)
            self.model = YOLO(model_path)
            logger.info("YOLO object-detection model loaded.")

        return self.model

    def _refine_food_label(
        self,
        crop,
        db: Session,
        yolo_label: str,
    ):
        """Use the existing food classifier to refine a YOLO label."""
        crop_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".jpg",
                delete=False,
            ) as temp_file:
                crop_path = temp_file.name

            if not cv2.imwrite(crop_path, crop):
                return yolo_label, None, "yolo"

            # Use the original food classifier, not the 10-class
            # webcam candidate. The original model includes tomato
            # and onion among its trained classes.
            result = ml_service.predict(
                crop_path,
                db,
                use_webcam_model=False,
            )

            top = result.get("top_prediction", {})
            predicted_label = str(
                top.get("item_name", "unknown")
            ).strip().lower()
            confidence = float(top.get("confidence", 0.0) or 0.0)

            if (
                predicted_label != "unknown"
                and confidence >= FOOD_CLASSIFICATION_THRESHOLD
            ):
                return (
                    predicted_label.replace("_", " "),
                    confidence,
                    "food_classifier",
                )

            return "uncertain food", None, "uncertain"

        except Exception:
            logger.exception(
                "Food-label refinement failed; keeping YOLO label."
            )
            return yolo_label, None, "yolo"

        finally:
            if crop_path and os.path.exists(crop_path):
                try:
                    os.remove(crop_path)
                except OSError:
                    logger.warning(
                        "Could not remove temporary crop: %s",
                        crop_path,
                    )

    def predict(self, image_path: str, db: Session) -> dict:
        results = self._get_model().predict(
         source=image_path,
         conf=0.45,
         iou=0.5,
         imgsz=640,
         verbose=False,
)

        if not results:
            raise RuntimeError("YOLO returned no inference results.")

        result = results[0]
        image = result.orig_img.copy()
        height, width = image.shape[:2]
        detections = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                yolo_label = result.names[class_id]
                detection_confidence = float(box.conf[0].item())

                x1, y1, x2, y2 = [
                    int(round(value))
                    for value in box.xyxy[0].tolist()
                ]

                # Keep coordinates within the image boundaries.
                x1 = max(0, min(x1, width - 1))
                x2 = max(0, min(x2, width))
                y1 = max(0, min(y1, height - 1))
                y2 = max(0, min(y2, height))

                crop = image[y1:y2, x1:x2]

                if crop.size == 0:
                    continue

                # Trust the custom YOLO model's trained class prediction.
                final_label = yolo_label
                class_confidence = None
                label_source = "custom_yolo"

                label = f"{final_label} {detection_confidence:.0%}"

                if class_confidence is not None:
                    label += f" | class {class_confidence:.0%}"

                color = (0, 190, 90)

                cv2.rectangle(
                    image,
                    (x1, y1),
                    (x2, y2),
                    color,
                    2,
                )

                cv2.putText(
                    image,
                    label,
                    (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                    cv2.LINE_AA,
                )

                detections.append({
                    "class_name": final_label,
                    "confidence": round(detection_confidence, 4),
                    "yolo_class": yolo_label,
                    "label_source": label_source,
                    "classification_confidence": (
                        round(class_confidence, 4)
                        if class_confidence is not None
                        else None
                    ),
                    "bbox": {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    },
                })

        success, encoded = cv2.imencode(
            ".jpg",
            image,
            [int(cv2.IMWRITE_JPEG_QUALITY), 90],
        )

        if not success:
            raise RuntimeError("Could not encode the annotated image.")

        annotated_image = (
            "data:image/jpeg;base64,"
            + base64.b64encode(encoded.tobytes()).decode("ascii")
        )

        return {
            "model": "Custom YOLO 10-class food detector",
            "image_width": width,
            "image_height": height,
            "detections": detections,
            "annotated_image": annotated_image,
            "message": (
                f"Detected {len(detections)} supported object(s)."
                if detections
                else (
                    "No supported food objects detected. "
                    "The pretrained YOLO model cannot detect every food."
                )
            ),
        }


yolo_detection_service = YoloDetectionService()