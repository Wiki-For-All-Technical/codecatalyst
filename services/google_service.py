"""
services/google_service.py

Business logic for fetching images from Google Photos (shared public album)
and Google Drive. All functions return structured dicts with:
  'images', 'next_page_token', 'error', 'error_type' keys.
"""

import base64
import json
import logging
import re

from flask import url_for
from google.auth.transport.requests import Request, AuthorizedSession
import requests as http_requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refresh_if_needed(creds):
    """Refreshes credentials if expired. Returns the (possibly updated) creds."""
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def _encode_url(raw_url: str) -> str:
    """Base64-encode a URL so it can be safely embedded in a Flask route."""
    return base64.urlsafe_b64encode(raw_url.encode()).decode()


def _check_real_scopes(creds, required_scope: str) -> bool:
    """
    Verifies that Google's token introspection endpoint confirms the required scope.
    Returns True if the scope is present, False otherwise.
    """
    try:
        token_info = http_requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}",
            timeout=10
        ).json()
        real_scopes = token_info.get("scope", "")
        logger.info("Real token scopes from Google: %s", real_scopes)
        return required_scope in real_scopes
    except Exception as exc:
        logger.warning("Could not verify token scopes: %s", exc)
        return True  # Optimistically proceed; the API call itself will fail if wrong


# ---------------------------------------------------------------------------
# Google Photos — Shared Public Album (no API key needed)
# ---------------------------------------------------------------------------

# Google Photos serves images from this CDN host
_PHOTOS_CDN = "lh3.googleusercontent.com"

# Short-link pattern   https://photos.app.goo.gl/XXXXX
# Long-link pattern    https://photos.google.com/share/...
_VALID_ALBUM_HOSTS = ("photos.app.goo.gl", "photos.google.com", "goo.gl")


def fetch_from_shared_album(album_url: str, page: int = 0) -> dict:
    """
    Fetch photo thumbnails from a publicly shared Google Photos album link.

    Strategy:
    1. Follow redirects on short URLs to get the canonical album URL.
    2. Fetch the album HTML page (no auth — it's public).
    3. Extract lh3.googleusercontent.com image URLs embedded in the page JSON.
    4. Return proxy URLs for the discovered images.

    Google Photos embeds photo data as JSON inside <script> tags as part of
    AF_initDataCallback calls. We extract all lh3 CDN URLs from that blob.

    Args:
        album_url: The shared album link pasted by the user.
        page:      Page index for client-side pagination (not used for server
                   pagination since we load everything in one page fetch).

    Returns:
        {
            'images': [proxy_url, ...],
            'next_page_token': None,       # Album fetched all at once
            'raw_urls': [str, ...],        # Stored in session for upload
            'error': str | None,
            'error_type': str | None,
        }
    """
    album_url = album_url.strip()

    # Basic validation
    if not any(h in album_url for h in _VALID_ALBUM_HOSTS):
        return {
            "images": [], "next_page_token": None, "raw_urls": [],
            "error": (
                "That doesn't look like a Google Photos shared album link. "
                "It should start with https://photos.app.goo.gl/ or https://photos.google.com/share/"
            ),
            "error_type": "invalid_url",
        }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        # Follow short-link redirects
        resp = http_requests.get(album_url, headers=headers, timeout=30, allow_redirects=True)

        if resp.status_code == 404:
            return {
                "images": [], "next_page_token": None, "raw_urls": [],
                "error": "Album not found (404). Check the link and make sure the album is public.",
                "error_type": "not_found",
            }

        if resp.status_code != 200:
            return {
                "images": [], "next_page_token": None, "raw_urls": [],
                "error": f"Could not load album (HTTP {resp.status_code}). Is the album set to 'Anyone with the link'?",
                "error_type": "http_error",
            }

        html = resp.text

        # ── Extract photo URLs from the page ──────────────────────────────
        # Google Photos embeds CDN URLs in two forms:
        #   "https://lh3.googleusercontent.com/PHOTO_ID"
        #   'https://lh3.googleusercontent.com/PHOTO_ID'
        # We collect all unique lh3 URLs that look like photos (long hash path).

        raw_pattern = re.compile(
            r'https://lh3\.googleusercontent\.com/([A-Za-z0-9_\-]{30,})'
        )
        found = list(dict.fromkeys(raw_pattern.findall(html)))  # unique, preserve order

        if not found:
            return {
                "images": [], "next_page_token": None, "raw_urls": [],
                "error": (
                    "No photos found in this album. "
                    "Make sure the album is set to 'Anyone with the link can view' "
                    "and contains at least one photo."
                ),
                "error_type": "no_photos",
            }

        # Build full-resolution and thumbnail URLs
        base_urls = [f"https://lh3.googleusercontent.com/{photo_id}" for photo_id in found]

        # Thumbnail for gallery display (400×400, crop)
        thumb_urls = [u + "=w400-h400-c" for u in base_urls]
        # Full-res for upload (original, no resize param)
        full_urls = base_urls  # no size suffix = original resolution

        proxy_urls = [
            url_for("gallery.image_proxy", image_url=_encode_url(t))
            for t in thumb_urls
        ]

        logger.info("Shared album: found %d photos", len(found))

        return {
            "images": proxy_urls,
            "next_page_token": None,   # All loaded at once
            "raw_urls": full_urls,     # Full-res URLs saved for upload
            "error": None,
            "error_type": None,
        }

    except http_requests.exceptions.ConnectionError:
        return {
            "images": [], "next_page_token": None, "raw_urls": [],
            "error": "Could not connect to Google Photos. Check your internet connection.",
            "error_type": "network",
        }
    except Exception as exc:
        logger.exception("Error fetching shared album %s", album_url)
        return {
            "images": [], "next_page_token": None, "raw_urls": [],
            "error": f"Error loading album: {exc}",
            "error_type": "generic",
        }


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

