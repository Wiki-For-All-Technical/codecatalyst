from flask import Blueprint, render_template, redirect, url_for
from auth import google

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
