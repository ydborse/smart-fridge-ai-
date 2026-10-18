# Smart Fridge – Smart Food. Healthy You. 🍏❄️

An end-to-end intelligent refrigerator assistant that tracks food in your fridge, detects freshness of fruits and vegetables using computer vision, retrieves packaged food details from barcodes, checks ethylene gas shelf compatibility, and sends instant alerts to your phone before food spoils.

---

## 🌟 Key Features

1. **Dashboard & Telemetry**:
   - High-level KPIs: Total Items, Fresh Items, Expiring Soon (≤3 days), Expired items.
   - **Today's Smart Insights**: Automated daily briefing on urgent actions and gas warnings.
   - **24-Hour Telemetry Line Chart**: Real-time hourly temperature curves across shelves using Recharts.
   - **Humidity Donut Gauge**: Live relative humidity tracking.
2. **Fridge Digital Twin**:
   - Visual interactive refrigerator with 5 clickable shelves: Top Shelf, Middle Shelf, Bottom Shelf, Vegetable Drawer, and Freezer.
   - Shelf health index (0–100), live temperature/humidity readouts, and stored item inventory.
   - **Ethylene Gas Compatibility Warning**: Detects ethylene producers (apple, banana, tomato, avocado) stored next to gas-sensitive produce (lettuce, coriander, capsicum, strawberry) and warns the user.
3. **Food Management**:
   - Filterable, searchable, and sortable pantry table with status badges (Fresh, Expiring Soon, Expired).
   - One-click actions to mark items as consumed, edit quantities, or delete records.
4. **AI Freshness Recognition (MobileNetV2)**:
   - Photograph produce using phone camera or file upload.
   - Model classifies produce item and freshness stage (**Fresh, Ripe, Overripe, Rotten**) with confidence score.
   - Calculates dynamic adjusted expiry date and suggests the optimal storage shelf.
5. **Barcode Scanner & Open Food Facts Integration**:
   - Looks up products via Open Food Facts API (`https://world.openfoodfacts.org/api/v2/product/{barcode}.json`) with local database caching.
   - Autofills product name, brand, Nutri-Score, category, and quantity.
   - **OCR Expiry Date Extraction**: Optional camera scan of the packaging expiration stamp (`EXP / BEST BEFORE`).
6. **Weekly Fridge Audit (Sunday Routine)**:
   - Users upload 2–5 photos of their fridge shelves from different angles.
   - System cross-references detected items against active inventory, highlighting matched, missing, and unknown items.
   - Automated missing item verification with instant phone alerts.
7. **Pluggable Multi-Channel Notification Service**:
   - Common interface `send(user, title, message, channel)` across Email, Web Push, and SMS.
   - **Email (PRIMARY)**: SMTP via aiosmtplib/smtplib with Gmail App Password default + Resend/Brevo API fallback. Clean HTML emails with food thumbnail, expiry date, status badge, and "Mark as used" link. Daily morning digest (8:00 AM) and instant alerts for spoiled/expired foods.
   - **Web Push (PHONE)**: Full PWA support (`manifest.json` + `sw.js`) via Web Push (VAPID) protocol.
   - **SMS (OPTIONAL)**: Twilio and Fast2SMS provider abstraction (<160 chars) with configurable DLT template ID.
   - Quiet hours filtering, up to 3x retry loop with backoff, and audit logging in `notifications_log`.
8. **Consumption & Waste History**:
   - Financial savings analytics, efficiency rates, and monthly waste vs. consumed comparative bar charts.
9. **Active Learning Retraining Loop**:
   - Moderation console to review user-corrected predictions, approve images into the training split, and retrain models safely against a fixed test set.

---

## 🏗️ Architecture & Tech Stack

```
   ┌────────────────────────────────────────────────────────┐
   │          React 18 + Vite + TypeScript (PWA)            │
   │  Tailwind CSS 3 • Lucide Icons • Recharts • Web Push   │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP / REST (/api)
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │               FastAPI (Python 3.11)                    │
   │  Pydantic v2 • SQLAlchemy 2.0 • APScheduler • JWT Auth │
   ├───────────────────────────┬────────────────────────────┤
   │  ML Engine: PyTorch / ONNX│ Barcode: Open Food Facts   │
   │  MobileNetV2 Classifier   │ Alerts: Email / Push / SMS │
   └─────────────┬─────────────┴─────────────┬──────────────┘
                 │                           │
                 ▼                           ▼
      ┌──────────────────────┐   ┌──────────────────────┐
      │ PostgreSQL / SQLite  │   │   Local File Storage │
      │ Relational Database  │   │  /storage/uploads/   │
      └──────────────────────┘   └──────────────────────┘
```

- **Frontend**: React 18, TypeScript, Tailwind CSS, Recharts, React Router, Axios, Lucide Icons, Service Worker PWA.
- **Backend**: FastAPI, SQLAlchemy 2.0, APScheduler, Pydantic 2, Python-Jose (JWT), BCrypt, PyWebPush, aiosmtplib.
- **Database**: PostgreSQL (Docker / Production) with automatic SQLite fallback for zero-config local runs.
- **Computer Vision**: PyTorch MobileNetV2 (36 compound classes), OpenCV/PIL image processing, ONNX export.
- **Notifications**: SMTP (Gmail App Password), Resend API, Brevo API, Web Push (VAPID), Twilio SMS, Fast2SMS.