def fetch_from_drive(creds, page_token: str | None = None) -> dict:
    """
    Fetch a page of images from Google Drive.

    Returns same shape as fetch_from_shared_album.
    """
    try:
        creds = _refresh_if_needed(creds)
        authed = AuthorizedSession(creds)

        params = {
            "pageSize": 25,
            "q": "mimeType contains 'image/' and trashed = false",
            "fields": "nextPageToken, files(id, name, thumbnailLink, webContentLink)",
            "orderBy": "name",
            "corpora": "user",
            "includeItemsFromAllDrives": True,
            "supportsAllDrives": True,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = authed.get(
            "https://www.googleapis.com/drive/v3/files",
            params=params,
            timeout=30,
        )

        if resp.status_code == 403:
            return {
                "images": [], "next_page_token": None, "raw_urls": [],
                "error": "Access denied (403). Please check Google Drive API permissions.",
                "error_type": "api_disabled",
            }

        resp.raise_for_status()
        data = resp.json()

        items = data.get("files", [])
        proxy_urls = []
        raw_urls = []
        for item in items:
            link = item.get("thumbnailLink")
            download_link = item.get("webContentLink")
            if link:
                proxy_urls.append(
                    url_for("gallery.image_proxy", image_url=_encode_url(link))
                )
                raw_urls.append(download_link or link)

        return {
            "images": proxy_urls,
            "next_page_token": data.get("nextPageToken"),
            "raw_urls": raw_urls,
            "error": None,
            "error_type": None,
        }

    except Exception as exc:
        logger.exception("Error fetching from Google Drive")
        return {
            "images": [], "next_page_token": None, "raw_urls": [],
            "error": f"Error fetching from Google Drive: {exc}",
            "error_type": "generic",
        }


# ---------------------------------------------------------------------------
# Image byte fetching (used by upload pipeline)
# ---------------------------------------------------------------------------

def fetch_image_bytes(creds, encoded_url: str) -> bytes:
    """
    Decode the proxy-encoded URL and fetch the raw image bytes.

    For Google Photos shared album images (lh3.googleusercontent.com):
      - No auth required (public CDN). Request directly.
    For Google Drive images:
      - Requires an authenticated session.

    Strips sizing parameters to get full-resolution image.

    Returns raw bytes or raises an exception.
    """
    decoded = base64.urlsafe_b64decode(encoded_url).decode()

    # Strip Google Photo sizing/crop params (e.g. =w400-h400-c) to get full-res
    if "lh3.googleusercontent.com" in decoded:
        # Remove any sizing suffix after the last '='
        if re.search(r'=[whs]\d', decoded.split("/")[-1]):
            decoded = decoded.rsplit("=", 1)[0]
        # Public CDN — no auth needed
        resp = http_requests.get(decoded, stream=True, timeout=60)
        resp.raise_for_status()
        return resp.content

    # Google Drive — needs credentials
    if creds:
        creds = _refresh_if_needed(creds)
        authed = AuthorizedSession(creds)
        resp = authed.get(decoded, stream=True, timeout=60)
        resp.raise_for_status()
        return resp.content

    raise ValueError(f"No credentials available to fetch {decoded}")
