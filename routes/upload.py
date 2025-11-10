from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from auth import wiki
from config import Config
import base64
from auth.google import get_credentials
import requests
from requests_oauthlib import OAuth1Session

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")

@upload_bp.route("/metadata", methods=["POST"])
def metadata():
    selected = request.form.getlist("selected_images")
    if not selected:
        flash("No images selected.")
        return redirect(url_for("gallery.select_domain"))
    session["selected_images"] = selected
    return render_template("metadata.html", images=selected)

@upload_bp.route("/save_metadata", methods=["POST"])
def save_metadata():
    """Save metadata from form and redirect to Wikimedia login."""
    image_urls = request.form.getlist("image_url")
    titles = request.form.getlist("title")
    descriptions = request.form.getlist("description")

    # Structure metadata and store in session
    metadata_list = []
    for i in range(len(image_urls)):
        metadata_list.append({"url": image_urls[i], "title": titles[i], "description": descriptions[i]})
    
    session["upload_metadata"] = metadata_list
    return redirect(url_for("upload.wiki_login"))

@upload_bp.route("/wiki_login")
def wiki_login():
    return wiki.start_login()

@upload_bp.route("/wiki_callback")
def wiki_callback():
    return wiki.finish_login()

@upload_bp.route("/do_upload")
def do_upload():
    metadata_list = session.get("upload_metadata", [])
    wiki_tokens = session.get("wiki_access_token")

    if not metadata_list or not wiki_tokens:
        flash("Missing images or Wikimedia login")
    if not metadata_list or not wiki_tokens:
        flash("Missing image metadata or Wikimedia login")
        return redirect(url_for("main.index"))

    # Create authenticated session
    oauth = OAuth1Session(
        client_key=Config.WIKI_CONSUMER_KEY,
        client_secret=Config.WIKI_CONSUMER_SECRET,
        resource_owner_key=wiki_tokens["oauth_token"],
        resource_owner_secret=wiki_tokens["oauth_token_secret"],
    )

    # Step 2: Upload images
    upload_results = []
    for item in metadata_list:
        try:
            # Step 1: Get CSRF token for each upload
            token_resp = oauth.get(Config.WIKI_API, params={"action": "query", "meta": "tokens", "type": "csrf", "format": "json"}).json()
            csrf_token = token_resp["query"]["tokens"]["csrftoken"]

            # Step 2: Fetch image data via proxy.
            # The URL from the form is /gallery/image_proxy/<encoded_url_of_thumbnail>
            encoded_url_part = item['url'].split('/')[-1]
            
            # Decode the URL to get the original Google URL, remove the size parameter for full resolution
            decoded_url = base64.urlsafe_b64decode(encoded_url_part).decode()
            if "=w200-h200" in decoded_url: # Specific to Google Photos
                base_url = decoded_url.split("=w200-h200")[0]
                # Re-encode the full-resolution URL for the proxy
                encoded_url_part = base64.urlsafe_b64encode(base_url.encode()).decode()

            full_image_url = url_for('gallery.image_proxy', image_url=encoded_url_part, _external=True)
            
            # Pass the session cookie which contains the Google auth token to the proxy endpoint
            session_cookie = request.cookies.get('session')
            image_response = requests.get(full_image_url, cookies={'session': session_cookie}, stream=True)
            image_response.raise_for_status()
            image_content = image_response.content

            # Step 3: Upload the file content to Wikimedia
            filename = item['title'].strip().replace(" ", "_") + ".jpg" if item['title'].strip() else f"Wikigram_Upload_{item['url'][-10:]}.jpg"
            
            upload_request = oauth.post(
                Config.WIKI_API,
                files={"file": (filename, image_content)},
                data={
                    "action": "upload", "filename": filename, "token": csrf_token,
                    "comment": item['description'], "format": "json", "ignorewarnings": 1,
                }
            )
            upload_results.append(upload_request.json())
        except Exception as e:
            upload_results.append({"error": f"Failed to upload {item.get('title', 'image')}: {e}"})

    return render_template("upload_result.html", results=upload_results)
