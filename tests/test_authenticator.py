from unittest.mock import Mock

import pytest
import requests

from pycaruna import Authenticator, CarunaApiError
from pycaruna.authenticator import _is_login_page


def test_is_login_page_same_path_not_openid_hop():
    current = "https://authentication2.caruna.fi/portal/login"
    assert _is_login_page("./login", current)
    assert _is_login_page(current, current)
    assert not _is_login_page("./openid-connect-login", current)
    assert not _is_login_page("./login/callback", current)


def test_login_http_error_is_not_a_reachability_failure(monkeypatch):
    response = Mock()
    response.status_code = 502
    response.url = "https://plus.caruna.fi/api/authorization/login"
    request = Mock()
    request.url = response.url
    err = requests.HTTPError(response=response)
    err.request = request

    monkeypatch.setattr(Authenticator, "_login", Mock(side_effect=err))
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert exc.value.status_code == 502
    assert "502" in str(exc.value)
    assert "Could not reach Caruna+" not in str(exc.value)


def test_login_timeout_is_reachability_failure(monkeypatch):
    monkeypatch.setattr(
        Authenticator, "_login", Mock(side_effect=requests.Timeout())
    )
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Could not reach Caruna+"
