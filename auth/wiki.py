"""
auth/wiki.py

Wikimedia OAuth 2.0 authentication using Authlib.

Flow:
  1. /upload/wiki_authenticate  → wiki.start_login()   → redirect to Wikimedia
  2. /wiki_callback             → wiki.finish_login()   → exchange code → store token
"""

import logging
from flask import session, redirect, url_for, current_app, request, flash
from app import oauth

logger = logging.getLogger(__name__)

# ── Token storage helpers ────────────────────────────────────────────────────

def _store_token(token: dict):
    """Persist the OAuth 2.0 token dict in the session."""
    session["wiki_token"] = token
    # Keep a flat access_token string for easy access
    session["wiki_access_token"] = token.get("access_token")
    session.modified = True


def get_token() -> dict | None:
    """Retrieve the stored OAuth 2.0 token dict, or None."""
    return session.get("wiki_token")


def get_access_token() -> str | None:
    """Return just the access_token string, or None."""
    return session.get("wiki_access_token")


def is_authenticated() -> bool:
    return bool(get_access_token())


# ── OAuth flow ───────────────────────────────────────────────────────────────

def start_login():
    """
    Build the Wikimedia authorisation URL and redirect the user there.
    Authlib stores the PKCE state/nonce automatically in the session.
    """
    redirect_uri = current_app.config["WIKI_REDIRECT_URI"]
    logger.info("Starting Wikimedia OAuth 2.0 login, redirect_uri=%s", redirect_uri)
    return oauth.wikimedia.authorize_redirect(redirect_uri)


def finish_login():
    """
    Handle the OAuth 2.0 callback:
      - Exchange the authorisation code for tokens
      - Store the token in the session
      - Redirect to the wiki success page
    """
    try:
        redirect_uri = current_app.config["WIKI_REDIRECT_URI"]
        token = oauth.wikimedia.authorize_access_token(redirect_uri=redirect_uri)
        logger.info("Wikimedia OAuth 2.0 token obtained successfully")
        _store_token(token)

        # Optionally fetch the user profile and store the username
        try:
            userinfo_url = current_app.config.get("WIKI_USERINFO_URL")
            if userinfo_url:
                resp = oauth.wikimedia.get(userinfo_url, token=token)
                resp.raise_for_status()
                profile = resp.json()
                session["wiki_username"] = profile.get("username") or profile.get("name")
                logger.info("Logged in as Wikimedia user: %s", session.get("wiki_username"))
        except Exception as exc:
            logger.warning("Could not fetch Wikimedia user profile: %s", exc)

        return redirect(url_for("upload.wiki_success"))

    except Exception as exc:
        err = str(exc)
        logger.error("Wikimedia OAuth 2.0 callback error: %s", err)
        flash(f"Wikimedia login failed: {err}", "error")
        return redirect(url_for("upload.wiki_login"))
