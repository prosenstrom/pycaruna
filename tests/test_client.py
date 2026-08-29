from unittest.mock import Mock, patch

from pycaruna import CarunaPlus, TimeSpan


def _response(status_code, payload, ok=None):
    response = Mock()
    response.status_code = status_code
    response.ok = (200 <= status_code < 400) if ok is None else ok
    response.json.return_value = payload
    return response


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
def test_get_metering_points_falls_back_to_assets(mock_get):
    mock_get.side_effect = [
        _response(404, {"error": "missing"}),
        _response(200, []),
    ]
    assert CarunaPlus("tok").get_metering_points("c") == []
    assert mock_get.call_count == 2


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
def test_get_energy_keeps_old_wrapper(mock_get):
    mock_get.return_value = _response(
        200, {"results": [{"data": [{"consumption": 1.33}]}]}
    )
    payload = CarunaPlus("tok").get_energy("c", "a", TimeSpan.DAILY, 2023, 1, 1)
    assert payload["results"][0]["data"][0]["consumption"] == 1.33
