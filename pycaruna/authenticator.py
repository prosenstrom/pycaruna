import logging
import re
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import pycaruna.utils as utils
from pycaruna.exceptions import CarunaApiError, CarunaAuthError

_LOGGER = logging.getLogger(__name__)

LOGIN_START = "https://plus.caruna.fi/"
AUTH_ORIGIN = "https://authentication2.caruna.fi"
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _meta_refresh_url(html):
    soup = BeautifulSoup(html, "lxml")
    for meta in soup.find_all("meta"):
        if (meta.get("http-equiv") or "").lower() != "refresh":
            continue
        content = meta.get("content") or ""
        match = re.search(r"url\s*=\s*(.+)", content, flags=re.I)
        if match:
            return match.group(1).strip().strip("'\"")
    return None


def _ajax_redirect(response):
    if location := response.headers.get("Ajax-Location"):
        return location
    match = re.search(
        r"<redirect><!\[CDATA\[(.*?)\]\]></redirect>", response.text or ""
    )
    if match:
        return match.group(1)
    return None


def _form_feedback(html):
    soup = BeautifulSoup(html, "lxml")
    messages = []
    for span in soup.find_all("span", id=re.compile("FeedbackMessage", re.I)):
        text = span.get_text(" ", strip=True)
        if text:
            messages.append(text)
    return "; ".join(messages) if messages else None


def _login_action(html, form):
    match = re.search(
        r'Wicket\.Ajax\.ajax\(\{"u":"([^"]+loginWithUserID)"', html
    )
    if match:
        return match.group(1)
    return form.get("action") or "./login"


class Authenticator:
    def __init__(self, username, password):
        """
        :param username: your e-mail address
        :param password: your password
        """
        self.username = username
        self.password = password

    def login(self):
        """
        Performs the login dance required to obtain cookies etc. for further API communication.

        Follows the live plus.caruna.fi / authentication2.caruna.fi Wicket flow. The old
        hardcoded form action and Ajax-Location header are no longer sufficient on their own.
        """
        try:
            return self._login()
        except (requests.ConnectionError, requests.Timeout) as err:
            raise CarunaApiError("Could not reach Caruna+") from err
        except requests.HTTPError as err:
            response = err.response
            status = response.status_code if response is not None else None
            url = ""
            if err.request is not None:
                url = err.request.url
            elif response is not None:
                url = response.url
            raise CarunaApiError(
                f"Caruna+ request failed ({status}) at {url}",
                status_code=status,
            ) from err
        except requests.RequestException as err:
            if isinstance(err, ValueError):
                raise CarunaApiError(
                    "Caruna+ returned a non-JSON response"
                ) from err
            raise CarunaApiError("Could not reach Caruna+") from err
        except ValueError as err:
            raise CarunaApiError("Caruna+ returned a non-JSON response") from err

    def _login(self):
        session = requests.Session()
        session.headers.update(BROWSER_HEADERS)

        start = session.post(
            utils.create_caruna_plus_url("/authorization/login"),
            json={"language": "fi", "redirectAfterLogin": LOGIN_START},
            timeout=30,
        )
        start.raise_for_status()
        redirect_url = start.json().get("loginRedirectUrl")
        if not redirect_url:
            raise CarunaApiError("Caruna+ did not return a login URL")

        page = session.get(redirect_url, timeout=30)
        page.raise_for_status()
        if refresh := _meta_refresh_url(page.text):
            page = session.get(urljoin(page.url, refresh), timeout=30)
            page.raise_for_status()

        soup = BeautifulSoup(page.content, "lxml")
        form = soup.find("form")
        if form is None:
            raise CarunaApiError("Caruna+ login form was not found")

        fields = utils.get_hidden_form_vars(soup)
        fields["ttqusername"] = self.username
        fields["userPassword"] = self.password
        submit = soup.find("input", attrs={"type": "submit", "name": True})
        if submit is not None:
            fields[submit["name"]] = "1"

        action = _login_action(page.text, form)
        login_url = urljoin(page.url, action)
        _LOGGER.debug("Posting Caruna+ credentials to %s", login_url)
        posted = session.post(
            login_url,
            data=fields,
            headers={
                "Wicket-Ajax": "true",
                "Wicket-Ajax-BaseURL": "login",
                "Wicket-FocusedElementId": "loginWithUserID5",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": AUTH_ORIGIN,
                "Referer": page.url,
            },
            timeout=30,
        )
        posted.raise_for_status()

        nxt = _ajax_redirect(posted)
        if not nxt:
            feedback = _form_feedback(posted.text) or "Caruna+ rejected the login"
            raise CarunaAuthError(feedback)
        if "error" in nxt.lower() or nxt.rstrip("/").endswith("login"):
            raise CarunaAuthError("Caruna+ rejected the email or password")

        follow = session.get(urljoin(posted.url, nxt), timeout=30)
        follow.raise_for_status()
        if refresh := _meta_refresh_url(follow.text):
            follow = session.get(urljoin(follow.url, refresh), timeout=30)
            follow.raise_for_status()

        soup = BeautifulSoup(follow.content, "lxml")
        relay = soup.find("form")
        if relay is None or not relay.get("action"):
            raise CarunaApiError("Caruna+ OpenID form was missing after login")

        relayed = session.post(
            urljoin(follow.url, relay["action"]),
            data=utils.get_hidden_form_vars(soup),
            allow_redirects=False,
            timeout=30,
        )
        location = relayed.headers.get("Location")
        if not location:
            raise CarunaApiError("Caruna+ OpenID relay did not redirect")

        bounced = session.get(
            urljoin(relayed.url, location), allow_redirects=False, timeout=30
        )
        returned = bounced.headers.get("Location")
        if not returned:
            raise CarunaApiError("Caruna+ did not return an OpenID callback")

        query = parse_qs(urlparse(returned).query)
        try:
            token_payload = {
                "code": query["code"][0],
                "state": query["state"][0],
                "session_state": query["session_state"][0],
            }
        except (KeyError, IndexError) as err:
            raise CarunaAuthError("Caruna+ OpenID callback was incomplete") from err

        token = session.post(
            utils.create_caruna_plus_url("/authorization/token"),
            data=token_payload,
            timeout=30,
        )
        token.raise_for_status()
        result = token.json()
        if not isinstance(result, dict) or not result.get("token"):
            raise CarunaAuthError("Caruna+ login did not return a token")
        return result
