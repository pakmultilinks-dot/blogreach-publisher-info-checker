# -*- coding: utf-8 -*-
"""
BlogReach: Publisher Website Info Checker - core logic.

Fetches a homepage and extracts basic publisher-relevant information:
page title, meta description, HTTPS usage, load time, and link count.

All network behavior is isolated here so it can be unit-tested with mocks.
"""
import os
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = float(os.environ.get("CHECKER_TIMEOUT", "10"))
MAX_BYTES = int(os.environ.get("CHECKER_MAX_BYTES", str(2 * 1024 * 1024)))
USER_AGENT = "BlogReach-InfoChecker/1.0 (+https://blogreach.com)"


class InvalidURLError(ValueError):
    """The supplied string is not a usable http(s) URL."""


class UnreachableError(RuntimeError):
    """The URL looks fine but the site could not be fetched."""


def normalize_url(raw):
    """Clean user input into a fetchable http(s) URL.

    Adds https:// when no scheme is given. Raises InvalidURLError when the
    input cannot be a website address.
    """
    if raw is None:
        raise InvalidURLError("Please enter a website URL.")
    text = raw.strip()
    if not text:
        raise InvalidURLError("Please enter a website URL.")
    if len(text) > 2048:
        raise InvalidURLError("That URL is too long to be valid.")
    if " " in text:
        raise InvalidURLError("URLs cannot contain spaces. Example: https://example.com")
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLError("Only http and https URLs are supported.")
    host = parsed.hostname or ""
    if "." not in host and host != "localhost":
        raise InvalidURLError("That does not look like a valid website address.")
    if re.search(r"[^\w\-.:\/@?#&=%+~*,;()\[\]!$']", text):
        raise InvalidURLError("That URL contains invalid characters.")
    return text


def check_website(raw_url):
    """Fetch a homepage and return its basic info as a dict.

    Returns keys: url, final_url, uses_https, load_time_s, title,
    meta_description, link_count, page_bytes.

    Raises InvalidURLError for bad input and UnreachableError when the site
    cannot be fetched or does not return usable HTML.
    """
    url = normalize_url(raw_url)
    started = time.monotonic()
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
            stream=True,
        )
    except requests.exceptions.Timeout:
        raise UnreachableError(
            "The site took too long to respond (over %d seconds)." % int(REQUEST_TIMEOUT)
        )
    except requests.exceptions.ConnectionError:
        raise UnreachableError(
            "Could not connect to that website. Check the address and try again."
        )
    except requests.exceptions.RequestException as exc:
        raise UnreachableError("Could not fetch that website: %s" % exc)

    try:
        chunks = []
        downloaded = 0
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            downloaded += len(chunk)
            if downloaded > MAX_BYTES:
                break
            chunks.append(chunk)
        body = b"".join(chunks)
    finally:
        response.close()
    load_time = time.monotonic() - started

    if response.status_code >= 400:
        raise UnreachableError(
            "The website returned an error (HTTP %d)." % response.status_code
        )

    content_type = response.headers.get("Content-Type", "")
    final_url = response.url
    uses_https = urlparse(final_url).scheme == "https"

    title = ""
    meta_description = ""
    link_count = 0
    if "html" in content_type.lower() or not content_type:
        soup = BeautifulSoup(body, "html.parser")
        title_tag = soup.title
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        meta = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        if meta and meta.get("content"):
            meta_description = meta["content"].strip()
        link_count = len(soup.find_all("a", href=True))

    return {
        "url": url,
        "final_url": final_url,
        "uses_https": uses_https,
        "load_time_s": round(load_time, 2),
        "title": title,
        "meta_description": meta_description,
        "link_count": link_count,
        "page_bytes": downloaded,
        "http_status": response.status_code,
    }
