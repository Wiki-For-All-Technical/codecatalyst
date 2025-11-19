import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev")

    # Flask-Session
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False

    # Google
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

    # Wikimedia
    WIKI_CONSUMER_KEY = os.getenv("WIKI_CONSUMER_KEY")
    WIKI_CONSUMER_SECRET = os.getenv("WIKI_CONSUMER_SECRET")

    # API endpoints
    WIKI_INITIATE = "https://commons.wikimedia.org/w/index.php?title=Special:OAuth/initiate&format=json"
    WIKI_AUTHORIZE = "https://commons.wikimedia.org/w/index.php?title=Special:OAuth/authorize"
    WIKI_TOKEN = "https://commons.wikimedia.org/w/index.php?title=Special:OAuth/token&format=json"
    WIKI_API = "https://commons.wikimedia.org/w/api.php"

    GOOGLE_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/photoslibrary.readonly"
    ]
