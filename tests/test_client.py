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
