from flask import session, request, redirect, url_for
from requests_oauthlib import OAuth1Session
from config import Config
import logging
import os
import json

USER_AGENT = "WikimediaUploader/1.0 (https://your-app-url.com; your-email@example.com)"

def _get_wiki_session(**kwargs):
    """Creates and configures an OAuth1Session for the Wikimedia API."""
    if not Config.WIKI_CONSUMER_KEY or not Config.WIKI_CONSUMER_SECRET:
        raise ValueError("WIKI_CONSUMER_KEY and WIKI_CONSUMER_SECRET must be set in environment variables.")

    session_params = {
        'client_key': Config.WIKI_CONSUMER_KEY,
        'client_secret': Config.WIKI_CONSUMER_SECRET,
    }
    session_params.update(kwargs)

    oauth = OAuth1Session(**session_params)
    oauth.headers.update({"User-Agent": USER_AGENT})
    return oauth

def start_login():
    """Initialize Wikimedia OAuth 1.0a login flow - redirects to official Wikimedia login page"""
    try:
        callback_url = Config.WIKI_CALLBACK_URL
        consumer_key = Config.WIKI_CONSUMER_KEY
        
        logging.warning(f"=== WIKIMEDIA OAUTH DETAILS ===")
        logging.warning(f"Callback URL: {callback_url}")
        logging.warning(f"Consumer Key: {consumer_key}")
        logging.warning(f"OAuth Initiate URL: {Config.WIKI_INITIATE}")
        logging.warning(f"================================")

        # Create OAuth1Session
        oauth = _get_wiki_session(callback_uri=callback_url)

        # Manually fetch request token because Wikimedia returns non-standard JSON
        response = oauth.post(Config.WIKI_INITIATE)
        response.raise_for_status()
        
        token_data = response.json()
        if 'key' not in token_data or 'secret' not in token_data:
            raise ValueError(f"Invalid request token response from Wikimedia: {token_data}")

        request_token = {
            'oauth_token': token_data['key'],
            'oauth_token_secret': token_data['secret']
        }
        
        # Store request token in session
        session["wiki_request_token"] = request_token
        session.modified = True
        logging.info("Stored request token in session")
        
        # Manually construct the authorization URL.
        # The `oauth.authorization_url` method can't be used here because it doesn't know
        # about the token we fetched manually from the JSON response.
        from urllib.parse import urlencode
        auth_url = f"{Config.WIKI_AUTHORIZE}&{urlencode({'oauth_token': request_token['oauth_token']})}"
        logging.info(f"Redirecting to authorization page: {auth_url}")
        
        return redirect(auth_url)
        
    except Exception as e:
        err_text = str(e)
        logging.error(f"Wikimedia OAuth Error: {err_text}")
        print(f"\n=== WIKIMEDIA ERROR ===")
        print(f"Error: {err_text}")
        print(f"======================\n")
        
        if "signature" in err_text.lower() or "invalid" in err_text.lower():
            return (
                "<b>Wikimedia Login Error: Invalid Signature</b><br><br>"
                "Your consumer key or secret may be incorrect. Please verify them on Special:OAuthConsumerRegistration.<br><br>"
                f"Error: {err_text}"
            ), 500
        
        return (f"<b>Wikimedia Login Error:</b> {err_text}<br><br>" 
                "Please check your consumer settings on Special:OAuthConsumerRegistration and try again."), 500

def finish_login():
    """Complete Wikimedia OAuth 1.0a login"""
    try:
        request_token = session.get("wiki_request_token")
        if not request_token:
            logging.error("No request token found in session")
            return redirect(url_for("upload.wiki_login"))

        oauth_verifier = request.args.get("oauth_verifier")
        if not oauth_verifier:
            logging.error("No oauth_verifier in callback")
            return redirect(url_for("upload.wiki_login"))

        # Create OAuth session with request token
        oauth = _get_wiki_session(
            resource_owner_key=request_token.get("oauth_token"),
            resource_owner_secret=request_token.get("oauth_token_secret"),
            verifier=oauth_verifier,
        )
        
        # Manually fetch access token because Wikimedia returns non-standard JSON
        response = oauth.post(Config.WIKI_TOKEN)
        response.raise_for_status()

        token_data = response.json()
        if 'key' not in token_data or 'secret' not in token_data:
            raise ValueError(f"Invalid access token response from Wikimedia: {token_data}")

        access_token = {
            'oauth_token': token_data['key'],
            'oauth_token_secret': token_data['secret']
        }
        
        # Store access token in session
        session["wiki_access_token"] = access_token
        session.modified = True
        
        # Always redirect to the success page to show "Login Successful"
        session.pop("post_wiki_next", None)
        return redirect(url_for("upload.wiki_success"))
        
    except Exception as e:
        err_text = str(e)
        logging.error(f"Wikimedia OAuth finish_login error: {err_text}")
        return (f"<b>Wikimedia Login Error:</b> {err_text}<br><br>" 
                "Please try logging in again."), 500

def direct_login():
    """Use pre-generated access tokens directly"""
    try:
        if not Config.WIKI_ACCESS_TOKEN or not Config.WIKI_ACCESS_SECRET:
            return (
                "<b>Wikimedia Login Error:</b> Pre-generated access tokens not found<br><br>"
                "Please ensure WIKI_ACCESS_TOKEN and WIKI_ACCESS_SECRET are set in your .env file."
            ), 500
        
        # Store pre-generated tokens directly in session
        session["wiki_access_token"] = {
            'oauth_token': Config.WIKI_ACCESS_TOKEN,
            'oauth_token_secret': Config.WIKI_ACCESS_SECRET,
        }
        session.modified = True
        logging.info("Using pre-generated Wikimedia access tokens")

        # Redirect to success page first
        return redirect(url_for("upload.wiki_success"))
        
    except Exception as e:
        err_text = str(e)
        logging.error(f"Wikimedia direct_login error: {err_text}")
        return (f"<b>Wikimedia Login Error:</b> {err_text}"), 500
