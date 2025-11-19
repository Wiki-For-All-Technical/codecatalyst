# routes/gallery.py
from flask import Blueprint, render_template, redirect, url_for, request, session, flash, Response
import logging # Import the logging library
from google.auth.transport.requests import AuthorizedSession
from auth.google import get_credentials
from googleapiclient.discovery import build
import requests
import base64

gallery_bp = Blueprint("gallery", __name__, url_prefix="/gallery")


@gallery_bp.route("/select_domain")
def select_domain():
    """Step 1: Show dropdown to select Google Photos or Google Drive"""
    return render_template("select_domain.html")


@gallery_bp.route("/fetch", methods=["GET", "POST"])
def fetch_images(): # sourcery skip: extract-method
    """Step 2: Fetch images from selected domain and store in session (paginated)."""
    creds = get_credentials()
    if not creds:
        flash("Please login with Google first")
        return redirect(url_for("main.index"))

    if request.method == "POST":  # Initial fetch from form
        session.pop("images", None)  # Clear previous gallery
        session.pop("next_page_token", None)
        session["domain"] = request.form.get("domain")
        next_page_token = None
    else:  # Subsequent fetch (GET request for pagination)
        next_page_token = session.get("next_page_token")

    domain = session.get("domain")
    if not domain:
        flash("No domain selected. Please start over.")
        return redirect(url_for("gallery.select_domain"))

    required_scopes = {
        "photos": "https://www.googleapis.com/auth/photoslibrary.readonly",
        "drive": "https://www.googleapis.com/auth/drive"
    }
    if domain in required_scopes and required_scopes[domain] not in creds.scopes:
        flash(f"Access to {domain.title()} not granted. Please log in again.")
        return redirect(url_for("main.google_login"))

    # Manually refresh token if expired. This is more compatible than using listeners.
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        # Save the updated credentials back to the session
        session["credentials"] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }

    new_images = []

    if domain == "photos":
        # Fetch from Google Photos using googleapiclient
        try:
            # Create a fresh session for this API call to avoid state leakage
            photos_session = AuthorizedSession(creds)
            service = build("photoslibrary", "v1", http=photos_session, static_discovery=False)
            results = service.mediaItems().search(
                body={"pageSize": 25, "pageToken": next_page_token}
            ).execute()
            
            all_items = results.get("mediaItems", [])
            session["next_page_token"] = results.get("nextPageToken")

            # Add thumbnail sizing and filter out any items that might be missing a baseUrl
            # Create proxy URLs instead of direct Google URLs
            new_images = [ # The URL part is the base64 encoded google URL
                url_for('gallery.image_proxy', image_url=base64.urlsafe_b64encode((item["baseUrl"] + "=w200-h200").encode()).decode()) for item in all_items if "baseUrl" in item
            ]
            
        except Exception as e:
            logging.exception("Error fetching from Google Photos:") # Log the full error
            flash(f"Error fetching from Google Photos. Please ensure the Google Photos Library API is enabled in your Google Cloud Console. Error: {e}")
            return redirect(url_for("gallery.select_domain"))

    elif domain == "drive":
        try:
            # To completely avoid the googleapiclient state-leakage bug,
            # we will use a direct requests call for the Drive API.
            drive_session = AuthorizedSession(creds)

            params = {
                'pageSize': 25,
                'q': "mimeType contains 'image/' and trashed = false",
                'fields': "nextPageToken, files(id, name, thumbnailLink, webContentLink)",
                'orderBy': "name",
                'corpora': "user",
                'includeItemsFromAllDrives': True,
                'supportsAllDrives': True
            }
            if next_page_token:
                params['pageToken'] = next_page_token

            response = drive_session.get("https://www.googleapis.com/drive/v3/files", params=params)
            response.raise_for_status()
            results = response.json()
            
            all_items = results.get("files", [])
            session["next_page_token"] = results.get("nextPageToken")
            # Create proxy URLs for Drive images. Prioritize webContentLink over thumbnailLink.
            for item in all_items:
                # webContentLink is for downloading the file, thumbnailLink is for a small preview.
                # Let's use the thumbnail for the gallery view as it's smaller and faster.
                link = item.get("thumbnailLink") # or item.get("webContentLink")
                if link:
                    encoded_url = base64.urlsafe_b64encode(link.encode()).decode()
                    new_images.append(url_for('gallery.image_proxy', image_url=encoded_url))

        except Exception as e:
            logging.exception("Error fetching from Google Drive:") # Log the full error
            flash(f"Error fetching from Google Drive: {e}")
            return redirect(url_for("gallery.select_domain"))

    else:
        flash("Invalid domain selected")
        return redirect(url_for("gallery.select_domain"))

    # Append new images to the existing list in the session
    current_images = session.get("images", [])
    current_images.extend(new_images)
    session["images"] = current_images

    # If it's a GET request (AJAX for "load more"), return JSON. Otherwise, redirect.
    if request.method == "GET":
        return {
            "images": new_images,
            "next_page_token": session.get("next_page_token")
        }

    return redirect(url_for("gallery.display_gallery"))


@gallery_bp.route("/display")
def display_gallery():
    """Step 3: Display the gallery of fetched images."""
    images = session.get("images", [])
    return render_template("gallery.html", images=images, next_page_token=session.get("next_page_token"))


@gallery_bp.route("/image_proxy/<path:image_url>")
def image_proxy(image_url):
    """
    A proxy to fetch images using the server's credentials.
    The image_url is base64 encoded to be URL-safe.
    """
    creds = get_credentials()
    if not creds:
        return "Authentication required", 401

    try:
        decoded_url = base64.urlsafe_b64decode(image_url).decode()
        
        # Use an AuthorizedSession to fetch the image. This correctly adds the
        # 'Authorization: Bearer <token>' header to the request.
        authed_session = AuthorizedSession(creds)
        resp = authed_session.get(decoded_url, stream=True)
        resp.raise_for_status()
        return Response(resp.iter_content(chunk_size=1024), content_type=resp.headers['Content-Type'])
    except Exception as e:
        # Return a 1x1 pixel transparent GIF on error
        return Response(base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"), mimetype='image/gif')