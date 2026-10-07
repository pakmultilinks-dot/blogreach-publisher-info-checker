# -*- coding: utf-8 -*-
"""Automated tests for the Publisher Website Info Checker.

Network calls are mocked, so the suite runs offline and stays deterministic.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

import checker
from checker import InvalidURLError, UnreachableError, check_website, normalize_url

SAMPLE_HTML = b"""
<!doctype html><html><head>
<title>Example Publisher</title>
<meta name="description" content="A fine example website.">
</head><body>
<a href="/about">About</a><a href="https://other.com">Other</a><a>No href</a>
</body></html>
"""


def make_response(html=SAMPLE_HTML, url="https://example.com/", status=200,
                  content_type="text/html; charset=utf-8"):
    resp = MagicMock()
    resp.status_code = status
    resp.url = url
    resp.headers = {"Content-Type": content_type}
    resp.iter_content.return_value = [html]
    return resp


# --- URL normalization -----------------------------------------------------

def test_normalize_adds_https_when_missing():
    assert normalize_url("example.com") == "https://example.com"


def test_normalize_keeps_explicit_http():
    assert normalize_url("http://example.com") == "http://example.com"


def test_normalize_strips_whitespace():
    assert normalize_url("  https://example.com  ") == "https://example.com"


def test_normalize_rejects_empty():
    with pytest.raises(InvalidURLError):
        normalize_url("   ")


def test_normalize_rejects_bad_scheme():
    with pytest.raises(InvalidURLError):
        normalize_url("ftp://example.com")


def test_normalize_rejects_spaces_inside():
    with pytest.raises(InvalidURLError):
        normalize_url("https://exa mple.com")


def test_normalize_rejects_bare_word():
    with pytest.raises(InvalidURLError):
        normalize_url("not a url at all")


# --- check_website ----------------------------------------------------------

@patch("checker.requests.get")
def test_check_returns_title_meta_and_link_count(mock_get):
    mock_get.return_value = make_response()
    result = check_website("example.com")
    assert result["title"] == "Example Publisher"
    assert result["meta_description"] == "A fine example website."
    assert result["link_count"] == 2  # only <a> tags with href count


@patch("checker.requests.get")
def test_check_reports_https_after_redirect(mock_get):
    mock_get.return_value = make_response(url="https://www.example.com/")
    result = check_website("http://example.com")
    assert result["uses_https"] is True
    assert result["final_url"] == "https://www.example.com/"


@patch("checker.requests.get")
def test_check_reports_no_https_for_plain_http(mock_get):
    mock_get.return_value = make_response(url="http://example.com/")
    result = check_website("http://example.com")
    assert result["uses_https"] is False


@patch("checker.requests.get")
def test_check_measures_load_time(mock_get):
    mock_get.return_value = make_response()
    result = check_website("example.com")
    assert result["load_time_s"] >= 0


@patch("checker.requests.get")
def test_check_raises_on_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("dns fail")
    with pytest.raises(UnreachableError) as exc:
        check_website("https://no-such-site-xyz.com")
    assert "Could not connect" in str(exc.value)


@patch("checker.requests.get")
def test_check_raises_on_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("slow")
    with pytest.raises(UnreachableError) as exc:
        check_website("https://example.com")
    assert "too long" in str(exc.value)


@patch("checker.requests.get")
def test_check_raises_on_http_error_status(mock_get):
    mock_get.return_value = make_response(status=404)
    with pytest.raises(UnreachableError) as exc:
        check_website("https://example.com/missing")
    assert "404" in str(exc.value)


def test_check_raises_on_invalid_url_without_network():
    with patch("checker.requests.get") as mock_get:
        with pytest.raises(InvalidURLError):
            check_website("ht!tp://bad url")
        mock_get.assert_not_called()


# --- Flask routes ------------------------------------------------------------

@pytest.fixture()
def client():
    import app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Website URL" in response.data


def test_post_invalid_url_shows_error(client):
    response = client.post("/check", data={"url": "not a url"})
    assert response.status_code == 200
    assert b"alert error" in response.data


@patch("app.check_website")
def test_post_valid_url_shows_results(mock_check, client):
    mock_check.return_value = {
        "url": "https://example.com", "final_url": "https://example.com/",
        "uses_https": True, "load_time_s": 0.42, "title": "Example Publisher",
        "meta_description": "A fine example website.", "link_count": 2,
        "page_bytes": 1234, "http_status": 200,
    }
    response = client.post("/check", data={"url": "example.com"})
    assert response.status_code == 200
    assert b"Example Publisher" in response.data
    assert b"0.42" in response.data


@patch("app.check_website")
def test_post_unreachable_shows_friendly_error(mock_check, client):
    mock_check.side_effect = UnreachableError("Could not connect to that website.")
    response = client.post("/check", data={"url": "https://down.example"})
    assert response.status_code == 200
    assert b"Could not connect" in response.data
