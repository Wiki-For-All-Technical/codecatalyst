import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-change-me")

    # Flask-Session (filesystem backend)
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_FILE_DIR = os.path.join(os.getcwd(), ".flask_sessions")

    # ── Google OAuth 2.0 ─────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/oauth2callback")

    GOOGLE_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/photoslibrary.readonly",
    ]

    # ── Wikimedia OAuth 2.0 ──────────────────────────────────────────────────
    # Register at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
    # Select "OAuth 2.0" when registering your consumer.
    WIKI_CLIENT_ID       = os.getenv("WIKI_CLIENT_ID")
    WIKI_CLIENT_SECRET   = os.getenv("WIKI_CLIENT_SECRET")
    WIKI_REDIRECT_URI    = os.getenv("WIKI_REDIRECT_URI", "http://localhost:5000/wiki_callback")

    # Wikimedia OAuth 2.0 endpoints (hosted on meta.wikimedia.org)
    WIKI_AUTHORIZE_URL   = "https://meta.wikimedia.org/w/rest.php/oauth2/authorize"
    WIKI_TOKEN_URL       = "https://meta.wikimedia.org/w/rest.php/oauth2/access_token"
    WIKI_USERINFO_URL    = "https://meta.wikimedia.org/w/rest.php/oauth2/resource/profile"

    # Commons API for uploads
    WIKI_API             = "https://commons.wikimedia.org/w/api.php"

    # Wikimedia OAuth 2.0 scopes
    # basic: read username; uploadfile: upload to Commons; editpage: write wikitext
    WIKI_SCOPES          = "basic uploadfile editpage"
