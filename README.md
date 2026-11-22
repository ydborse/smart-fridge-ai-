# Smart Fridge AI

An intelligent household food-management and freshness-monitoring web application built with **React 19, TypeScript, FastAPI, PostgreSQL 15, Ultralytics YOLOv8n, and PyTorch MobileNetV2**.

Smart Fridge AI helps everyday households track refrigerator inventory, monitor shelf zones, detect produce and freshness through live webcam AI, discover meal ideas from available ingredients, manage shopping lists, and receive grouped expiry/spoilage alerts via Email and Telegram.

## Key Features

- **Household Dashboard:** At-a-glance inventory summary (Total, Fresh, Use Soon, Past Date), quick **Scan Food** and **Add Manually** actions, and live shelf telemetry charts.
- **Refrigerator Zones & Digital Twin:** Visual shelf layout (Top Shelf, Middle Shelf, Bottom Shelf, Vegetable Drawer, Freezer, Door Shelf) with temperature/humidity tracking, health index, and ethylene gas compatibility checks.
- **Live Webcam & Two-Stage AI Recognition:** Real-time **YOLOv8n** object detection (`agnostic_nms=True`, 2-of-3 frame consensus label stabilization) paired with **MobileNetV2** crop refinement, ensemble agreement fusion, **Top-3 class probability bars**, and one-click **Save to Fridge**.
- **Produce Freshness & Dairy Packaging AI:** Separate MobileNetV2 pipelines for produce freshness (`Fresh` / `Rotten` + RGB defect checks) and packaged dairy (`Milk`, `Yogurt`, `Paneer`, `Cheese`) with **Open Food Facts** barcode lookup and **OCR expiry-date scanning**.
- **Meal Ideas & Shopping List:** Suggests meals matched to currently tracked inventory and manages missing grocery items persistently.
- **Consumption & Waste Analytics (INR):** 5-month consumption vs. waste trend chart, pantry efficiency score, estimated value consumed/lost in `₹`, and activity timeline.
- **Grouped Smart Alerts (Email, Telegram & PWA):** Automated `APScheduler` engine delivering grouped food summaries (no per-item spam), Quiet Hours support (`22:00–07:00`), and on-demand live summary triggers from Settings.
- **Dual Theme UI:** Warm editorial Light Mode and **Carbon Black + Emerald** Dark Mode persisted via `localStorage`, plus route-level code splitting (`React.lazy`).

## Machine Learning Models & Verified Metrics

| Model | Architecture | Task | Verified Test Metrics |
| :--- | :--- | :--- | :--- |
| **Custom Food Detector** | Ultralytics YOLOv8n (`ten_class_food_v1`) | 10-class produce detection & bounding boxes | **82.6%** Precision · **81.0%** Recall · **87.1%** mAP@50 · **68.0%** mAP@50–95 |
| **Freshness Classifier** | PyTorch MobileNetV2 | Binary produce freshness (`fresh` / `rotten`) | **92.5%** Accuracy |
| **Food & Dairy Classifier** | PyTorch MobileNetV2 | 15-class produce & dairy classification | **86.2%** Accuracy |
| **Webcam Produce Candidate** | PyTorch MobileNetV2 | 10-class cropped produce benchmark | **96.6%** Accuracy |
| **Dairy Packaging Classifier** | PyTorch MobileNetV2 | 4-class retail dairy packaging | **65.3%** Accuracy (paired with Barcode + OCR) |

### Training Dataset Splits

| Dataset | Train | Validation | Test | Total Images | Split |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Freshness Classifier (`freshness_webcam_splits`) | 14,724 | 3,156 | 3,156 | **21,036** | 70 / 15 / 15 |
| 10-Class Produce (`webcam_food_splits`) | 8,233 | 1,761 | 1,774 | **11,768** | 70 / 15 / 15 |
| 10-Class YOLO (`fruits_vegetables_10class_yolo`) | 1,426 | 178 | 178 | **1,782** | 80 / 10 / 10 |

## Tech Stack

- **Frontend:** React 19, TypeScript, Tailwind CSS 3.4, Vite, React Router, Lucide React, Recharts, Nginx
- **Backend:** Python 3.11, FastAPI, Uvicorn, SQLAlchemy, JWT Auth, APScheduler
- **Database:** PostgreSQL 15 (Alpine)
- **AI / CV:** PyTorch, Torchvision (MobileNetV2), Ultralytics YOLOv8n, OpenCV, Pillow
- **Infrastructure:** Docker, Docker Compose

## Quick Start (Docker Compose)

1. Copy `backend/.env.example` to `backend/.env` and configure your SMTP email, Telegram Bot token/chat ID, and `YOLO_MODEL_PATH`.
2. Start all services:
   ```powershell
   docker compose up -d --build