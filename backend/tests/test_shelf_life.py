import pytest
from app.services.ml_inference import ml_service
from app.services.alert_engine import ETHYLENE_PRODUCERS, ETHYLENE_SENSITIVE

def test_shelf_life_freshness_adjustment():
    # Apple fresh base is 21 days
    fresh_days = ml_service.calculate_adjusted_shelf_life("apple", "Fresh")
    assert fresh_days == 21

    # Ripe is ~55% of base
    ripe_days = ml_service.calculate_adjusted_shelf_life("apple", "Ripe")
    assert 10 <= ripe_days <= 13

    # Overripe is ~25% of base
    overripe_days = ml_service.calculate_adjusted_shelf_life("apple", "Overripe")
    assert 4 <= overripe_days <= 6

    # Rotten is 0 days
    rotten_days = ml_service.calculate_adjusted_shelf_life("apple", "Rotten")
    assert rotten_days == 0

def test_ethylene_gas_compatibility_sets():
    assert "apple" in ETHYLENE_PRODUCERS
    assert "banana" in ETHYLENE_PRODUCERS
    assert "tomato" in ETHYLENE_PRODUCERS

    assert "lettuce" in ETHYLENE_SENSITIVE
    assert "coriander" in ETHYLENE_SENSITIVE
    assert "strawberry" in ETHYLENE_SENSITIVE
