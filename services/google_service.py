"""
services/google_service.py

Business logic for fetching images from Google Photos and Google Drive.
All functions return structured dicts with 'images', 'next_page_token', and 'error' keys.
"""

import base64
import logging
from flask import url_for
from google.auth.transport.requests import Request, AuthorizedSession
import requests as http_requests

logger = logging.getLogger(__name__)


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
        return True  # Optimistically proceed; the API call itself will fail if scope is wrong


def fetch_from_photos(creds, page_token: str | None = None) -> dict:
    """
    Fetch a page of images from Google Photos.

    Returns:
        {
            'images': [proxy_url, ...],   # list of gallery.image_proxy URLs
            'next_page_token': str | None,
            'error': str | None,          # human-readable error, if any
            'error_type': str | None,     # 'scope' | 'api_disabled' | 'generic'
        }
    """
    PHOTOS_SCOPE = "https://www.googleapis.com/auth/photoslibrary.readonly"

    try:
        creds = _refresh_if_needed(creds)

        if not _check_real_scopes(creds, PHOTOS_SCOPE):
            return {
                "images": [], "next_page_token": None,
                "error": (
                    "Google Photos permission was not granted. "
                    "Please log in again and accept the Photos permission."
                ),
                "error_type": "scope",
            }

        headers = {"Authorization": f"Bearer {creds.token}"}
        params = {"pageSize": 25}
        if page_token:
            params["pageToken"] = page_token

        resp = http_requests.get(
            "https://photoslibrary.googleapis.com/v1/mediaItems",
            params=params,
            headers=headers,
            timeout=30,
        )

        if resp.status_code == 403:
            return {
                "images": [], "next_page_token": None,
                "error": (
                    "Access denied (403). The 'Google Photos Library API' may not be enabled "
                    "in your Google Cloud project, or your account is not a test user."
                ),
                "error_type": "api_disabled",
            }

        resp.raise_for_status()
        data = resp.json()

        items = data.get("mediaItems", [])
        proxy_urls = [
            url_for(
                "gallery.image_proxy",
                image_url=_encode_url(item["baseUrl"] + "=w400-h400"),
            )
            for item in items
            if "baseUrl" in item
        ]

        return {
            "images": proxy_urls,
            "next_page_token": data.get("nextPageToken"),
            "error": None,
            "error_type": None,
        }

    except Exception as exc:
        logger.exception("Error fetching from Google Photos")
        return {
            "images": [], "next_page_token": None,
            "error": f"Error fetching from Google Photos: {exc}",
            "error_type": "generic",
        }


def fetch_from_drive(creds, page_token: str | None = None) -> dict:
    """
    Fetch a page of images from Google Drive.

    Returns same shape as fetch_from_photos.
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
                "images": [], "next_page_token": None,
                "error": "Access denied (403). Please check Google Drive API permissions.",
                "error_type": "api_disabled",
            }

        resp.raise_for_status()
        data = resp.json()

        items = data.get("files", [])
        proxy_urls = []
        for item in items:
            link = item.get("thumbnailLink")
            if link:
                proxy_urls.append(
                    url_for("gallery.image_proxy", image_url=_encode_url(link))
                )

        return {
            "images": proxy_urls,
            "next_page_token": data.get("nextPageToken"),
            "error": None,
            "error_type": None,
        }

    except Exception as exc:
        logger.exception("Error fetching from Google Drive")
        return {
            "images": [], "next_page_token": None,
            "error": f"Error fetching from Google Drive: {exc}",
            "error_type": "generic",
        }


def fetch_image_bytes(creds, encoded_url: str) -> bytes:
    """
    Decode the proxy-encoded URL and fetch the raw image bytes via an authenticated session.
    Strips sizing parameters to get the full-resolution image.

    Returns raw bytes or raises an exception.
    """
    decoded = base64.urlsafe_b64decode(encoded_url).decode()

    # Strip Google Photo sizing params (e.g. =w400-h400) for full-res download
    if "=" in decoded and ("-h" in decoded or "-w" in decoded or decoded.endswith("=s400")):
        decoded = decoded.split("=")[0]

    creds = _refresh_if_needed(creds)
    authed = AuthorizedSession(creds)
    resp = authed.get(decoded, stream=True, timeout=60)
    resp.raise_for_status()
    return resp.content
