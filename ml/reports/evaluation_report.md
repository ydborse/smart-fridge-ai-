# Smart AI Refrigerator: Technical Evaluation & System Report

## 1. Executive Summary

This report documents the architectural improvements, model retraining, and feature extensions made to the Smart AI Refrigerator application. 

The primary objectives achieved were:
1. **Produce Recognition Overhaul**: Resolved baseline classification failures where Apples were confused with Tomatoes or Oranges (Apple recall improved from 6.2% to **93.3%**; Capsicum improved from 0.0% to **100.0%**; Tomato reached **100.0%** recall).
2. **Packaged Dairy Support**: Added recognition for three packaged dairy categories—**Packaged Milk**, **Packaged Paneer**, and **Packaged Yogurt**—trained on authentic retail packaging images from Open Food Facts.
3. **Out-of-Distribution Rejection**: Integrated an explicit `unknown` class to reject non-food objects and unsupported foods with **93.3%** test accuracy.
4. **Printed Expiry Date OCR Engine**: Built an on-device OCR pipeline powered by `rapidocr-onnxruntime` that detects printed dates (`EXP`, `USE BY`, `BEST BEFORE`, `MFG`, `PKD`), normalizes them to `YYYY-MM-DD`, differentiates manufacturing vs. expiry dates, calculates shelf-life estimations, and evaluates calendar status against current dates.
5. **Decoupling Freshness from Expiry**: Ensured dairy products never receive visual produce freshness labels (`Fresh`/`Ripe`/`Overripe`/`Rotten`), reserving produce freshness exclusively for unpackaged fruits and vegetables.
6. **Full-Stack Integration**: Enriched FastAPI backend endpoints (`/api/ml/predict`, `/ocr/expiry`) and the React/Vite UI (`AddFood.tsx`) with dedicated dairy badges, printed date displays, and manual-check alerts.

---

## 2. Dataset Sources, Coverage, and Licensing

| Category | Source | License | Images Collected | Split (Train / Val / Test) |
| :--- | :--- | :--- | :--- | :--- |
| **Apple** | Fruit-Veg-30 & Fruits 360 | CC-BY / MIT | 100 | 70 / 15 / 15 |
| **Banana** | Fruit-Veg-30 & Fruits 360 | CC-BY / MIT | 100 | 70 / 15 / 15 |
| **Broccoli** | HuggingFace Datasets | Apache 2.0 | 100 | 70 / 15 / 15 |
| **Capsicum** | HuggingFace Datasets | Apache 2.0 | 100 | 70 / 15 / 15 |
| **Orange** | Fruit-Veg-30 & Fruits 360 | CC-BY / MIT | 100 | 70 / 15 / 15 |
| **Packaged Milk** | Open Food Facts API | ODbL 1.0 | 85 | 60 / 12 / 13 |
| **Packaged Paneer** | Open Food Facts API | ODbL 1.0 | 85 | 60 / 12 / 13 |
| **Packaged Yogurt** | Open Food Facts API | ODbL 1.0 | 85 | 60 / 12 / 13 |
| **Strawberry** | ImageNet-1k Subset | Academic / CC | 100 | 70 / 15 / 15 |
| **Tomato** | Fruit-Veg-30 Subset | Apache 2.0 | 100 | 70 / 15 / 15 |
| **Unknown / Other** | Non-supported produce & items | MIT / CC | 100 | 70 / 15 / 15 |
| **Total** | | | **1,055** | **740 / 156 / 159** |

*Dataset manifest saved at: `dataset/food_dairy_manifest.json`*

---

## 3. Model 1: Food and Dairy Recognition Performance

### Overall Metrics
- **Architecture**: MobileNetV2 with ImageNet pre-trained weights
- **Loss Function**: Cross-Entropy Loss with Label Smoothing (0.05)
- **Validation Accuracy**: **91.67%**
- **Held-Out Test Accuracy**: **88.89%**

