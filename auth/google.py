from flask import session, redirect, request, url_for, flash
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from config import Config

def get_google_flow(state=None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": Config.GOOGLE_CLIENT_ID,
                "client_secret": Config.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [Config.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=Config.GOOGLE_SCOPES,
        state=state,
        redirect_uri=Config.GOOGLE_REDIRECT_URI,
    )

# ...existing code...
def login():
    flow = get_google_flow()
    auth_url, state = flow.authorization_url(
        # access_type="offline" is needed to get a refresh token.
        # The library includes this by default if the scope includes 'offline_access',
        # but it's good practice to be explicit.
        access_type="offline",
        prompt="consent"  # Force consent to ensure a refresh_token is always requested.
    )
    session["state"] = state
    return redirect(auth_url)

def callback():
    state = session.pop("state", None)
    flow = get_google_flow(state=state)
    try:
        # Use full authorization_response to preserve state/code
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        # log useful debug info and ask user to re-authenticate
        import logging, traceback
        logging.exception("Google token exchange failed")
        print("AUTH URL:", request.url)
        print("REQUEST ARGS:", dict(request.args))
        traceback.print_exc()
        flash("Google token exchange failed; please try logging in again.")
        return redirect(url_for("main.google_login"))

    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    flash("Google login successful")
    return redirect(url_for("gallery.select_domain"))

# new helper to fetch photos using Photos Library API
def list_google_photos(max_items=50):
    from googleapiclient.discovery import build
    creds = get_credentials()
    if not creds:
        return None, "No valid Google credentials"
    try:
        photos_service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)
        results = photos_service.mediaItems().list(pageSize=max_items).execute()
        items = results.get("mediaItems", [])
        return items, None
    except Exception as e:
        import logging, traceback
        logging.exception("Failed to list Google Photos media items")
        traceback.print_exc()
        return None, str(e)
# ...existing code...

from datetime import datetime, timezone

def get_credentials():
    if "credentials" not in session:
        return None
    
    creds_data = session["credentials"]
    
    # Reconstruct Credentials object from session data
    creds = Credentials(
        token=creds_data["token"],
        refresh_token=creds_data.get("refresh_token"), # Use .get for safety
        token_uri=creds_data["token_uri"],
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=creds_data["scopes"],
        # Convert expiry string back to a naive datetime object representing UTC.
        # The google-auth library expects a naive datetime for comparison.
        expiry=(datetime.fromisoformat(creds_data["expiry"].replace("Z", ""))
                if creds_data.get("expiry") else None)
    )

    # The AuthorizedSession in the image_proxy will handle automatic token refreshes.
    # We only need to check for a non-refreshable expired token.
    if creds.expired and not creds.refresh_token:
        flash("Your Google session has expired and cannot be refreshed. Please log in again.")
        session.pop("credentials", None)
        return None

    return creds
