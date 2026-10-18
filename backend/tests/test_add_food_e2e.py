import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.seed import seed_database

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    seed_database()

def test_add_food_flow_e2e():
    with TestClient(app) as client:
        # 1. Check health
        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # 2. Get Zones
        zones_resp = client.get("/api/zones")
        assert zones_resp.status_code == 200
        zones = zones_resp.json()
        assert len(zones) >= 1
        target_zone_id = zones[0]["id"]

        # 3. Add a Food Item
        food_payload = {
            "name": "E2E Fresh Blueberries",
            "category": "Fruits",
            "item_type": "fruit",
            "zone_id": target_zone_id,
            "quantity": 1.0,
            "unit": "box",
            "expiry_date": (datetime.utcnow() + timedelta(days=6)).isoformat(),
            "freshness_status": "Fresh",
            "source": "manual",
            "estimated_cost": 3.99,
            "notes": "Purchased fresh today"
        }

        add_resp = client.post("/api/foods", json=food_payload)
        assert add_resp.status_code == 200
        food_data = add_resp.json()
        assert food_data["name"] == "E2E Fresh Blueberries"
        food_id = food_data["id"]

        # 4. Verify item appears in inventory
        list_resp = client.get("/api/foods?search=Blueberries")
        assert list_resp.status_code == 200
        assert any(item["id"] == food_id for item in list_resp.json())

        # 5. Verify Dashboard summary reflects active food
        dash_resp = client.get("/api/dashboard/summary")
        assert dash_resp.status_code == 200
        summary = dash_resp.json()
        assert summary["stats"]["total_items"] >= 1

        # 6. Mark Food as Used
        use_resp = client.post(f"/api/foods/{food_id}/use")
        assert use_resp.status_code == 200
        assert use_resp.json()["is_used"] is True

        # 7. Clean up
        del_resp = client.delete(f"/api/foods/{food_id}")
        assert del_resp.status_code == 200