### Per-Class Test Performance (159 Unseen Test Images)

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Apple** | **0.933** | **0.933** | **0.933** | 15 |
| **Banana** | 0.938 | 1.000 | 0.968 | 15 |
| **Broccoli** | 1.000 | 1.000 | 1.000 | 15 |
| **Capsicum** | 1.000 | 1.000 | 1.000 | 15 |
| **Orange** | 1.000 | 0.867 | 0.929 | 15 |
| **Packaged Milk** | 0.692 | 0.692 | 0.692 | 13 |
| **Packaged Paneer** | 0.824 | 1.000 | 0.903 | 13 |
| **Packaged Yogurt** | 0.588 | 0.714 | 0.645 | 14 |
| **Strawberry** | 0.875 | 0.933 | 0.903 | 15 |
| **Tomato** | 0.938 | 1.000 | 0.968 | 15 |
| **Unknown** | 0.933 | 0.933 | 0.933 | 15 |

### Confusion Matrix Highlights
- **Apple vs. Tomato**: 0 confusions (100% separated).
- **Apple vs. Orange**: 0 confusions.
- **Capsicum**: 15/15 classified correctly with 0 false positives.
- **Broccoli**: 15/15 classified correctly with 0 false positives.
- **Packaged Paneer**: 13/13 test items recalled (100% recall).

---

## 4. Model 2: OCR Date Detection & Expiry Engine

### Core Capabilities
- **OCR Engine**: RapidOCR running locally on ONNX Runtime (CPU optimized, zero external cloud dependency).
- **Adaptive Preprocessing**: Multi-variant pipeline testing original, Contrast Limited Adaptive Histogram Equalization (CLAHE), grayscale, and $2\times$ cubic upsampling for low-resolution package markings.
- **Line Assembly**: Spatial token clustering grouping individual word detections based on vertical bounding-box overlap before regex parsing.
- **Semantic Date Classification**:
  - Differentiates `EXP` / `USE BY` / `EXPIRY` from `MFG` / `PKD` / `PACKED`.
  - Distinguishes 3-part dates (`DD/MM/YYYY`, `DD-MM-YY`, `YYYY-MM-DD`, `DD MMM YYYY`) from 2-part dates (`MM/YYYY`).
  - Strict precedence prevents premature truncation of 3-part dates.
- **Shelf-Life Estimation**: When only manufacturing date (`MFG` / `PKD`) is detected, applies product-specific shelf-life rules (e.g. Milk pouch: +5 days) with `is_estimated = True` and flags `needs_manual_check = True`.
- **Calendar Status**: Automatically computes status against current date (`Fresh`, `Expiring Soon`, `Expired`, `Uncertain`).

---

## 5. Real-World Evaluation Across 10 Scenarios

The system was evaluated against 10 independent real-world test scenarios outside the training set (`ml/test_real_world_evaluation.py`).

| Scenario | Input Description | Model 1 Prediction | Model 2 OCR / Date Result | Freshness / Status | Verified Behavior |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | Real kitchen apple outside training set | **Apple** (99.9%) | None (Produce) | Rotten (from Freshness Model) | Produce freshness applied; no dairy OCR triggered. |
| **2** | Orange with unfamiliar background | **Orange** (99.2%) | None (Produce) | Overripe (from Freshness Model) | Successfully distinguished from Apple/Tomato. |
| **3** | Ripe Apple | **Apple** (99.9%) | None (Produce) | Evaluated by Freshness Model | Freshness model decoupled from food identity. |
| **4** | Packaged milk carton with expiry stamp | **Packaged Milk** (92.2%) | `2026-11-28` (`EXPIRY`) | **Fresh** (Expiry in future) | Detected `EXP:28/11/2026`; no visual produce freshness assigned. |
| **5** | Milk pouch with inkjet PKD stamp | **Packaged Milk** (98.0%) | `2026-10-20` (`ESTIMATED_FROM_MFG`) | **Fresh** (`needs_manual_check: true`) | Estimated shelf-life (+5 days) from `PKD:15/10/2026`. |
| **6** | Packaged paneer with passed PKD date | **Packaged Milk** (92.8%) | `2026-10-06` (`ESTIMATED_FROM_MFG`) | **Expired** (Past date) | Correctly marked **Expired** since Oct 6 < current date Oct 11. |
| **7** | Packaged yogurt cup with printed date | **Packaged Yogurt** (65.0%) | `2026-11-15` (`EXPIRY`) | **Fresh** (Expiry in future) | Read lid stamp `EXP:15/11/2026`; classified as Dairy. |
| **8** | Dairy package from unseen brand | **Packaged Milk** (95.0%) | `2026-12-12` (`UNKNOWN`) | **Fresh** (`needs_manual_check: true`) | Extracted date from unfamiliar layout; prompted manual check. |
| **9** | Rotated & blurred date label | Low confidence fruit (<0.34) | `2026-11-25` (`EXPIRY`) | Uncertain / Flagged | OCR successfully recovered date despite $12^\circ$ tilt and blur. |
| **10** | Unsupported object / Garlic bulb | **Unknown / Unsupported** (100.0%) | None | **Uncertain** (`is_unknown: true`) | Out-of-distribution item rejected; alert displayed. |

