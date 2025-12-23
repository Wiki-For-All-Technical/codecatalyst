from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import wiki
from config import Config
import base64
from auth.google import get_credentials
from google.auth.transport.requests import AuthorizedSession
from requests_oauthlib import OAuth1Session
import time

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

@upload_bp.route("/metadata", methods=["POST"])
def metadata():
    selected = request.form.getlist("selected_images")
    if not selected:
        flash("No images selected.")
        return redirect(url_for("gallery.select_domain"))
    session["selected_images"] = selected
    session.modified = True
    return render_template("metadata.html", images=selected)

@upload_bp.route("/save_metadata", methods=["POST"])
def save_metadata():
    """Save metadata from form and redirect to Wikimedia login."""
    image_urls = request.form.getlist("image_url")
    titles = request.form.getlist("title")
    descriptions = request.form.getlist("description")
    print(f"DEBUG: Received {len(image_urls)} images in save_metadata")
    print(f"DEBUG: Titles: {titles}, Descriptions: {descriptions}")

    if not image_urls:
        print("DEBUG: No image URLs received")
        flash("Error: No image data received. Please try again.")
        return redirect(url_for("gallery.select_domain"))

    # Structure metadata and store in session
    metadata_list = []
    for i in range(len(image_urls)):
        metadata_list.append({"url": image_urls[i], "title": titles[i], "description": descriptions[i]})

    session["upload_metadata"] = metadata_list
    print(f"DEBUG: Saved metadata to session: {len(metadata_list)} items")
    print(f"DEBUG: Session keys after save: {list(session.keys())}")
    session.permanent = True
    session.modified = True
    return render_template("wiki_login.html")

@upload_bp.route("/wiki_login")
def wiki_login():
    return wiki.start_login()

@upload_bp.route("/wiki_callback")
def wiki_callback():
    return wiki.finish_login()

@upload_bp.route("/verify_login", methods=["POST"])
def verify_login():
    username = request.form.get("username")
    password = request.form.get("password")
    # For now, just store the username in session and redirect to upload option
    session["wiki_username"] = username
    session.modified = True
    return redirect(url_for("upload.upload_option"))

@upload_bp.route("/upload_option")
def upload_option():
    return render_template("upload_option.html")

@upload_bp.route("/do_upload", methods=["GET", "POST"])
def do_upload():
    metadata_list = session.get("upload_metadata", [])
    wiki_tokens = session.get("wiki_access_token")
    print(f"DEBUG: do_upload - Metadata count: {len(metadata_list)}, Tokens present: {bool(wiki_tokens)}")
    print(f"DEBUG: Session keys in do_upload: {list(session.keys())}")
    print(f"DEBUG: Session permanent: {session.permanent}")
    print(f"DEBUG: Session modified: {session.modified}")

    if not metadata_list:
        print("DEBUG: No metadata found, redirecting to select_domain")
        flash("Session expired. Please select images again.")
        return redirect(url_for("gallery.select_domain"))

    if not wiki_tokens:
        return redirect(url_for("upload.wiki_login"))

    # Create authenticated session
    google_creds = get_credentials()
    if not google_creds:
        flash("Google session expired. Please log in again.")
        return redirect(url_for("main.google_login"))

    oauth = OAuth1Session(
        client_key=Config.WIKI_CONSUMER_KEY,
        client_secret=Config.WIKI_CONSUMER_SECRET,
        resource_owner_key=wiki_tokens["oauth_token"],
        resource_owner_secret=wiki_tokens["oauth_token_secret"],
    )
    oauth.headers.update({'User-Agent': 'WikimediaUploader/1.0'})

    # Step 2: Upload images
    upload_results = []
    for item in metadata_list:
        try:
            # Step 1: Get CSRF token for each upload
            try:
                token_response = oauth.get(Config.WIKI_API, params={"action": "query", "meta": "tokens", "type": "csrf", "format": "json"})
                if token_response.status_code == 200:
                    token_resp = token_response.json()
                    csrf_token = token_resp["query"]["tokens"]["csrftoken"]
                else:
                    upload_results.append({"error": f"Failed to get CSRF token for {item.get('title', 'image')}: HTTP {token_response.status_code}: {token_response.text}"})
                    continue
            except ValueError as e:
                upload_results.append({"error": f"Failed to parse CSRF token response for {item.get('title', 'image')}: {e}. Response: {token_response.text[:500]}"})
                continue
            except Exception as e:
                upload_results.append({"error": f"Failed to get CSRF token for {item.get('title', 'image')}: {e}"})
                continue

            # Step 2: Fetch image data directly from Google (bypass local proxy)
            encoded_url_part = item['url'].split('/')[-1]
            decoded_url = base64.urlsafe_b64decode(encoded_url_part).decode()

            # Remove any size parameters to get the full-size image
            # Google Photos URLs may contain parameters like =w200-h200, =s400, etc.
            if '=' in decoded_url and ('-h' in decoded_url or '-w' in decoded_url or decoded_url.endswith('=s400')):
                # Remove size parameters to get full resolution
                base_url = decoded_url.split('=')[0]
            else:
                base_url = decoded_url

            # Make an authenticated request directly to Google
            google_authed_session = AuthorizedSession(google_creds)
            image_response = google_authed_session.get(base_url, stream=True)
            image_response.raise_for_status()
            image_content = image_response.content

            # Step 3: Upload the file content to Wikimedia
            base_filename = item['title'].strip().replace(" ", "_") if item['title'].strip() else f"Wikigram_Upload_{item['url'][-10:]}"
            timestamp = str(int(time.time()))
            filename = f"{base_filename}_{timestamp}.jpg"
            
            upload_request = oauth.post(
                Config.WIKI_API,
                files={"file": (filename, image_content)},
                data={
                    "action": "upload", "filename": filename, "token": csrf_token,
                    "comment": item['description'], "format": "json", "ignorewarnings": 1,
                }
            )

            # Check if the response is valid JSON before parsing
            try:
                if upload_request.status_code == 200:
                    result = upload_request.json()
                    upload_results.append(result)
                else:
                    upload_results.append({"error": f"HTTP {upload_request.status_code}: {upload_request.text}"})
            except ValueError as e:
                # JSON parsing failed
                upload_results.append({"error": f"Failed to parse response for {filename}: {e}. Response: {upload_request.text[:500]}"})
        except Exception as e:
            upload_results.append({"error": f"Failed to upload {item.get('title', 'image')}: {e}"})

    return render_template("upload_result.html", results=upload_results)
