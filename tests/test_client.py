from unittest.mock import Mock, patch

import pytest

from pycaruna import CarunaApiError, CarunaAuthError, CarunaPlus, TimeSpan


def _response(status_code, payload, ok=None):
    response = Mock()
    response.status_code = status_code
    response.ok = (200 <= status_code < 400) if ok is None else ok
    response.json.return_value = payload
    return response


@patch("pycaruna.client.requests.get")
def test_get_energy_raises_on_500_json(mock_get):
    mock_get.return_value = _response(500, {"error": "upstream"})
    with pytest.raises(CarunaApiError) as exc:
        CarunaPlus("tok").get_energy("c", "a", TimeSpan.DAILY, 2026, 8, 16)
    assert exc.value.status_code == 500
    assert "upstream" in str(exc.value)


@patch("pycaruna.client.requests.get")
def test_get_json_raises_auth_error_on_401(mock_get):
    mock_get.return_value = _response(401, {"error": "expired"})
    with pytest.raises(CarunaAuthError) as exc:
        CarunaPlus("tok").get_user_profile("c")
    assert exc.value.status_code == 401


@patch("pycaruna.client.requests.get")
def test_get_metering_points_reraises_401(mock_get):
    mock_get.return_value = _response(401, {"error": "expired"})
    with pytest.raises(CarunaAuthError):
        CarunaPlus("tok").get_metering_points("c")
    assert mock_get.call_count == 1


@patch("pycaruna.client.requests.get")
def test_get_metering_points_raises_last_error_when_both_fail(mock_get):
    mock_get.side_effect = [
        _response(404, {"error": "missing"}),
        _response(500, {"error": "boom"}),
    ]
    with pytest.raises(CarunaApiError) as exc:
        CarunaPlus("tok").get_metering_points("c")
    assert exc.value.status_code == 500
    assert mock_get.call_count == 2


@patch("pycaruna.client.requests.get")
def test_get_metering_points_empty_200_is_no_meters(mock_get):
    mock_get.side_effect = [
        _response(404, {"error": "missing"}),
        _response(200, []),
    ]
    assert CarunaPlus("tok").get_metering_points("c") == []


@patch("pycaruna.client.requests.get")
def test_get_metering_points_reads_2026_payload(mock_get):
    mock_get.return_value = _response(
        200,
        [
            {
                "type": "consumptionMeteringPoint",
                "assetId": "mp-1",
                "gsrn": "64300",
            }
        ],
    )
    points = CarunaPlus("tok").get_metering_points("cust")
    assert points[0]["assetId"] == "mp-1"
    assert points[0]["customerId"] == "cust"


@patch("pycaruna.client.requests.get")
def test_get_json_raises_on_non_json(mock_get):
    response = _response(200, None)
    response.json.side_effect = ValueError("no json")
    mock_get.return_value = response
    with pytest.raises(CarunaApiError) as exc:
        CarunaPlus("tok").get_user_profile("c")
    assert exc.value.status_code == 200
    assert "Non-JSON" in str(exc.value)


@patch("pycaruna.client.requests.get")
def test_get_json_raises_auth_error_on_403(mock_get):
    mock_get.return_value = _response(403, {"error": "forbidden"})
    with pytest.raises(CarunaAuthError) as exc:
        CarunaPlus("tok").get_user_profile("c")
    assert exc.value.status_code == 403


@patch("pycaruna.client.requests.get")
def test_error_excerpt_falls_back_to_string_payload(mock_get):
    mock_get.return_value = _response(500, {"foo": 1})
    with pytest.raises(CarunaApiError) as exc:
        CarunaPlus("tok").get_user_profile("c")
    assert "{'foo': 1}" in str(exc.value)


@patch("pycaruna.client.requests.get")
def test_get_assets_and_contracts(mock_get):
    mock_get.return_value = _response(200, [{"id": "a"}])
    client = CarunaPlus("tok")
    assert client.get_assets("c") == [{"id": "a"}]
    assert client.get_contracts("c") == [{"id": "a"}]


@patch("pycaruna.client.requests.get")
def test_get_energy_normalizes_flat_list(mock_get):
    mock_get.return_value = _response(200, [{"totalConsumption": 1.33}])
    payload = CarunaPlus("tok").get_energy("c", "a", TimeSpan.MONTHLY, 2026, 1, 1)
    assert payload["results"][0]["data"][0]["totalConsumption"] == 1.33
    assert mock_get.call_args.kwargs["params"]["timespan"] == "monthly"


@patch("pycaruna.client.requests.get")
def test_get_metering_points_skips_non_meters_and_duplicates(mock_get):
    mock_get.return_value = _response(
        200,
        [
            {"type": "contract", "id": "c1"},
            {"type": "consumptionMeteringPoint", "assetId": "mp-1", "gsrn": "1"},
            {"type": "consumptionMeteringPoint", "assetId": "mp-1", "gsrn": "1"},
            {"type": "consumptionMeteringPoint"},
        ],
    )
    points = CarunaPlus("tok").get_metering_points("cust")
    assert [point["assetId"] for point in points] == ["mp-1"]


def test_get_metering_points_reraises_api_error_on_403():
    client = CarunaPlus("tok")
    client._get_json = Mock(side_effect=CarunaApiError("nope", status_code=403))
    with pytest.raises(CarunaApiError) as exc:
        client.get_metering_points("c")
    assert exc.value.status_code == 403
