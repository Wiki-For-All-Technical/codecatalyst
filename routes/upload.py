"""
routes/upload.py

Upload controller — Wikimedia login flow and the upload pipeline.
Uses Wikimedia OAuth 2.0 Bearer token (stored by auth/wiki.py).
"""

import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import wiki
from auth.google import get_credentials
from services.google_service import fetch_image_bytes
from services.wikimedia_service import upload_file_to_commons_bearer

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


# ── Wikimedia auth pages ──────────────────────────────────────────────────────

@upload_bp.route("/wiki_prompt")
def wiki_prompt():
    """Prompt the user to connect Wikimedia after Google login."""
    session["post_wiki_next"] = url_for("gallery.select_domain")
    session.modified = True
    return render_template("wiki_login.html")


@upload_bp.route("/wiki_login")
def wiki_login():
    """Alias used by do_upload redirect when wiki session expires."""
    session["post_wiki_next"] = url_for("gallery.select_domain")
    session.modified = True
    return render_template("wiki_login.html")


@upload_bp.route("/wiki_authenticate", methods=["POST"])
def wiki_authenticate():
    """Start Wikimedia OAuth 2.0 flow via Authlib."""
    return wiki.start_login()


@upload_bp.route("/wiki_success")
def wiki_success():
    """Shown after a successful Wikimedia OAuth 2.0 callback."""
    return render_template("wiki_success.html")


# ── Metadata form ─────────────────────────────────────────────────────────────

@upload_bp.route("/metadata", methods=["POST"])
def metadata():
    selected = request.form.getlist("selected_images")
    if not selected:
        flash("No images selected. Please select at least one image.", "warning")
        return redirect(url_for("gallery.display_gallery"))
    session["selected_images"] = selected
    session.modified = True
    return render_template("metadata.html", images=selected)


@upload_bp.route("/save_metadata", methods=["POST"])
def save_metadata():
    image_urls     = request.form.getlist("image_url")
    titles         = request.form.getlist("title")
    descriptions   = request.form.getlist("description")
    categories_raw = request.form.getlist("categories")

    if not image_urls:
        flash("No image data received. Please try again.", "error")
        return redirect(url_for("gallery.select_domain"))

    metadata_list = []
    for i, url in enumerate(image_urls):
        cats = [
            c.strip()
            for c in (categories_raw[i] if i < len(categories_raw) else "").split(",")
            if c.strip()
        ]
        metadata_list.append({
            "url":         url,
            "title":       titles[i]       if i < len(titles)       else "",
            "description": descriptions[i] if i < len(descriptions) else "",
            "categories":  cats,
        })

    session["upload_metadata"] = metadata_list
    session.permanent = True
    session.modified  = True
    logger.info("Metadata saved for %d images", len(metadata_list))
    return redirect(url_for("upload.do_upload"))


# ── Upload execution ──────────────────────────────────────────────────────────

@upload_bp.route("/do_upload", methods=["GET", "POST"])
def do_upload():
    """
    Main upload handler.
    Downloads each image from Google via the authenticated proxy, then
    uploads to Wikimedia Commons using an OAuth 2.0 Bearer token.
    """
    metadata_list = session.get("upload_metadata", [])
    access_token  = wiki.get_access_token()

    # ── Guards ────────────────────────────────────────────────────────────
    if not metadata_list:
        flash("Session expired. Please select images again.", "warning")
        return redirect(url_for("gallery.select_domain"))

    if not access_token:
        flash("Wikimedia session not found. Please connect your Wikimedia account.", "warning")
        return redirect(url_for("upload.wiki_login"))

    google_creds = get_credentials()
    if not google_creds:
        flash("Google session expired. Please login again.", "error")
        return redirect(url_for("main.google_login"))

    # ── Upload loop ───────────────────────────────────────────────────────
    upload_results = []

    for item in metadata_list:
        # The proxy URL contains the encoded path after /image_proxy/
        encoded_url_part = item["url"].split("/image_proxy/")[-1]

        # Step 1: Download from Google
        try:
            image_bytes = fetch_image_bytes(google_creds, encoded_url_part)
        except Exception as exc:
            upload_results.append({
                "success":  False,
                "filename": item.get("title", "unknown"),
                "url":      None,
                "error":    f"Failed to download from Google: {exc}",
            })
            continue

        # Step 2: Upload to Wikimedia Commons via Bearer token
        result = upload_file_to_commons_bearer(
            access_token=access_token,
            image_bytes=image_bytes,
            title=item.get("title", ""),
            description=item.get("description", ""),
            categories=item.get("categories", []),
        )

        if result.get("error") == "AUTH_EXPIRED":
            session.pop("wiki_token", None)
            session.pop("wiki_access_token", None)
            flash("Wikimedia session expired. Please reconnect your Wikimedia account.", "warning")
            return redirect(url_for("upload.wiki_login"))

        upload_results.append(result)

    # Clear metadata after a complete run
    session.pop("upload_metadata", None)
    session.modified = True

    success_count = sum(1 for r in upload_results if r.get("success"))
    return render_template(
        "upload_result.html",
        results=upload_results,
        success_count=success_count,
        total=len(upload_results),
    )
