from flask import session, redirect, url_for, current_app, request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from datetime import datetime
import logging


def creds_to_dict(creds):
    """Helper function to convert Google credentials object to a JSON-serializable dictionary."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes,
        'expiry': creds.expiry.isoformat() if creds.expiry else None
    }

def get_credentials():
    """Retrieves Google credentials from the session and reconstructs the Credentials object."""
    if 'credentials' not in session:
        return None
    creds_dict = session['credentials']
    
    # Create a copy to avoid modifying the session directly
    creds_data = creds_dict.copy()
    if creds_data.get('expiry'):
        creds_data['expiry'] = datetime.fromisoformat(creds_data['expiry'])
    return Credentials(**creds_data)

def get_flow():
    """Builds the Google OAuth Flow object from the app config."""
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": current_app.config["GOOGLE_CLIENT_ID"],
                "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [current_app.config["GOOGLE_REDIRECT_URI"]],
            }
        },
        scopes=current_app.config["GOOGLE_SCOPES"],
        redirect_uri=current_app.config["GOOGLE_REDIRECT_URI"]
    )

def login():
    """Initiates the Google login flow, forcing the consent screen to appear."""
    flow = get_flow()
    # 'prompt=consent' is the crucial fix. It forces the consent screen to appear every time,
    # ensuring that new scopes (like Google Photos) are requested from the user.
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='select_account consent'
    )
    session['state'] = state
    return redirect(authorization_url)

def callback():
    """Handles the callback from Google after user authentication."""
    flow = get_flow()
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    
    # DEBUG LOGGING: Check exactly what scopes Google returned
    logging.info(f"--- GOOGLE LOGIN CALLBACK ---")
    logging.info(f"Granted Scopes: {credentials.scopes}")
    
    session['credentials'] = creds_to_dict(credentials)

    return redirect(url_for('gallery.select_domain'))