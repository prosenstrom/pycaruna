import json
from pathlib import Path

from bs4 import BeautifulSoup

from pycaruna.utils import (
    asset_items,
    create_caruna_plus_headers,
    create_caruna_plus_url,
    customer_ids_from_user,
    energy_kwh,
    flatten_ids,
    get_hidden_form_vars,
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


def test_create_caruna_plus_url_and_headers():
    assert create_caruna_plus_url("/customers/1/info") == (
        "https://plus.caruna.fi/api/customers/1/info"
    )
    assert create_caruna_plus_headers("tok") == {
        "Authorization": "Bearer tok",
        "User-Agent": "pycaruna",
    }


def test_get_hidden_form_vars_skips_visible_and_nameless():
    soup = BeautifulSoup(
        """
        <form>
          <input type="hidden" name="csrf" value="abc">
          <input type="hidden" name="empty">
          <input type="text" name="user" value="x">
          <input type="hidden" value="noname">
        </form>
        """,
        "lxml",
    )
    assert get_hidden_form_vars(soup) == {"csrf": "abc", "empty": ""}


def test_flatten_ids_drops_empty_and_none_tokens():
    assert flatten_ids(None) == []
    assert flatten_ids(["None", "[]", "", "  ", 123]) == ["123"]


def test_asset_items_unwraps_named_lists_and_single_objects():
    assert asset_items({"results": [{"assetId": "a"}]}) == [{"assetId": "a"}]
    assert asset_items({"data": [{"id": 1}]}) == [{"id": 1}]
    assert asset_items({"assets": [{"id": 1}, "skip"]}) == [{"id": 1}]
    assert asset_items({"meteringPoints": [{"id": 1}]}) == [{"id": 1}]
    assert asset_items({"meteringpoints": [{"id": 1}]}) == [{"id": 1}]
    assert asset_items({"items": [{"id": 1}]}) == [{"id": 1}]
    assert asset_items({"assetId": "solo", "gsrn": "1"}) == [
        {"assetId": "solo", "gsrn": "1"}
    ]
    assert asset_items({"gsrn": "1"}) == [{"gsrn": "1"}]
    assert asset_items({"meteringPointNumber": "1"}) == [{"meteringPointNumber": "1"}]
    assert asset_items({"foo": "bar"}) == []
    assert asset_items("nope") == []
    assert asset_items([{"id": 1}, "skip"]) == [{"id": 1}]


def test_is_meter_accepts_gsrn_tabs_and_address():
    assert is_meter({"assetId": "1", "gsrn": "x"})
    assert is_meter({"assetId": "1", "meteringPointNumber": "x"})
    assert is_meter({"assetId": "1", "tabs": ["consumption"]})
    assert is_meter({"assetId": "1", "address": {"streetName": "X"}})
    assert not is_meter({"assetId": "1"})


def test_normalize_energy_dict_wrappers_and_single_row():
    assert normalize_energy({"hours": [{"consumption": 1}]}) == {
        "results": [{"data": [{"consumption": 1}]}]
    }
    assert normalize_energy({"days": [1]}) == {"results": [{"data": [1]}]}
    assert normalize_energy({"timestamp": "t", "totalConsumption": 2.5}) == {
        "results": [{"data": [{"timestamp": "t", "totalConsumption": 2.5}]}]
    }
    assert normalize_energy({"timestamp": "t", "consumption": 1}) == {
        "results": [{"data": [{"timestamp": "t", "consumption": 1}]}]
    }
    assert normalize_energy({"results": [{"data": []}]}) == {"results": [{"data": []}]}
