import json
from pathlib import Path

from pycaruna.utils import (
    asset_items,
    customer_ids_from_user,
    energy_kwh,
    is_meter,
    normalize_energy,
)

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


def _load(name):
    return json.loads((RESOURCES / name).read_text())


def test_normalize_energy_old_wrapper():
    payload = _load("energy.json")
    normalized = normalize_energy(payload)
    assert "results" in normalized
    rows = normalized["results"][0]["data"]
    assert rows
    assert energy_kwh(rows[0]) == 1.33


def test_normalize_energy_flat_2026_list():
    payload = _load("energy_flat.json")
    normalized = normalize_energy(payload)
    rows = normalized["results"][0]["data"]
    assert len(rows) == 2
    assert energy_kwh(rows[0]) == 1.33
    assert energy_kwh(rows[1]) == 1.55


def test_normalize_energy_error_object_is_empty():
    assert normalize_energy({"error": "boom"}) == {"results": [{"data": []}]}


def test_energy_kwh_prefers_consumption_then_total():
    assert energy_kwh({"consumption": 2.0, "totalConsumption": 9.0}) == 2.0
    assert energy_kwh({"totalConsumption": 1.5}) == 1.5
    assert energy_kwh({"invoicedConsumption": 0.25}) == 0.25
    assert energy_kwh({}) is None


def test_customer_ids_from_user_merges_and_dedupes():
    user = {
        "ownCustomerNumbers": ["111", ["222"]],
        "representedCustomerNumbers": "222, 333",
    }
    assert customer_ids_from_user(user) == ["111", "222", "333"]
    assert customer_ids_from_user({"representedCustomerNumbers": ["444"]}) == ["444"]
    assert customer_ids_from_user({}) == []


def test_asset_items_and_is_meter_from_2026_fixture():
    items = asset_items(_load("meteringpoints.json"))
    assert len(items) == 1
    assert is_meter(items[0])
    assert items[0]["type"] == "consumptionMeteringPoint"


def test_asset_items_and_is_meter_from_old_assets():
    items = asset_items(_load("assets.json"))
    assert len(items) == 1
    assert is_meter(items[0])
    assert items[0]["type"] == "meteringPoint"


def test_is_meter_rejects_unrelated_assets():
    assert not is_meter({"type": "contract", "id": "1"})
