from flask import Blueprint, render_template, redirect, url_for, session
from auth import google, wiki

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/google_login")
def google_login():
    return google.login()

@main_bp.route("/oauth2callback")
def google_callback():
    return google.callback()


@main_bp.route("/oauth_callback")
def oauth_callback():
    return wiki.finish_login()

@main_bp.route("/wiki_direct_login")
def wiki_direct_login():
    """Use pre-generated access tokens directly (for owner-only consumers)"""
    return wiki.direct_login()

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
