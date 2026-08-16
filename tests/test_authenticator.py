from unittest.mock import Mock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from pycaruna import Authenticator, CarunaApiError, CarunaAuthError
from pycaruna.authenticator import (
    _ajax_redirect,
    _form_feedback,
    _is_login_page,
    _login_action,
    _meta_refresh_url,
)

LOGIN_PAGE_URL = "https://authentication2.caruna.fi/portal/login"
LOGIN_FORM_HTML = """<!doctype html>
<html><body>
<form action="./login">
  <input type="hidden" name="csrf" value="tok">
  <input type="submit" name="loginWithUserID5" value="1">
</form>
<script>Wicket.Ajax.ajax({"u":"./loginWithUserID"});</script>
</body></html>
"""
RELAY_HTML = """<!doctype html>
<html><body>
<form action="https://plus.caruna.fi/openid">
  <input type="hidden" name="SAMLResponse" value="x">
</form>
</body></html>
"""
META_REFRESH_HTML = (
    '<html><head><meta http-equiv="refresh" content="0;url=./login"></head></html>'
)
FOLLOW_REFRESH_HTML = (
    '<html><head><meta http-equiv="refresh" content="0;url=./relay"></head></html>'
)
TOKEN_RESULT = {"token": "tok-1", "user": {"ownCustomerNumbers": ["111"]}}


def _html_response(url, html, headers=None):
    response = Mock()
    response.url = url
    response.text = html
    response.content = html.encode()
    response.headers = headers or {}
    response.status_code = 200
    response.raise_for_status = Mock()
    return response


def _json_response(url, payload, headers=None):
    response = Mock()
    response.url = url
    response.text = ""
    response.content = b""
    response.headers = headers or {}
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json.return_value = payload
    return response


def _redirect_response(url, location):
    return _html_response(url, "", headers={"Location": location})


def test_is_login_page_same_path_not_openid_hop():
    current = "https://authentication2.caruna.fi/portal/login"
    assert _is_login_page("./login", current)
    assert _is_login_page(current, current)
    assert not _is_login_page("./openid-connect-login", current)
    assert not _is_login_page("./login/callback", current)


def test_meta_refresh_url_parses_and_ignores_other_meta():
    html = """
    <html><head>
      <meta charset="utf-8">
      <meta http-equiv="Refresh" content="0; URL='./next'">
    </head></html>
    """
    assert _meta_refresh_url(html) == "./next"
    assert _meta_refresh_url("<html></html>") is None
    assert _meta_refresh_url('<meta http-equiv="refresh" content="5">') is None
    assert _meta_refresh_url('<meta http-equiv="refresh">') is None


def test_ajax_redirect_header_and_cdata():
    header = Mock(headers={"Ajax-Location": "./openid-connect-login"}, text="")
    assert _ajax_redirect(header) == "./openid-connect-login"

    cdata = Mock(
        headers={},
        text="<redirect><![CDATA[./openid-connect-login]]></redirect>",
    )
    assert _ajax_redirect(cdata) == "./openid-connect-login"

    empty = Mock(headers={}, text=None)
    assert _ajax_redirect(empty) is None


def test_form_feedback_joins_messages():
    html = """
    <span id="id1FeedbackMessage">bad email</span>
    <span id="id2FeedbackMessage"> </span>
    <span id="id3FeedbackMessage">try again</span>
    """
    assert _form_feedback(html) == "bad email; try again"
    assert _form_feedback("<html></html>") is None


def test_login_action_prefers_wicket_ajax():
    form = BeautifulSoup('<form action="./login"></form>', "lxml").find("form")
    html = 'Wicket.Ajax.ajax({"u":"./x-loginWithUserID"})'
    assert _login_action(html, form) == "./x-loginWithUserID"
    assert _login_action("<html></html>", form) == "./login"
    bare = BeautifulSoup("<form></form>", "lxml").find("form")
    assert _login_action("<html></html>", bare) == "./login"


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


def test_login_http_error_without_request_uses_response_url(monkeypatch):
    response = Mock()
    response.status_code = 503
    response.url = "https://plus.caruna.fi/api/authorization/login"
    err = requests.HTTPError(response=response)
    err.request = None
    monkeypatch.setattr(Authenticator, "_login", Mock(side_effect=err))
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert exc.value.status_code == 503
    assert response.url in str(exc.value)


