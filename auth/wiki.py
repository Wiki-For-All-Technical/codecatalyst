from flask import session, request, redirect, url_for
from requests_oauthlib import OAuth1Session
from config import Config
import os

USER_AGENT = "WikimediaUploader/1.0 (https://your-app-url.com; your-email@example.com)" # Replace with your app's URL and contact email

def start_login():
    # Check if we have owner-only tokens configured in environment
    access_token = os.environ.get("WIKI_ACCESS_TOKEN")
    access_secret = os.environ.get("WIKI_ACCESS_SECRET")

    if access_token and access_secret:
        session["wiki_access_token"] = {
            "oauth_token": access_token,
            "oauth_token_secret": access_secret
        }
        session.modified = True
        return redirect(url_for("upload.do_upload"))

    if not Config.WIKI_CONSUMER_KEY or not Config.WIKI_CONSUMER_SECRET:
        raise ValueError("WIKI_CONSUMER_KEY and WIKI_CONSUMER_SECRET must be set in environment variables.")
    oauth = OAuth1Session(
        client_key=Config.WIKI_CONSUMER_KEY,
        client_secret=Config.WIKI_CONSUMER_SECRET,
        callback_uri=url_for("upload.wiki_callback", _external=True),
    )
    # Set the User-Agent header after creating the session
    oauth.headers.update({"User-Agent": USER_AGENT})
    fetch_response = oauth.fetch_request_token(Config.WIKI_INITIATE)
    session["wiki_request_token"] = fetch_response
    authorization_url = oauth.authorization_url(Config.WIKI_AUTHORIZE)
    return redirect(authorization_url)

def finish_login():
    request_token = session.get("wiki_request_token")
    oauth_verifier = request.args.get("oauth_verifier")
    oauth = OAuth1Session(
        client_key=Config.WIKI_CONSUMER_KEY,
        client_secret=Config.WIKI_CONSUMER_SECRET,
        resource_owner_key=request_token["oauth_token"],
        resource_owner_secret=request_token["oauth_token_secret"],
        verifier=oauth_verifier,
    )
    # Set the User-Agent header after creating the session
    oauth.headers.update({"User-Agent": USER_AGENT})
    access_tokens = oauth.fetch_access_token(Config.WIKI_TOKEN)
    session["wiki_access_token"] = access_tokens
    session.modified = True
    return redirect(url_for("upload.do_upload"))
