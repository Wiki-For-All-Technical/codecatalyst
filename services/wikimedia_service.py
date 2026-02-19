"""
services/wikimedia_service.py

Business logic for uploading to Wikimedia Commons using an OAuth 2.0 Bearer token.
"""

import re
import time
import logging
import requests

logger = logging.getLogger(__name__)

COMMONS_API  = "https://commons.wikimedia.org/w/api.php"
USER_AGENT   = "G2Commons/2.0 (https://github.com/your-org/g2commons; your-email@example.com)"


def _commons_session(access_token: str) -> requests.Session:
    """Return a requests.Session pre-configured with the Bearer token."""
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {access_token}",
        "User-Agent":    USER_AGENT,
    })
    return s


def get_csrf_token(access_token: str) -> str:
    """
    Fetch a CSRF (edit) token from Wikimedia Commons.
    Raises ValueError if the API returns an error.
    """
    s    = _commons_session(access_token)
    resp = s.get(
        COMMONS_API,
        params={"action": "query", "meta": "tokens", "type": "csrf", "format": "json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        code = data["error"].get("code", "")
        info = data["error"].get("info", "Unknown API error")
        if code in ("mwoauth-invalid-authorization", "badtoken", "mustbeloggedin"):
            raise PermissionError("AUTH_EXPIRED")
        raise ValueError(f"API error [{code}]: {info}")

    token = data.get("query", {}).get("tokens", {}).get("csrftoken")
    if not token or token == "+\\":
        raise ValueError("Could not obtain a CSRF token — are you logged in?")
    return token


def sanitize_filename(title: str, fallback: str = "G2Commons_Upload") -> str:
    """Return a Wikimedia-safe filename base (no extension)."""
    clean = re.sub(r"[^\w\s\-.]", "", title or "").strip()
    return clean.replace(" ", "_") if clean else fallback


def build_wikitext(description: str, categories: list[str]) -> str:
    """Generate the standard Commons wikitext page content."""
    cat_wikitext = "\n".join(f"[[Category:{c}]]" for c in (categories or []))
    return (
        f"== {{{{int:filedesc}}}} ==\n"
        f"{{{{Information\n"
        f"|description={description}\n"
        f"|date={{{{subst:CURRENTYEAR}}}}-{{{{subst:CURRENTMONTH}}}}-{{{{subst:CURRENTDAY2}}}}\n"
        f"|source={{{{own}}}}\n"
        f"|author=[[User:{{{{subst:REVISIONUSER}}}}|]]\n"
        f"}}}}\n\n"
        f"== {{{{int:license-header}}}} ==\n"
        f"{{{{self|cc-by-sa-4.0}}}}\n"
        f"{cat_wikitext}"
    )


def upload_file_to_commons_bearer(
    access_token: str,
    image_bytes: bytes,
    title: str,
    description: str,
    categories: list[str] | None = None,
) -> dict:
    """
    Upload a single file to Wikimedia Commons using an OAuth 2.0 Bearer token.

    Returns:
        {
            'success':  bool,
            'filename': str,
            'url':      str | None,
            'error':    str | None,
        }
    """
    # ── 1. Get CSRF token ───────────────────────────────────────────────
    try:
        csrf_token = get_csrf_token(access_token)
    except PermissionError:
        return {"success": False, "filename": "", "url": None, "error": "AUTH_EXPIRED"}
    except Exception as exc:
        return {"success": False, "filename": "", "url": None, "error": f"Auth error: {exc}"}

    # ── 2. Build filename and wikitext ──────────────────────────────────
    base     = sanitize_filename(title)
    filename = f"{base}_{int(time.time())}.jpg"
    pagetext = build_wikitext(description, categories or [])

    # ── 3. POST to upload API ───────────────────────────────────────────
    s = _commons_session(access_token)
    try:
        resp = s.post(
            COMMONS_API,
            files={"file": (filename, image_bytes, "image/jpeg")},
            data={
                "action":         "upload",
                "filename":       filename,
                "token":          csrf_token,
                "text":           pagetext,
                "comment":        f"Uploaded via G2Commons: {description[:200]}",
                "format":         "json",
                "ignorewarnings": 1,
            },
            timeout=120,
        )
    except Exception as exc:
        logger.exception("Network error during Wikimedia upload of %s", filename)
        return {"success": False, "filename": filename, "url": None, "error": str(exc)}

    if resp.status_code != 200:
        return {
            "success":  False,
            "filename": filename,
            "url":      None,
            "error":    f"HTTP {resp.status_code}: {resp.text[:300]}",
        }

    try:
        result = resp.json()
    except ValueError:
        return {
            "success":  False,
            "filename": filename,
            "url":      None,
            "error":    f"Invalid JSON response: {resp.text[:300]}",
        }

    # ── 4. Parse result ─────────────────────────────────────────────────
    if "error" in result:
        code = result["error"].get("code", "")
        info = result["error"].get("info", "Unknown error")
        if code in ("mwoauth-invalid-authorization", "badtoken", "mustbeloggedin"):
            return {"success": False, "filename": filename, "url": None, "error": "AUTH_EXPIRED"}
        return {"success": False, "filename": filename, "url": None, "error": f"[{code}] {info}"}

    upload_data = result.get("upload", {})
    if upload_data.get("result") == "Success":
        commons_filename = upload_data.get("filename", filename)
        commons_url = f"https://commons.wikimedia.org/wiki/File:{commons_filename}"
        logger.info("Successfully uploaded %s to Commons", commons_filename)
        return {"success": True, "filename": commons_filename, "url": commons_url, "error": None}

    return {
        "success":  False,
        "filename": filename,
        "url":      None,
        "error":    f"Unexpected response: {result}",
    }