def test_login_timeout_is_reachability_failure(monkeypatch):
    monkeypatch.setattr(Authenticator, "_login", Mock(side_effect=requests.Timeout()))
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Could not reach Caruna+"


def test_login_connection_error_is_reachability_failure(monkeypatch):
    monkeypatch.setattr(
        Authenticator, "_login", Mock(side_effect=requests.ConnectionError())
    )
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Could not reach Caruna+"


def test_login_request_exception_is_reachability_failure(monkeypatch):
    monkeypatch.setattr(
        Authenticator, "_login", Mock(side_effect=requests.RequestException("x"))
    )
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Could not reach Caruna+"


def test_login_json_decode_error_is_non_json(monkeypatch):
    err = requests.exceptions.JSONDecodeError("Expecting value", "doc", 0)
    monkeypatch.setattr(Authenticator, "_login", Mock(side_effect=err))
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Caruna+ returned a non-JSON response"


def test_login_value_error_is_non_json(monkeypatch):
    monkeypatch.setattr(Authenticator, "_login", Mock(side_effect=ValueError("bad")))
    with pytest.raises(CarunaApiError) as exc:
        Authenticator("user", "pass").login()
    assert str(exc.value) == "Caruna+ returned a non-JSON response"


def _script_login_session(
    session,
    *,
    start=None,
    first_page=None,
    login_page=None,
    posted=None,
    follow=None,
    relay_page=None,
    relayed=None,
    bounced=None,
    token=None,
):
    start = start or _json_response(
        "https://plus.caruna.fi/api/authorization/login",
        {"loginRedirectUrl": LOGIN_PAGE_URL},
    )
    first_page = first_page or _html_response(LOGIN_PAGE_URL, META_REFRESH_HTML)
    login_page = login_page or _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML)
    posted = posted or _html_response(
        "https://authentication2.caruna.fi/portal/loginWithUserID",
        "",
        headers={"Ajax-Location": "./openid-connect-login"},
    )
    follow = follow or _html_response(
        "https://authentication2.caruna.fi/portal/openid-connect-login",
        FOLLOW_REFRESH_HTML,
    )
    relay_page = relay_page or _html_response(
        "https://authentication2.caruna.fi/portal/relay",
        RELAY_HTML,
    )
    relayed = relayed or _redirect_response(
        "https://plus.caruna.fi/openid",
        "https://authentication2.caruna.fi/auth?session=1",
    )
    bounced = bounced or _redirect_response(
        "https://authentication2.caruna.fi/auth?session=1",
        "https://plus.caruna.fi/?code=abc&state=st&session_state=ss",
    )
    token = token or _json_response(
        "https://plus.caruna.fi/api/authorization/token",
        TOKEN_RESULT,
    )
    session.post.side_effect = [start, posted, relayed, token]
    session.get.side_effect = [first_page, login_page, follow, relay_page, bounced]