---

## 🚀 Quickstart: Running with Docker Compose

Run the entire stack (PostgreSQL + FastAPI + React Frontend) with a single command:

```bash
docker compose up --build
```

- **Web Application**: http://localhost:5173
- **FastAPI Interactive Docs**: http://localhost:8000/docs
- **PostgreSQL Database**: localhost:5432

---

## 💻 Manual Setup & Local Execution

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ and npm

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies (CPU PyTorch)
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Seed database with demo user, 5 zones, 24 food items, and 24h sensor history
python -m app.seed

# Start backend server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend will be running at `http://127.0.0.1:8000` with Swagger docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup

In a separate terminal:

```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 🧪 Running the Test Suite

We include tests covering alert rules, safety overrides, shelf life calculations, barcode parsing, and end-to-end food management:

```bash
# From repository root:
# Windows PowerShell:
$env:PYTHONPATH = "backend"
backend\.venv\Scripts\python.exe -m pytest backend\tests

# Linux/macOS:
PYTHONPATH=backend pytest backend/tests
```

All 8 tests will execute and pass:
- `test_packaged_food_expiry_rule`: Validates expired item alert triggers.
- `test_fruit_rotten_rule`: Validates spoiled produce alert generation.
- `test_safety_override_rule`: Validates safety override when days-in-fridge exceeds typical shelf life.
- `test_guess_shelf_life_and_zone`: Validates barcode category mapping to shelf and days.
- `test_lookup_barcode_cached`: Validates Open Food Facts caching in database.
- `test_shelf_life_freshness_adjustment`: Validates shelf-life decay curve across freshness classes.
- `test_ethylene_gas_compatibility_sets`: Validates ethylene producer and sensitive sets.
- `test_add_food_flow_e2e`: Comprehensive end-to-end integration test of API lifecycle.

---

## 🤖 ML Pipeline & Active Learning

### 1. Download & Prepare Dataset
```bash
# 1. Download Kaggle datasets or generate offline test samples
python ml/download_datasets.py

# 2. Deduplicate, map labels, and create fixed 70/15/15 train/val/test splits
python ml/prepare_dataset.py
```

### 2. Train MobileNetV2
```bash
python ml/train.py
```
Outputs:
- `ml/models/best_model.pth`: PyTorch checkpoint with early stopping.
- `ml/models/model.onnx`: Exported ONNX runtime model.

### 3. Evaluate Model
```bash
python ml/evaluate.py
```
Generates comprehensive report in `ml/reports/evaluation_report.md` focusing on **Rotten class recall** to guarantee food safety.

### 4. Retrain with Active Learning
```bash
python ml/retrain.py
```
Merges approved user uploads into the training set and only promotes candidates that improve test accuracy and rotten recall.

---

## 🔔 Pluggable Notifications Architecture (Email, Web Push, SMS)

The system includes a unified notification abstraction `send(user, title, message, channel, metadata, db)`:

### 1. Email Alerts (PRIMARY)
- **Engine**: SMTP via `aiosmtplib` / `smtplib` using a Gmail App Password (default) or HTTP API via **Resend** or **Brevo**.
- **Templates**: Clean, responsive HTML emails with food thumbnails, expiry date, status badges, and direct **"Mark as used"** action buttons.
- **Cadence**: Daily 8:00 AM digest email of all items expiring within lead time + instant alert for spoiled / expired items.
- **Configuration** in `.env`:
  ```env
  EMAIL_PROVIDER="smtp"
  SMTP_HOST="smtp.gmail.com"
  SMTP_PORT=587
  SMTP_USER="your_email@gmail.com"
  SMTP_PASSWORD="your_16_char_app_password"
  EMAIL_FROM="your_email@gmail.com"
  ```

### 2. Phone Alerts (PWA Web Push)
- **Engine**: Progressive Web App (`manifest.json` + `sw.js`) utilizing standard **VAPID Web Push protocol** via `pywebpush`.
- **Activation**: Open **Settings** -> click **"Enable Notifications"** to register your phone or browser service worker with the server's VAPID public key.
- **Features**: Push notifications appear directly on mobile lock screens and phone notification centers without app store installation.

### 3. SMS Alerts (OPTIONAL)
- **Engine**: Provider abstraction supporting **Twilio** and **Fast2SMS** (India DLT route with configurable template ID).
- **Compliance**: Concise messages strictly under 160 characters. Disabled by default.

### 4. Dispatch Logging & Resiliency
- Every delivery attempt is logged in the `notifications_log` database table with timestamp, recipient, channel, and provider.
- Automatic retry loop attempts delivery up to **3 times with exponential backoff**.
- 24-hour deduplication prevents repeated alerts for the same item and state.

---

## 📝 Demo Credentials & Default State

The database comes pre-seeded with:
- **Demo User**: `demo@smartfridge.com` / `SmartFridge123!`
- **5 Monitored Shelves**: Top Shelf, Middle Shelf, Bottom Shelf, Vegetable Drawer, Freezer.
- **24 Food Items**: Mixed across Fresh, Ripe, Overripe, Expiring Soon, and Expired states.
- **24 Hours of Telemetry**: Realistic temperature & humidity history.
- **Notification Logs**: Sample delivery history visible on the Settings page.

---

## 🛡️ Disclaimer
*Freshness predictions are assistive and not a food safety guarantee. Always inspect food condition and smell before consumption.*
