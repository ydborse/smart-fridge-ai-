import os
import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.services.dairy_classifier import dairy_service

client = TestClient(app)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_DIR = os.path.join(BASE_DIR, "datasets", "dairy_packaging")

def test_dairy_service_initialization():
    """Verify that the DairyModelService loaded the MobileNetV2 checkpoint."""
    assert dairy_service is not None
    assert dairy_service.is_loaded is True
    assert set(dairy_service.classes) == {"cheese", "milk", "paneer", "yogurt"}

def _find_first_image(dir_path: str) -> str:
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                return os.path.join(root, f)
    raise FileNotFoundError(f"No image files found in {dir_path}")

def test_dairy_service_prediction_on_real_samples():
    """Verify inference on samples from each of the 4 test categories."""
    for cat in ["milk", "yogurt", "paneer", "cheese"]:
        cat_dir = os.path.join(DATASET_DIR, "test", cat)
        assert os.path.exists(cat_dir), f"Directory {cat_dir} does not exist"
        sample_path = _find_first_image(cat_dir)
        res = dairy_service.predict(sample_path)

        assert "category" in res
        assert res["category"] in dairy_service.classes
        assert "confidence" in res
        assert 0.0 <= res["confidence"] <= 1.0
        assert "all_scores" in res
        assert len(res["all_scores"]) == 4
        assert "suggested_shelf" in res
        assert "typical_shelf_life_days" in res
        assert res["is_dairy"] is True
        assert "freshness_note" in res

def test_dairy_endpoint_success():
    """Verify POST /api/predict/dairy returns 200 with schema-compliant payload."""
    test_img_path = os.path.join(DATASET_DIR, "test", "milk")
    sample_file = _find_first_image(test_img_path)

    with open(sample_file, "rb") as f:
        response = client.post(
            "/api/predict/dairy",
            files={"file": ("test_milk.jpg", f.read(), "image/jpeg")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert "display_name" in data
    assert "confidence" in data
    assert "all_scores" in data
    assert "suggested_shelf" in data
    assert "typical_shelf_life_days" in data
    assert "suggested_expiry_date" in data
    assert data["is_dairy"] is True

def test_dairy_endpoint_unsupported_file():
    """Verify POST /api/predict/dairy rejects unsupported file formats."""
    dummy_txt = io.BytesIO(b"Hello world, not an image")
    response = client.post(
        "/api/predict/dairy",
        files={"file": ("document.txt", dummy_txt, "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