@patch("pycaruna.authenticator.requests.Session")
def test_login_happy_path(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    _script_login_session(session)

    result = Authenticator("user", "pass").login()
    assert result == TOKEN_RESULT
    token_call = session.post.call_args_list[-1]
    assert token_call.kwargs["data"] == {
        "code": "abc",
        "state": "st",
        "session_state": "ss",
    }
    credential_call = session.post.call_args_list[1]
    assert credential_call.kwargs["data"]["ttqusername"] == "user"
    assert credential_call.kwargs["data"]["userPassword"] == "pass"
    assert credential_call.kwargs["data"]["loginWithUserID5"] == "1"


@patch("pycaruna.authenticator.requests.Session")
def test_login_missing_redirect_url(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.return_value = _json_response(
        "https://plus.caruna.fi/api/authorization/login",
        {},
    )
    with pytest.raises(CarunaApiError, match="did not return a login URL"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_missing_form(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.return_value = _json_response(
        "https://plus.caruna.fi/api/authorization/login",
        {"loginRedirectUrl": LOGIN_PAGE_URL},
    )
    session.get.return_value = _html_response(
        LOGIN_PAGE_URL, "<html><body>nope</body></html>"
    )
    with pytest.raises(CarunaApiError, match="login form was not found"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_rejected_without_ajax_redirect(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    posted = _html_response(
        LOGIN_PAGE_URL,
        '<span id="fFeedbackMessage">väärä salasana</span>',
    )
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        posted,
    ]
    session.get.side_effect = [_html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML)]
    with pytest.raises(CarunaAuthError, match="väärä salasana"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_rejected_when_ajax_stays_on_login_page(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    posted = _html_response(
        LOGIN_PAGE_URL,
        "",
        headers={"Ajax-Location": "./login"},
    )
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        posted,
    ]
    session.get.side_effect = [_html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML)]
    with pytest.raises(CarunaAuthError, match="rejected the email or password"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_missing_openid_form(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        _html_response(
            "https://authentication2.caruna.fi/portal/loginWithUserID",
            "",
            headers={"Ajax-Location": "./openid-connect-login"},
        ),
    ]
    session.get.side_effect = [
        _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML),
        _html_response(
            "https://authentication2.caruna.fi/portal/openid-connect-login",
            "<html><body>no form</body></html>",
        ),
    ]
    with pytest.raises(CarunaApiError, match="OpenID form was missing"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_openid_relay_without_redirect(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        _html_response(
            "https://authentication2.caruna.fi/portal/loginWithUserID",
            "",
            headers={"Ajax-Location": "./openid-connect-login"},
        ),
        _html_response("https://plus.caruna.fi/openid", ""),
    ]
    session.get.side_effect = [
        _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML),
        _html_response(
            "https://authentication2.caruna.fi/portal/openid-connect-login",
            RELAY_HTML,
        ),
    ]
    with pytest.raises(CarunaApiError, match="OpenID relay did not redirect"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_missing_openid_callback(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        _html_response(
            "https://authentication2.caruna.fi/portal/loginWithUserID",
            "",
            headers={"Ajax-Location": "./openid-connect-login"},
        ),
        _redirect_response(
            "https://plus.caruna.fi/openid",
            "https://authentication2.caruna.fi/auth?session=1",
        ),
    ]
    session.get.side_effect = [
        _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML),
        _html_response(
            "https://authentication2.caruna.fi/portal/openid-connect-login",
            RELAY_HTML,
        ),
        _html_response("https://authentication2.caruna.fi/auth?session=1", ""),
    ]
    with pytest.raises(CarunaApiError, match="did not return an OpenID callback"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_incomplete_openid_callback(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        _html_response(
            "https://authentication2.caruna.fi/portal/loginWithUserID",
            "",
            headers={"Ajax-Location": "./openid-connect-login"},
        ),
        _redirect_response(
            "https://plus.caruna.fi/openid",
            "https://authentication2.caruna.fi/auth?session=1",
        ),
    ]
    session.get.side_effect = [
        _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML),
        _html_response(
            "https://authentication2.caruna.fi/portal/openid-connect-login",
            RELAY_HTML,
        ),
        _redirect_response(
            "https://authentication2.caruna.fi/auth?session=1",
            "https://plus.caruna.fi/?code=abc",
        ),
    ]
    with pytest.raises(CarunaAuthError, match="OpenID callback was incomplete"):
        Authenticator("user", "pass").login()


@patch("pycaruna.authenticator.requests.Session")
def test_login_missing_token(mock_session_cls):
    session = Mock()
    mock_session_cls.return_value = session
    session.post.side_effect = [
        _json_response(
            "https://plus.caruna.fi/api/authorization/login",
            {"loginRedirectUrl": LOGIN_PAGE_URL},
        ),
        _html_response(
            "https://authentication2.caruna.fi/portal/loginWithUserID",
            "",
            headers={"Ajax-Location": "./openid-connect-login"},
        ),
        _redirect_response(
            "https://plus.caruna.fi/openid",
            "https://authentication2.caruna.fi/auth?session=1",
        ),
        _json_response(
            "https://plus.caruna.fi/api/authorization/token",
            {"user": {}},
        ),
    ]
    session.get.side_effect = [
        _html_response(LOGIN_PAGE_URL, LOGIN_FORM_HTML),
        _html_response(
            "https://authentication2.caruna.fi/portal/openid-connect-login",
            RELAY_HTML,
        ),
        _redirect_response(
            "https://authentication2.caruna.fi/auth?session=1",
            "https://plus.caruna.fi/?code=abc&state=st&session_state=ss",
        ),
    ]
    with pytest.raises(CarunaAuthError, match="did not return a token"):
        Authenticator("user", "pass").login()
