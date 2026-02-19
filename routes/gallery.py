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
from services.google_service import fetch_from_photos, fetch_from_drive

logger = logging.getLogger(__name__)

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")

# ---------------------------------------------------------------------------
# Domain selection
# ---------------------------------------------------------------------------

@gallery_bp.route("/select_domain")
def select_domain():
    """Show source picker (Google Photos vs Google Drive)."""
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
    POST → initial fetch (clears old gallery, reads domain from form).
    GET  → load-more / pagination (AJAX JSON response).
    """
    creds = get_credentials()
    if not creds:
        flash("Session expired. Please login with Google again.", "error")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        session.pop("images", None)
        session.pop("next_page_token", None)
        session["domain"] = request.form.get("domain", "photos")
        page_token = None
    else:
        page_token = session.get("next_page_token")

    domain = session.get("domain")
    if not domain:
        flash("No source selected. Please start over.", "warning")
        return redirect(url_for("gallery.select_domain"))

    # --- Delegate to service layer ------------------------------------------
    if domain == "photos":
        result = fetch_from_photos(creds, page_token)
    elif domain == "drive":
        result = fetch_from_drive(creds, page_token)
    else:
        flash("Invalid source selected.", "error")
        return redirect(url_for("gallery.select_domain"))

    # Refresh session credentials if token was refreshed inside service
    # (AuthorizedSession refreshes automatically; re-persist just in case)
    # (Only matters for photos; creds object may have been refreshed)
    creds_after = get_credentials()
    if creds_after:
        session["credentials"] = creds_to_dict(creds_after)

    if result["error"]:
        if result.get("error_type") == "scope":
            # Need to re-login
            session.pop("credentials", None)
            flash(result["error"], "error")
            return redirect(url_for("main.google_login"))
        flash(result["error"], "error")
        return redirect(url_for("gallery.select_domain"))

    # Accumulate images in session
    current = session.get("images", [])
    current.extend(result["images"])
    session["images"] = current
    session["next_page_token"] = result["next_page_token"]
    session.modified = True

    # AJAX pagination → JSON
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
        domain=session.get("domain", "photos"),
    )


# ---------------------------------------------------------------------------
# Authenticated image proxy
# ---------------------------------------------------------------------------

@gallery_bp.route("/image_proxy/<path:image_url>")
def image_proxy(image_url):
    """
    Proxy to serve Google-authenticated images to the browser.
    image_url is a base64-encoded Google URL.
    """
    from google.auth.transport.requests import AuthorizedSession

    creds = get_credentials()
    if not creds:
        return "Authentication required", 401

    try:
        decoded_url = base64.urlsafe_b64decode(image_url).decode()
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