"""
routes/main.py

Core / auth routes.
"""

from flask import Blueprint, render_template, redirect, url_for, session
from auth import google, wiki

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    google_logged_in = "credentials" in session
    wiki_logged_in = wiki.is_authenticated()
    wiki_username = session.get("wiki_username")
    return render_template(
        "index.html",
        google_logged_in=google_logged_in,
        wiki_logged_in=wiki_logged_in,
        wiki_username=wiki_username,
    )


# ── Google OAuth 2.0 ─────────────────────────────────────────────────────────

@main_bp.route("/google_login")
def google_login():
    return google.login()


@main_bp.route("/oauth2callback")
def google_callback():
    return google.callback()


# ── Wikimedia OAuth 2.0 ───────────────────────────────────────────────────────

@main_bp.route("/wiki_callback")
def wiki_callback():
    """Wikimedia OAuth 2.0 redirect callback."""
    return wiki.finish_login()


# ── Shared ────────────────────────────────────────────────────────────────────

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))


@main_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@main_bp.route("/terms")
def terms():
    return render_template("terms.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")
