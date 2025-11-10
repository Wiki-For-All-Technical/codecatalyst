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


@gallery_bp.route("/fetch", methods=["POST"])
def fetch_images():
    """Step 2: Fetch images from selected domain and store in session."""
    if request.method == "POST":
        domain = request.form.get("domain")
        creds = get_credentials()

        if not creds:
            flash("Please login with Google first")
            return redirect(url_for("main.index"))

        required_scopes = {
            "photos": "https://www.googleapis.com/auth/photoslibrary.readonly",
            "drive": "https://www.googleapis.com/auth/drive"
        }
        if domain in required_scopes and required_scopes[domain] not in creds.scopes:
            flash(f"Access to {domain.title()} not granted. Please log in again.")
            return redirect(url_for("main.google_login"))

        images = []

        if domain == "photos":
            # Fetch from Google Photos using googleapiclient
            try:
                service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)
                all_items = []
                next_page_token = None

                while True: # Loop until all pages are fetched
                    results = service.mediaItems().list(pageSize=100, pageToken=next_page_token).execute()
                    all_items.extend(results.get("mediaItems", []))
                    next_page_token = results.get("nextPageToken")

                    if not next_page_token:
                        break

                # Sort items by creation date (newest first) for a consistent order.
                all_items.sort(key=lambda x: x.get('mediaMetadata', {}).get('creationTime', ''), reverse=True)
                # Add thumbnail sizing and filter out any items that might be missing a baseUrl
                # Create proxy URLs instead of direct Google URLs
                images = [ # The URL part is the base64 encoded google URL
                    url_for('gallery.image_proxy', image_url=base64.urlsafe_b64encode((item["baseUrl"] + "=w200-h200").encode()).decode()) for item in all_items if "baseUrl" in item
                ]
                
            except Exception as e:
                logging.exception("Error fetching from Google Photos:") # Log the full error
                flash(f"Error fetching from Google Photos. Please ensure the Google Photos Library API is enabled in your Google Cloud Console. Error: {e}")
                return redirect(url_for("gallery.select_domain"))

        elif domain == "drive":
            try:
                # Fetch from Google Drive using googleapiclient
                service = build("drive", "v3", credentials=creds)
                all_items = []
                page_token = None
                while True:
                    results = service.files().list(
                        pageSize=100,  # Fetch more items per page
                        q="mimeType contains 'image/' and trashed = false", # Query for non-trashed images
                        fields="nextPageToken, files(id, name, thumbnailLink, webContentLink)",
                        pageToken=page_token,
                        corpora="user",  # Search the user's 'My Drive' and items shared with them.
                        includeItemsFromAllDrives=True, # Include items from shared drives.
                        supportsAllDrives=True  # Acknowledge that the app supports shared drives.
                    ).execute()
                    
                    all_items.extend(results.get("files", []))
                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break
                # Sort items by name for a consistent order.
                all_items.sort(key=lambda x: x.get('name', ''))
                # Create proxy URLs for Drive images. Prioritize webContentLink over thumbnailLink.
                for item in all_items:
                    # webContentLink is for downloading the file, thumbnailLink is for a small preview.
                    # Let's use the thumbnail for the gallery view as it's smaller and faster.
                    link = item.get("thumbnailLink") # or item.get("webContentLink")
                    if link:
                        encoded_url = base64.urlsafe_b64encode(link.encode()).decode()
                        images.append(url_for('gallery.image_proxy', image_url=encoded_url))

            except Exception as e:
                logging.exception("Error fetching from Google Drive:") # Log the full error
                flash(f"Error fetching from Google Drive: {e}")
                return redirect(url_for("gallery.select_domain"))

        else:
            flash("Invalid domain selected")
            return redirect(url_for("gallery.select_domain"))

        # Store in session for next step
        session["images"] = images
        return redirect(url_for("gallery.display_gallery"))


@gallery_bp.route("/display")
def display_gallery():
    """Step 3: Display the gallery of fetched images."""
    images = session.get("images", [])
    return render_template("gallery.html", images=images)


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
        def update_session_credentials(refreshed_creds):
            """Callback to save refreshed credentials to the session."""
            session["credentials"]["token"] = refreshed_creds.token
            # It's also good practice to update the expiry if it's available
            if refreshed_creds.expiry:
                session["credentials"]["expiry"] = refreshed_creds.expiry.isoformat()
            if hasattr(refreshed_creds, 'expires_at') and refreshed_creds.expires_at:
                session["credentials"]["expiry"] = refreshed_creds.expires_at.isoformat()
            session.modified = True

        authed_session = AuthorizedSession(creds, refreshed_callback=update_session_credentials)
        resp = authed_session.get(decoded_url, stream=True)
        resp.raise_for_status()
        return Response(resp.iter_content(chunk_size=1024), content_type=resp.headers['Content-Type'])
    except Exception as e:
        # Return a 1x1 pixel transparent GIF on error
        return Response(base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"), mimetype='image/gif')
