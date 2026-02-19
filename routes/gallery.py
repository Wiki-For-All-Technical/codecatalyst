"""
routes/gallery.py

Image fetching / gallery controller.
All business logic is delegated to services/google_service.py.
"""

import base64
import logging
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, Response
from auth.google import get_credentials, creds_to_dict
from auth import wiki
from services.google_service import fetch_from_shared_album, fetch_from_drive
import requests as http_requests

logger = logging.getLogger(__name__)

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")

# ---------------------------------------------------------------------------
# Domain selection
# ---------------------------------------------------------------------------

@gallery_bp.route("/select_domain")
def select_domain():
    """Show source picker (Google Photos shared album vs Google Drive)."""
    if not get_credentials():
        flash("Please login with Google first.", "error")
        return redirect(url_for("main.index"))
    if not wiki.is_authenticated():
        flash("Please login to Wikimedia Commons first.", "warning")
        return redirect(url_for("upload.wiki_prompt"))
    return render_template("select_domain.html")


# ---------------------------------------------------------------------------
# Image fetching (initial + pagination)
# ---------------------------------------------------------------------------

@gallery_bp.route("/fetch", methods=["GET", "POST"])
def fetch_images():
    """
    POST → initial fetch (clears old gallery, reads domain + optional album_url from form).
    GET  → load-more / pagination for Drive (JSON response for AJAX).
    """
    creds = get_credentials()
    if not creds:
        flash("Session expired. Please login with Google again.", "error")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        session.pop("images", None)
        session.pop("raw_urls", None)
        session.pop("next_page_token", None)
        session["domain"] = request.form.get("domain", "drive")
        session["album_url"] = request.form.get("album_url", "").strip()
        page_token = None
    else:
        page_token = session.get("next_page_token")

    domain = session.get("domain")
    if not domain:
        flash("No source selected. Please start over.", "warning")
        return redirect(url_for("gallery.select_domain"))

    # --- Delegate to service layer ------------------------------------------
    if domain == "photos":
        album_url = session.get("album_url", "")
        if not album_url:
            flash("Please paste a shared Google Photos album link.", "error")
            return redirect(url_for("gallery.select_domain"))
        result = fetch_from_shared_album(album_url)

    elif domain == "drive":
        result = fetch_from_drive(creds, page_token)
        # Re-persist credentials in case they were refreshed
        creds_after = get_credentials()
        if creds_after:
            session["credentials"] = creds_to_dict(creds_after)
    else:
        flash("Invalid source selected.", "error")
        return redirect(url_for("gallery.select_domain"))

    if result["error"]:
        if result.get("error_type") == "scope":
            session.pop("credentials", None)
            flash(result["error"], "error")
            return redirect(url_for("main.google_login"))
        flash(result["error"], "error")
        return redirect(url_for("gallery.select_domain"))

    # Accumulate images + raw_urls in session
    current_images = session.get("images", [])
    current_raw    = session.get("raw_urls", [])
    current_images.extend(result["images"])
    current_raw.extend(result.get("raw_urls", []))
    session["images"]          = current_images
    session["raw_urls"]        = current_raw
    session["next_page_token"] = result["next_page_token"]
    session.modified = True

    # AJAX pagination request → JSON
    if request.method == "GET":
        return {
            "images": result["images"],
            "next_page_token": result["next_page_token"],
        }

    return redirect(url_for("gallery.display_gallery"))


# ---------------------------------------------------------------------------
# Gallery display
# ---------------------------------------------------------------------------

@gallery_bp.route("/display")
def display_gallery():
    images = session.get("images", [])
    if not images:
        flash("No images fetched yet. Please select a source first.", "warning")
        return redirect(url_for("gallery.select_domain"))
    return render_template(
        "gallery.html",
        images=images,
        next_page_token=session.get("next_page_token"),
        domain=session.get("domain", "drive"),
    )


# ---------------------------------------------------------------------------
# Image proxy
# ---------------------------------------------------------------------------

@gallery_bp.route("/image_proxy/<path:image_url>")
def image_proxy(image_url):
    """
    Proxy to serve images to the browser.
    image_url is a base64-encoded image URL.

    - lh3.googleusercontent.com (shared album): fetched directly — no auth needed.
    - Google Drive thumbnails: fetched via AuthorizedSession.
    """
    from google.auth.transport.requests import AuthorizedSession

    try:
        decoded_url = base64.urlsafe_b64decode(image_url).decode()

        if "lh3.googleusercontent.com" in decoded_url:
            # Public Google Photos CDN — no credentials required
            resp = http_requests.get(decoded_url, stream=True, timeout=30)
        else:
            creds = get_credentials()
            if not creds:
                return "Authentication required", 401
            authed = AuthorizedSession(creds)
            resp = authed.get(decoded_url, stream=True, timeout=30)

        resp.raise_for_status()
        return Response(
            resp.iter_content(chunk_size=4096),
            content_type=resp.headers.get("Content-Type", "image/jpeg"),
        )
    except Exception:
        logger.exception("Image proxy error for %s", image_url[:60])
        # Return a 1×1 transparent GIF as fallback
        return Response(
            base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
            mimetype="image/gif",
        )