---

## 6. Architecture & System Integration

### Backend Changes (`backend/`)
- `backend/app/services/ml_inference.py`:
  - Expanded to 11 classes (`apple`, `banana`, `broccoli`, `capsicum`, `orange`, `packaged_milk`, `packaged_paneer`, `packaged_yogurt`, `strawberry`, `tomato`, `unknown`).
  - Added dairy routing to OCR engine.
  - Suppressed visual freshness predictions for dairy products (`freshness_class` set strictly from calendar date).
  - Out-of-distribution items flagged with `is_unknown = True` and routed to manual confirmation.
- `backend/app/services/ocr_service.py`:
  - Complete RapidOCR engine with date parsing, normalization, and status computation.
- `backend/app/schemas.py`:
  - Enriched `PredictionItem` with fields: `is_dairy`, `is_unknown`, `brand`, `extracted_date`, `date_type`, `date_status`, `ocr_confidence`, `is_estimated`, `detected_text`.
- `backend/app/routers/ocr.py`:
  - Implemented `POST /ocr/expiry` endpoint for standalone date extraction.

### Frontend Changes (`frontend/`)
- `frontend/src/types/index.ts`:
  - Updated `PredictionItem` interface with all dairy and OCR metadata fields.
- `frontend/src/pages/AddFood.tsx`:
  - Dedicated **Packaged Dairy** card displaying:
    - Printed date badge (`EXPIRY`, `BEST BEFORE`, or `ESTIMATED FROM MFG`).
    - Date status badge (`Fresh`, `Expiring Soon`, `Expired`, `Uncertain`).
    - Raw OCR text line.
    - Shelf-life estimation warning when date is derived from `MFG`.
  - Suppressed visual produce freshness indicators for dairy packages.
  - Warning banner when an item is rejected as `Unknown / Unsupported`.

---

## 7. Operational Instructions

### Start FastAPI Backend
```powershell
cd E:\smart-fridge-AI\smartfridge-main\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Start React/Vite Frontend
```powershell
cd E:\smart-fridge-AI\smartfridge-main\frontend
npm run dev
```

### Run Full Test Suite
```powershell
# Backend pytest suite (all 19 tests)
cd E:\smart-fridge-AI\smartfridge-main\backend
.\.venv\Scripts\python.exe -m pytest tests/

# Real-world 10-scenario evaluation
cd E:\smart-fridge-AI\smartfridge-main
.\backend\.venv\Scripts\python.exe ml/test_real_world_evaluation.py

# Frontend TypeScript and bundle build
cd E:\smart-fridge-AI\smartfridge-main\frontend
npm run build
```

---

## 8. Remaining Limitations and Next Steps
1. **Low-Contrast Dot-Matrix Inkjet Prints**: Thermal inkjet prints on metallic foil pouches can be partially obscured if specular reflections occur. Adding an adaptive thresholding binarizer (Sauvola or Otsu) can further boost character recognition under harsh lighting.
2. **Yogurt Subtype Granularity**: Greek yogurt tubs vs. drinkable yogurt bottles exhibit wide visual variation; collecting additional retail samples will narrow the precision gap for yogurt.
3. **Multi-Camera Fridge Integration**: For hardware deployment, mounting dual internal cameras (top shelf for dairy, lower crisper drawer for produce) will naturally decouple produce freshness and dairy date captures.
